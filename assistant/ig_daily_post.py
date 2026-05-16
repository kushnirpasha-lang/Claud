#!/usr/bin/env python3
"""
HAiR LOVE — атомарный ежедневный постинг в Instagram (VPS-native).

Заменяет ненадёжный GitHub Actions cron. Запускается systemd-таймером
ровно в 20:00 Europe/Kiev (см. hairlove-ig-post.timer).

Ключевые свойства (решения аудита 2026-05-16):
  A. Атомарность. Источник истины — локальный ig_state.json на VPS.
     Он пишется атомарно (temp + os.replace) СРАЗУ при успехе публикации,
     ДО git push индекса. Если push в obshak упадёт — состояние уже
     зафиксировано, следующий запуск НЕ перепостит, а доедет индекс.
  A. Сверка с IG API. Перед постингом тянем недавние медиа аккаунта и
     проверяем, не было ли уже поста сегодня (по киевской дате). Это
     ловит худший случай: публикация прошла, но всё остальное упало и
     state не записался.
  D. Self-pull. Скрипт сам синхронит ветку контента (claude/obshak).

Идемпотентность = «не более одного поста за киевские сутки», проверяется
по реальному состоянию аккаунта в IG, а не по дате git-коммита.
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta

import requests

# --- Конфигурация --------------------------------------------------------

ASSISTANT_DIR = "/opt/assistant"
CONTENT_DIR = "/opt/hairlove-content"          # клон канон-ветки HairLove
CONTENT_BRANCH = "claude/hairlove"             # КАНОН: код+контент+очередь+индекс в одной ветке (консолидация 2026-05-16, obshak выведен из пайплайна)
REPO = "kushnirpasha-lang/Claud"

QUEUE_REL = "projects/hairlove/artifacts/instagram/posting-queue.json"
INDEX_REL = "projects/hairlove/artifacts/instagram/posting-index.txt"
PHOTOS_REL = "projects/hairlove/artifacts/instagram/photos"

STATE_FILE = os.path.join(ASSISTANT_DIR, "ig_state.json")
LOCK_FILE = os.path.join(ASSISTANT_DIR, "ig_post.lock")
LOG_FILE = os.path.join(ASSISTANT_DIR, "ig_post.log")
# Разовый флаг: если есть — следующий запуск постит, минуя проверку
# «уже постили сегодня», и удаляет флаг (срабатывает один раз).
FORCE_FLAG = os.path.join(ASSISTANT_DIR, "ig_force_once.flag")

KYIV_TZ = timezone(timedelta(hours=3))         # Europe/Kiev (EEST, лето)

GRAPH = "https://graph.instagram.com/v21.0"

CAPTIONS = {
    1: "Ти вже пробувала засіб, після якого локони просто слухаються? "
       "Кератин, сфінголіпіди, шовкові амінокислоти, олія аргани. "
       "Наноси на вологе волосся — не змивай. Все.\n\n"
       "Розроблено в Італії | HAiR LOVE",
    2: "Без силіконів. Без сульфатів. Без компромісів.\n\n"
       "Кератин + сфінголіпіди + шовкові амінокислоти + олія аргани + олія макадамії.\n\n"
       "Розроблено в Італії | HAiR LOVE",
    3: "Фен, праска, плойка — щодня. Thermo Protector Spray захищає до 220°C, "
       "розгладжує та додає блиск. Кератин + 9 амінокислот + екстракт виноградної кісточки. "
       "Не склеює.\n\nРозроблено в Італії | HAiR LOVE",
    4: "Масажуй до появи крем-піни — це значить що засіб працює. "
       "Гідролізований кератин, колаген, алое, пантенол запечатують кожну лусочку. "
       "15 секунд — бальзам. До 30 хвилин — маска-філер.\n\n"
       "Розроблено в Італії | HAiR LOVE",
}


# --- Утилиты -------------------------------------------------------------

def log(msg: str) -> None:
    ts = datetime.now(KYIV_TZ).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def run(cmd, cwd=None, check=True):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"cmd failed: {' '.join(cmd)}\n{r.stderr.strip()}")
    return r


def kyiv_today() -> str:
    return datetime.now(KYIV_TZ).strftime("%Y-%m-%d")


def kyiv_now() -> str:
    return datetime.now(KYIV_TZ).strftime("%Y-%m-%d %H:%M")


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def write_state_atomic(state: dict) -> None:
    """Атомарная запись состояния: temp-файл + os.replace (одна транзакция)."""
    state["updated"] = datetime.now(KYIV_TZ).isoformat()
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, STATE_FILE)


def telegram_notify(text: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    # TELEGRAM_CHAT_ID в .env — надёжнее всего.
    # Если не задан — используем @Pavel_Kus (работает, если он писал боту).
    # getUpdates НЕ используем: бот делает long polling и потребляет все updates.
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "") or "@Pavel_Kus"
    if not token:
        return
    try:
        if chat_id:
            requests.get(
                f"https://api.telegram.org/bot{token}/sendMessage",
                params={"chat_id": chat_id, "text": text}, timeout=10,
            )
    except Exception as e:  # noqa: BLE001 — уведомление не критично
        log(f"telegram notify failed (non-fatal): {e}")


# --- Git self-pull (D) ---------------------------------------------------

def sync_content_repo() -> None:
    """Синхронит локальный клон ветки контента. Создаёт клон при отсутствии."""
    token = os.environ.get("GH_TOKEN", "").strip()
    auth = f"https://{token}@github.com/{REPO}.git" if token else f"https://github.com/{REPO}.git"

    if not os.path.isdir(os.path.join(CONTENT_DIR, ".git")):
        log(f"content clone отсутствует — клонирую {CONTENT_BRANCH} в {CONTENT_DIR}")
        run(["git", "clone", "--branch", CONTENT_BRANCH, "--single-branch",
             auth, CONTENT_DIR])
    run(["git", "remote", "set-url", "origin", auth], cwd=CONTENT_DIR)
    run(["git", "fetch", "origin", CONTENT_BRANCH], cwd=CONTENT_DIR)
    # checkout -B + reset FETCH_HEAD: устойчиво независимо от имени локальной
    # ветки и single-branch-конфига старого клона (важно при миграции веток).
    run(["git", "checkout", "-B", CONTENT_BRANCH, "FETCH_HEAD"], cwd=CONTENT_DIR)
    run(["git", "reset", "--hard", "FETCH_HEAD"], cwd=CONTENT_DIR)
    run(["git", "config", "user.email", "bot@hairlove.studio"], cwd=CONTENT_DIR)
    run(["git", "config", "user.name", "HAiR LOVE Bot"], cwd=CONTENT_DIR)


def push_index(new_index: int, photo: str) -> bool:
    """Двигает posting-index.txt в канон-ветку. Не критично: state уже записан."""
    idx_path = os.path.join(CONTENT_DIR, INDEX_REL)
    try:
        with open(idx_path, "w", encoding="utf-8") as f:
            f.write(f"{new_index}\n")
        run(["git", "add", INDEX_REL], cwd=CONTENT_DIR)
        run(["git", "commit", "-m",
             f"instagram: опубліковано пост #{new_index} — {photo}"], cwd=CONTENT_DIR)
        for attempt, backoff in enumerate((0, 2, 4, 8), 1):
            if backoff:
                time.sleep(backoff)
            r = run(["git", "push", "origin", CONTENT_BRANCH],
                    cwd=CONTENT_DIR, check=False)
            if r.returncode == 0:
                log(f"index → {new_index} запушен в {CONTENT_BRANCH}")
                return True
            log(f"push попытка {attempt} не удалась: {r.stderr.strip()}")
        return False
    except Exception as e:  # noqa: BLE001
        log(f"push_index failed (non-fatal, state уже записан): {e}")
        return False


# --- Instagram -----------------------------------------------------------

def ig_token() -> str:
    return os.environ["INSTAGRAM_ACCESS_TOKEN"]


def ig_user() -> str:
    return os.environ["INSTAGRAM_USER_ID"]


def already_posted_today() -> bool:
    """Сверка с реальностью (A): был ли пост за киевские сутки уже опубликован."""
    try:
        r = requests.get(
            f"{GRAPH}/{ig_user()}/media",
            params={"fields": "id,timestamp", "limit": 5,
                    "access_token": ig_token()},
            timeout=20,
        )
        r.raise_for_status()
        today = kyiv_today()
        for m in r.json().get("data", []):
            ts = m.get("timestamp", "")
            if not ts:
                continue
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.astimezone(KYIV_TZ).strftime("%Y-%m-%d") == today:
                log(f"IG API: уже есть пост за сегодня ({today}), id={m.get('id')}")
                return True
        return False
    except Exception as e:  # noqa: BLE001
        # Не смогли свериться — безопаснее НЕ постить (риск дубля > риск пропуска)
        log(f"IG API сверка не удалась: {e} — пропускаю запуск ради безопасности")
        return True


def publish(photo: str, caption: str) -> str:
    enc = requests.utils.quote(photo)
    image_url = (f"https://raw.githubusercontent.com/{REPO}/"
                 f"{CONTENT_BRANCH}/{PHOTOS_REL}/{enc}")
    log(f"image_url: {image_url}")

    r = requests.post(
        f"{GRAPH}/{ig_user()}/media",
        data={"image_url": image_url, "caption": caption,
              "access_token": ig_token()},
        timeout=60,
    )
    cj = r.json()
    cid = cj.get("id")
    if not cid:
        raise RuntimeError(f"container error: {cj.get('error', cj)}")

    time.sleep(5)

    r2 = requests.post(
        f"{GRAPH}/{ig_user()}/media_publish",
        data={"creation_id": cid, "access_token": ig_token()},
        timeout=60,
    )
    pj = r2.json()
    pid = pj.get("id")
    if not pid:
        raise RuntimeError(f"publish error: {pj.get('error', pj)}")
    return pid


# --- Основной цикл -------------------------------------------------------

def main() -> int:
    # Lock — не допускаем параллельных запусков
    import fcntl
    lock_fd = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        log("Уже выполняется (lock занят) — выход")
        return 0

    log("=== HAiR LOVE daily post START ===")

    sync_content_repo()

    queue_path = os.path.join(CONTENT_DIR, QUEUE_REL)
    index_path = os.path.join(CONTENT_DIR, INDEX_REL)
    with open(queue_path, encoding="utf-8") as f:
        queue = json.load(f)
    with open(index_path, encoding="utf-8") as f:
        git_index = int(f.read().strip())

    state = load_state()
    state_index = state.get("next_index")
    if state_index is None:
        # Бутстрап: первый запуск, доверяем git
        state_index = git_index
        log(f"state отсутствует — бутстрап из git index = {git_index}")

    # Реконсиляция расхождения state ↔ git (A)
    if state_index > git_index:
        log(f"state ({state_index}) > git ({git_index}): прошлый push упал — "
            f"доезжаю индекс без перепоста")
        target = state_index
    elif state_index < git_index:
        log(f"state ({state_index}) < git ({git_index}): state отстал — "
            f"доверяю git")
        target = git_index
        state_index = git_index
    else:
        target = state_index

    if target >= len(queue):
        log(f"Очередь пройдена ({target}/{len(queue)}) — постить нечего")
        return 0

    # Разовый force-флаг: обходит проверку «уже постили сегодня» один раз
    force = os.path.exists(FORCE_FLAG)
    if force:
        log("FORCE-флаг найден — обхожу проверку 'уже постили сегодня' (разово)")
        try:
            os.remove(FORCE_FLAG)
        except OSError:
            pass

    # Идемпотентность по реальному состоянию аккаунта (A)
    if not force and already_posted_today():
        log("Сегодня уже постили (или сверка недоступна) — пропуск. "
            "Синхронизирую индекс если отстал.")
        if state_index > git_index:
            entry = queue[min(state_index - 1, len(queue) - 1)]
            push_index(state_index, entry["photo"])
        return 0

    entry = queue[target]
    photo = entry["photo"]
    caption = CAPTIONS.get(int(entry["caption_id"]), CAPTIONS[1])
    log(f"Постим index={target}/{len(queue)} photo={photo} cap={entry['caption_id']}")

    # Помечаем попытку (для диагностики/реконсиляции)
    state["attempting_index"] = target
    state["next_index"] = state_index
    write_state_atomic(state)

    try:
        post_id = publish(photo, caption)
    except Exception as e:  # noqa: BLE001
        log(f"❌ Публикация не удалась: {e}")
        state.pop("attempting_index", None)
        write_state_atomic(state)
        telegram_notify(
            f"❌ HAiR LOVE — пост НЕ опубліковано\n\n"
            f"Фото: {photo}\n"
            f"Пост: #{target + 1} з {len(queue)}\n"
            f"Помилка: {e}\n\n"
            f"🕗 {kyiv_now()} (Київ)"
        )
        return 1

    # УСПЕХ — атомарно фиксируем состояние ПЕРЕД git push (ядро решения A)
    new_index = target + 1
    state["next_index"] = new_index
    state["last_post_id"] = post_id
    state["last_photo"] = photo
    state["last_posted_date"] = kyiv_today()
    state.pop("attempting_index", None)
    write_state_atomic(state)
    log(f"✅ Опубліковано! post_id={post_id}. State зафиксирован: next={new_index}")

    # Зеркалим индекс в obshak (не критично — state уже истина)
    push_index(new_index, photo)

    telegram_notify(
        f"✅ HAiR LOVE — пост опубліковано в Instagram\n\n"
        f"Фото: {photo}\n"
        f"Пост: #{new_index} з {len(queue)}\n"
        f"Акаунт: @hair_love_company\n\n"
        f"🕗 {kyiv_now()} (Київ)"
    )
    log("=== HAiR LOVE daily post DONE ===")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        log(f"FATAL: {e}")
        sys.exit(1)

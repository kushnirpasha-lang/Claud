#!/usr/bin/env bash
set -euo pipefail

# ── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[•]${NC} $*"; }
success() { echo -e "${GREEN}[✓]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
error()   { echo -e "${RED}[✗]${NC} $*"; exit 1; }

REPO="https://github.com/kushnirpasha-lang/Claud.git"
BRANCH="claude/setup-digitalocean-vps-4Ij39"
APP_DIR="/opt/assistant"

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      Личный ИИ-ассистент — установка     ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── Root check ──────────────────────────────────────────────────────────────
[[ $EUID -ne 0 ]] && error "Запусти скрипт от root: sudo bash install.sh"

# ── 1. System packages ───────────────────────────────────────────────────────
info "Шаг 1/6 — Установка системных пакетов..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv nginx git curl openssl 2>/dev/null
success "Системные пакеты установлены"

# ── 2. Clone repo ────────────────────────────────────────────────────────────
info "Шаг 2/6 — Загрузка файлов ассистента..."
if [[ -d "$APP_DIR/.git" ]]; then
    warn "Директория уже существует — обновляю..."
    git -C "$APP_DIR" fetch origin "$BRANCH"
    git -C "$APP_DIR" reset --hard "origin/$BRANCH"
else
    rm -rf "$APP_DIR"
    git clone --branch "$BRANCH" --depth 1 "$REPO" "$APP_DIR"
fi
# Move assistant/ files to root of APP_DIR if needed
if [[ -d "$APP_DIR/assistant" ]]; then
    cp -r "$APP_DIR/assistant/." "$APP_DIR/"
fi
success "Файлы загружены в $APP_DIR"

# ── 3. Python virtualenv ─────────────────────────────────────────────────────
info "Шаг 3/6 — Установка Python-зависимостей..."
cd "$APP_DIR"
python3 -m venv venv
venv/bin/pip install -q --upgrade pip
venv/bin/pip install -q -r requirements.txt
success "Python-зависимости установлены"

# ── 4. Environment file ──────────────────────────────────────────────────────
info "Шаг 4/6 — Настройка переменных окружения..."

if [[ -f "$APP_DIR/.env" ]]; then
    warn ".env уже существует — пропускаю"
else
    echo ""
    echo -e "${YELLOW}Нужны данные для настройки:${NC}"
    echo ""

    read -rp "  Anthropic API Key (sk-ant-...): " ANTHROPIC_KEY
    [[ -z "$ANTHROPIC_KEY" ]] && error "API ключ не может быть пустым"

    read -rp "  Telegram Bot Token (от @BotFather): " BOT_TOKEN
    [[ -z "$BOT_TOKEN" ]] && error "Токен бота не может быть пустым"

    FLASK_SECRET=$(openssl rand -hex 32)

    cat > "$APP_DIR/.env" <<EOF
ANTHROPIC_API_KEY=${ANTHROPIC_KEY}
TELEGRAM_BOT_TOKEN=${BOT_TOKEN}
WEB_PORT=8080
FLASK_SECRET=${FLASK_SECRET}
EOF
    chmod 600 "$APP_DIR/.env"
    success ".env файл создан"
fi

# ── 5. Nginx ─────────────────────────────────────────────────────────────────
info "Шаг 5/6 — Настройка Nginx..."
cp "$APP_DIR/nginx.conf" /etc/nginx/sites-available/assistant
ln -sf /etc/nginx/sites-available/assistant /etc/nginx/sites-enabled/assistant
rm -f /etc/nginx/sites-enabled/default
nginx -t -q && systemctl restart nginx && systemctl enable nginx -q
success "Nginx настроен и запущен"

# ── 6. Systemd service ───────────────────────────────────────────────────────
info "Шаг 6/6 — Настройка автозапуска..."
cp "$APP_DIR/assistant.service" /etc/systemd/system/assistant.service
systemctl daemon-reload
systemctl enable assistant -q
systemctl restart assistant
sleep 3

# ── Done ─────────────────────────────────────────────────────────────────────
STATUS=$(systemctl is-active assistant 2>/dev/null || echo "unknown")
PUBLIC_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || echo "YOUR_IP")

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        Установка завершена!              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Статус сервиса : ${GREEN}${STATUS}${NC}"
echo -e "  Веб-чат        : ${BLUE}http://${PUBLIC_IP}${NC}"
echo -e "  Telegram бот   : работает в фоне"
echo ""
echo -e "${YELLOW}Полезные команды:${NC}"
echo "  systemctl status assistant      # статус"
echo "  journalctl -u assistant -f      # логи в реальном времени"
echo "  systemctl restart assistant     # перезапуск"
echo "  nano /opt/assistant/.env        # изменить API ключи"
echo ""

if [[ "$STATUS" != "active" ]]; then
    warn "Сервис не запустился. Смотри логи:"
    echo ""
    journalctl -u assistant -n 30 --no-pager
fi

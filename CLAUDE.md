# CLAUDE.md — HairLove

Ты работаешь над проектом **HairLove** — итальянский бренд профессиональной косметики для волос.
Владелец: **Павел** (@Pavel_Kus, +380637353733). Язык общения: русский.

## Рабочая директория проекта
```
projects/hairlove/
```
Все артефакты, знания, агенты — там.

## База знаний (читай перед любой задачей)
```
projects/hairlove/knowledge/компания.md    — кто мы, производство, рынки
projects/hairlove/knowledge/продукт.md     — продукты и цены (4 уровня)
projects/hairlove/knowledge/бренд.md       — позиционирование, голос, стиль
projects/hairlove/knowledge/аудитория.md   — B2B (салоны, дистрибуторы) и B2C
projects/hairlove/knowledge/метрики.md     — продажи, Instagram, реклама
projects/hairlove/knowledge/глоссарий.md   — термины, конкуренты, сокращения
```

## Агенты команды
| Slash-команда | Роль |
|---|---|
| `/hairlove` | Оркестратор — точка входа, маршрутизация |
| `/hairlove-strategy` | Стратегия, дорожная карта, решения |
| `/hairlove-texts` | Тексты для всех каналов |
| `/hairlove-insta` | Instagram, публикация, контент-план |
| `/hairlove-site` | Сайт, B2B витрина |
| `/hairlove-competitors` | Анализ конкурентов и рынка |
| `/hairlove-ads` | Meta Ads, Google Ads, таргетинг |

Субагенты в `projects/hairlove/.claude/agents/`:
`coordinator`, `planning`, `competitors`, `strategy`, `site`, `ads`, `growth`, `instagram`, `copy`, `text-editor`

## Маршруты
Актуальные цепочки агентов: `projects/hairlove/routes.md`

## Артефакты (результаты работы)
```
projects/hairlove/artifacts/strategy/
projects/hairlove/artifacts/competitors/
projects/hairlove/artifacts/instagram/
projects/hairlove/artifacts/copy/
projects/hairlove/artifacts/ads/
projects/hairlove/artifacts/site/
projects/hairlove/artifacts/planning/
projects/hairlove/artifacts/_summary/
```

## Текущее состояние команды
`projects/hairlove/team-state.md` — кто активен, на каком шаге, блокеры.

## Правила
1. Перед любой задачей — читай базу знаний (`knowledge/`)
2. Каждое действие → событие в дашборд: `bash ~/.claude/событие.sh hairlove <агент> <тип> "<сообщение>"`
3. Каждое действие → строка в `projects/hairlove/progress.log`
4. Артефакты сохраняй в соответствующую папку `artifacts/`
5. Обновляй `team-state.md` при смене активного агента
6. Не трогай `knowledge/` без явной команды Павла

## Дашборд агентов
`http://188.166.67.237/agents` — живая карта системы.

## Как запустить работу
- Полный цикл: `/hairlove` → `/full-cycle`
- Конкретная задача: вызови нужного агента напрямую
- Узнать маршрут: спроси `/hairlove` что делать с задачей

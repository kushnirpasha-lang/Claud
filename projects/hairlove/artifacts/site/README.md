# HairLove B2B Site — Deploy Guide

## Деплой на Vercel (3 кроки)

### Крок 1. Завантаж файл у GitHub
1. Створи репозиторій на GitHub (назва: `hairlove-site` або будь-яка)
2. Завантаж `index.html` у корінь репозиторію (drag & drop на github.com або через git)

### Крок 2. Підключи Vercel
1. Зайди на [vercel.com](https://vercel.com) → "Add New Project"
2. Обери репозиторій `hairlove-site` із GitHub
3. Framework Preset: **Other** (Vercel сам розпізнає статичний HTML)
4. Натисни **Deploy** — готово за ~30 секунд

### Крок 3. Домен (опційно)
- Vercel дасть безкоштовний URL: `hairlove-site.vercel.app`
- Щоб підключити свій домен (hairlove.com): Vercel → Project → Settings → Domains → Add

---

## Альтернатива: GitHub Pages (ще простіше)

1. GitHub репозиторій → Settings → Pages
2. Source: Deploy from branch → `main` → `/root`
3. Збережи — сайт буде на `username.github.io/hairlove-site`

---

## Структура файлів

```
artifacts/site/
├── index.html    # Весь сайт (HTML + CSS + JS в одному файлі)
└── README.md     # Цей файл
```

## Що є в сайті

- UA / RU / EN переключатель мов (зберігається в localStorage)
- 7 секцій: Nav → Hero → Продукти → Переваги → B2B → Форма → Footer
- Логотип SVG (HAiR LOVE з серцем замість O)
- Адаптивний дизайн (mobile-first, 375px+)
- Плавний скролл, fade-in анімації
- Форма → mailto (без бекенду)
- Бренд-кольори: бірюза #3ABFBF, зелений #5B8C5A, рожевий #F2D0D0

## Що оновити після запуску

- [ ] Замінити `mailto:info@hairlove.com` на реальний email в `handleSubmit()`
- [ ] Додати Google Analytics / Meta Pixel (якщо потрібно)
- [ ] Оновити ціни якщо зміняться
- [ ] Додати реальні фото продуктів (замінити SVG-ілюстрацію у hero)

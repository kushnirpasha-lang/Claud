# HAiR L♡VE — ТЗ для AI-генерации фото продуктов

Дата: 2026-05-07

---

## Инструмент

**Midjourney** (рекомендуется) — лучшее качество для продуктовой фотографии.  
Альтернатива: **Adobe Firefly** (вкладка «Generative Fill» или «Text to Image»).

---

## Как вставить фото реальной бутылки

### В Midjourney:
1. Загрузи фото бутылки в чат Discord → скопируй ссылку на изображение
2. В промпт вставь ссылку **первой**, потом текст:
   ```
   [ссылка на фото бутылки] [промпт ниже] --cref [ссылка на фото бутылки] --cw 100
   ```
3. Параметр `--cref` держит форму и цвет бутылки. `--cw 100` — максимальное сходство.

### В ChatGPT (DALL-E 3):
1. Прикрепи фото бутылки к сообщению
2. Напиши: *"Используй эту бутылку как продукт. Создай фото в стиле: [промпт]"*

---

## Визуальный стиль бренда (для всех изображений)

- **Палитра:** молочно-кремовый фон (`#EDE8DC`), акценты бирюза + нежно-розовый + шалфей
- **Настроение:** чистота, минимализм, профессиональная косметика, итальянская эстетика
- **Свет:** мягкий рассеянный, без жёстких теней — как студийный лайтбокс или северное окно
- **Текстуры рядом с бутылкой:** шёлковая ткань, лепестки, веточки, капли воды, мрамор
- **Никогда:** кричащие цвета, тёмный фон, глянцевые блики, перегруженная композиция

---

## ПРОМПТЫ — по типу поста

---

### 1. Чистый продуктовый шот (для всех продуктов)

**Использование:** первый пост о продукте, шапка профиля, Stories

```
Professional product photography of a hair care bottle, 
placed on a warm cream-colored surface (#EDE8DC), 
soft diffused natural light from the left, 
small sprig of green eucalyptus beside the bottle, 
minimal composition, clean Italian luxury aesthetic, 
shot on medium format camera, shallow depth of field, 
no shadows, no text overlays --ar 4:5 --style raw --v 6
```

**Для крем-спрея** — добавь в конце: `teal color accents, silk fabric draped softly beside`  
**Для термо-протектора** — добавь: `soft pink rose petals scattered around, warm tones`  
**Для маски-филлера** — добавь: `sage green leaves, aloe vera slice beside the bottle`

---

### 2. Текстурный флэтлей (вид сверху)

**Использование:** пост про состав, карусель «что внутри»

```
Flat lay product photography, hair care bottle centered, 
surrounded by its key ingredients laid out artfully: 
keratin pearl, argan oil in small glass bowl, silk threads, 
macadamia nuts, sprig of wheat, 
warm cream linen background, 
top-down view, soft even lighting, 
luxury beauty brand aesthetic, minimalist styling --ar 1:1 --style raw --v 6
```

**Для термо-протектора** замени ингредиенты на: `grape cluster, avocado half, amino acid capsules`  
**Для маски-филлера** замени на: `collagen pearls, aloe vera leaf cut open, rice grains, wheat`

---

### 3. Влажная текстура / «до и после ощущение»

**Использование:** пост про эффект, Reels-обложка

```
Close-up macro beauty photography, 
hair care spray bottle with water droplets on its surface, 
dark wet hair strand being touched gently from behind the bottle, 
soft teal-tinted morning light, 
misty atmosphere, 
luxury hair care brand, 
editorial beauty magazine style --ar 4:5 --style raw --v 6
```

---

### 4. Lifestyle — ванная / утренний ритуал

**Использование:** пост про использование, Stories

```
Lifestyle beauty photography, 
elegant bathroom shelf with marble surface, 
hair care bottle standing next to a white towel neatly folded, 
morning light through frosted glass window, 
cream and white tones, 
minimal luxury interior, 
no people visible, 
warm soft atmosphere --ar 4:5 --style raw --v 6
```

---

### 5. Руки + продукт (человеческое касание)

**Использование:** пост «как наносить», Reels-обложка

```
Elegant hands with natural manicure holding a hair care bottle, 
cream and teal color palette, 
soft natural light, 
clean white linen background, 
beauty editorial style, 
no jewelry, 
skin looks natural and healthy --ar 4:5 --style raw --v 6
```

---

### 6. Триплет — все три продукта вместе

**Использование:** пост «знакомьтесь с линейкой», шапка сайта

```
Three hair care bottles arranged in a triangle composition, 
warm cream background, 
each bottle slightly different pastel accent color (teal, rose, sage), 
soft studio lighting, 
luxury Italian beauty brand flat lay, 
green eucalyptus leaves scattered around, 
minimalist and clean --ar 16:9 --style raw --v 6
```

---

## Параметры Midjourney — шпаргалка

| Параметр | Что делает |
|---|---|
| `--ar 4:5` | Instagram-пост вертикальный |
| `--ar 1:1` | Instagram-пост квадратный |
| `--ar 9:16` | Stories / Reels-обложка |
| `--ar 16:9` | Горизонталь для сайта |
| `--style raw` | Реалистичнее, меньше AI-артефактов |
| `--v 6` | Последняя версия модели |
| `--cref [url]` | Держит внешний вид продукта с фото |
| `--cw 100` | Максимальное сходство с reference-фото |
| `--q 2` | Высокое качество (медленнее) |

---

## Что снять на телефон (для reference-фото)

Нужно **одно хорошее фото каждой бутылки** — оно станет основой для всей генерации.

**Как снять:**
- Поставь бутылку на белый лист А4 у окна (не в солнечный день — свет должен быть мягким)
- Снимай прямо, без угла — чтобы была видна этикетка
- Без фильтров, без вспышки
- Сфоткай все три: крем-спрей, термо-протектор, ламелярная маска

**Этих трёх фото достаточно** — остальное AI додумает сам.

---

## Порядок работы

1. Сфоткал бутылку по инструкции выше
2. Загрузил в Midjourney / ChatGPT
3. Скопировал промпт из этого файла
4. Вставил ссылку на фото + промпт → отправил
5. Выбрал лучший вариант из 4-х
6. Нажал `V` для вариаций или `U` для апскейла

---

*Артефакт создан: 2026-05-07 | Агент: instagram*

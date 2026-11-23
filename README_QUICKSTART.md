# Быстрый старт

> **Зачем этот файл:** кратчайший путь от пустой консоли до работающего сайта.
> Основной [`README.md`](README.md) — полный справочник; здесь только команды и
> типовые проблемы, чтобы поднять проект локально без чтения всей документации.

## Что понадобится

- Windows + PowerShell.
- Python **3.14.4**.
- Виртуальное окружение `D:\kod\djang-main\.venv` (будет создано, если его нет).

## Команды

```powershell
cd D:\kod\djang-main
if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

cd Al_Ven
$env:DB_ENGINE = "sqlite"
$env:DJANGO_DEBUG = "True"
$env:DJANGO_SSL_REDIRECT = "False"
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py runserver
```

Откройте:

- сайт — <http://127.0.0.1:8000/>;
- админка — <http://127.0.0.1:8000/admin/>.

Если `Al_Ven/db.sqlite3` уже есть в вашей локальной копии, `migrate` применит
только недостающие миграции. Чистый GitHub-клон не содержит локальную базу и
медиа: после `migrate` база будет пустой, а данные нужно восстановить из
личной резервной копии. Не загружайте базу с пользовательскими данными в GitHub.

## Проверка, что всё живо

```powershell
$env:DB_ENGINE = "sqlite"
..\.venv\Scripts\python.exe manage.py check
..\.venv\Scripts\python.exe manage.py test hello.tests
```

Ожидаемо: `System check identified no issues` и `Ran 29 tests ... OK`.

## Частые проблемы

| Симптом | Причина | Что делать |
| --- | --- | --- |
| Проект пытается подключиться к MySQL | `DB_ENGINE` по умолчанию `mysql` | Выполните `$env:DB_ENGINE = "sqlite"` в той же сессии PowerShell |
| Страница открывается, но нет CSS/JS | Статику не собрал dev-сервер | Убедитесь, что запущен `runserver`, а не `collectstatic`-режим без раздачи |
| HTTPS-ошибки в консоли runserver | Браузер отправляет `https://` на HTTP-порт | Введите `http://127.0.0.1:8000/` явно; HTTPS в режиме разработки выключен |
| Адрес в футере отображается как `РђР...` | Переменная `SITE_ADDRESS` была сохранена в Windows-1251 вместо UTF-8 | Известная форма повреждения исправляется автоматически; для другого текста задайте `SITE_ADDRESS` заново в корректной кодировке |
| Фото товаров не отображаются | `MEDIA_URL` раздаётся только при `DEBUG=True` | Локально оставьте `DJANGO_DEBUG=True`; в production настройте веб-сервер |
| `Invalid HTTP_HOST: testserver` в самописном скрипте | Django не знает тестовый хост | В скрипте добавьте `settings.ALLOWED_HOSTS += ["testserver"]` |
| Cloudflare показывает 520, 521–526, 1016, 1020 или 1033 | Ошибка edge, сети, DNS, TLS или security rule; запрос может не дойти до Django | Сверьте код в [справочнике Cloudflare](Cloudflare-ошибки.md); для локальной разработки используйте `http://127.0.0.1:8000/` |

Подробности — в [`README.md`](README.md) и [`AI_CONTEXT.md`](AI_CONTEXT.md).
Публикация через локальный Cloudflare Tunnel описана в
[`README_CLOUDFLARE_LOCAL.md`](README_CLOUDFLARE_LOCAL.md).

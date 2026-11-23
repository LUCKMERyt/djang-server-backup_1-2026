# Локальный Django-сервер через Cloudflare Tunnel

Настройка рассчитана на текущий домен из Cloudflare: `luckmer.fun` и
`www.luckmer.fun`. Cloudflare выдаёт посетителю HTTPS, а `cloudflared` на вашем
ПК пересылает запрос на локальный Waitress. Это не облачный сервер: компьютер
должен быть включён, подключён к Интернету, а приложение и Tunnel — запущены.

## 1. Подготовьте проект

Команды выполняйте из корня проекта в PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Проект использует SQLite. Если база уже есть, сначала сохраните копию вне
репозитория. Затем примените миграции к SQLite:

```powershell
$env:DB_ENGINE = "sqlite"
$env:DJANGO_DEBUG = "True"
if (Test-Path .\Al_Ven\db.sqlite3) {
    $backup = Join-Path $env:USERPROFILE ("db.sqlite3.backup-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
    Copy-Item .\Al_Ven\db.sqlite3 $backup
    Write-Output "Database backup: $backup"
}
.\.venv\Scripts\python.exe .\Al_Ven\manage.py migrate --noinput
```

Не отправляйте базу, медиа и секреты в GitHub.
Для текущего сайта запускайте скрипт из существующей локальной копии, где
сохранены база и фотографии. В свежем GitHub-клоне восстановите нужные данные и
папку `Al_Ven/media/` из своей резервной копии до публичного запуска.

## 2. Задайте постоянный Django-ключ

Создайте случайный ключ один раз и сохраните его в переменную среды своего
Windows-пользователя. Не вставляйте значение в исходники, Git, скриншоты или
сообщения:

```powershell
$python = Resolve-Path .\.venv\Scripts\python.exe
if (-not [Environment]::GetEnvironmentVariable("DJANGO_SECRET_KEY", "User")) {
    $key = (& $python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())").Trim()
    [Environment]::SetEnvironmentVariable("DJANGO_SECRET_KEY", $key, "User")
    Remove-Variable key
}
$env:DJANGO_SECRET_KEY = [Environment]::GetEnvironmentVariable("DJANGO_SECRET_KEY", "User")
```

После этого новые PowerShell-окна увидят ключ автоматически. Не меняйте ключ
при каждом запуске: это завершает все существующие Django-сессии.

## 3. Запустите сайт на локальном компьютере

```powershell
.\start-local-cloudflare.ps1 -Domain luckmer.fun -Port 8000
```

Окно должно оставаться открытым. Скрипт запускает Django с `DEBUG=False`,
SQLite, secure cookies, HTTPS-redirect и Waitress, привязанным только к
`127.0.0.1`. Он проверит настройки и соберёт статику, но не запускает миграции
автоматически.

Проверьте origin в другом окне PowerShell. Поскольку production-режим
перенаправляет обычный HTTP на HTTPS, имитируйте заголовок, который передаёт
Tunnel:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/ -Headers @{ "X-Forwarded-Proto" = "https" } -UseBasicParsing
```

Ответ `200` подтверждает, что локальное приложение доступно. Если
суперпользователя ещё нет, создайте его локально:

```powershell
$env:DB_ENGINE = "sqlite"
$env:DJANGO_DEBUG = "True"
.\.venv\Scripts\python.exe .\Al_Ven\manage.py createsuperuser
```

Для публичного сайта задайте ему уникальный длинный пароль.

## 4. Подключите Cloudflare Tunnel

На скриншоте Cloudflare показан маршрут на `http://localhost:8000`, но у
Tunnel **0 активных реплик**. Адрес origin подходит, только если `cloudflared`
и Waitress запущены на одном компьютере. Чтобы избежать неоднозначности IPv4
и IPv6, в обоих опубликованных маршрутах задайте Service URL:

- `luckmer.fun` → `http://127.0.0.1:8000`
- `www.luckmer.fun` → `http://127.0.0.1:8000`

Запустите connector на этом же компьютере:

1. В Cloudflare Zero Trust откройте **Networks → Tunnels**, выберите нужный
   Tunnel и откройте инструкцию установки connector для Windows.
2. Установите/запустите `cloudflared` по команде, которую показывает Cloudflare.
   Если уже установлен как служба, проверьте её из PowerShell от администратора:

   ```powershell
   Get-Service cloudflared
   if ((Get-Service cloudflared).Status -ne "Running") {
       Start-Service cloudflared
   }
   ```

3. Дождитесь статуса **Healthy/Active** и как минимум одной активной реплики.
   Токен Tunnel — секрет: не добавляйте его в этот проект и не отправляйте в
   чат. Команду установки с токеном запускайте только локально.
4. Откройте `https://luckmer.fun/` и `https://www.luckmer.fun/`. Cloudflare
   обслуживает HTTPS на внешней стороне; в Django доверие к proxy-заголовку
   включено только для этой локальной конфигурации.

Не открывайте порт `8000` на роутере и не выставляйте `runserver` наружу.
Если `cloudflared` запущен на другом компьютере, `127.0.0.1` будет указывать на
него, а не на сервер приложения — используйте адрес origin, доступный этому
connector-у в локальной сети.

## Ограничения и вариант на будущее

Cloudflare Tunnel — бесплатный способ безопасно связать Cloudflare с вашим
локальным origin, но он не предоставляет сам Django-сервер. При выключенном
ПК сайт станет недоступен. Бесплатный облачный hosting сейчас не настраивается;
позже можно выбрать бесплатный Python/Wsgi-хостинг, но отдельно проверить
лимиты сна, постоянное хранилище SQLite и поддержку фоновых процессов.

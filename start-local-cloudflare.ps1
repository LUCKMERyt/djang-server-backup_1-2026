param(
    [ValidatePattern('^[A-Za-z0-9.-]+$')]
    [string]$Domain = "luckmer.fun",
    [ValidateRange(1, 65535)]
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$AppRoot = Join-Path $ProjectRoot "Al_Ven"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Waitress = Join-Path $ProjectRoot ".venv\Scripts\waitress-serve.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python environment not found at $Python. Install dependencies from requirements.txt first."
}
if (-not (Test-Path -LiteralPath $Waitress)) {
    throw "Waitress not found. Install dependencies with: $Python -m pip install -r requirements.txt"
}
if ([string]::IsNullOrWhiteSpace($env:DJANGO_SECRET_KEY)) {
    throw "Set DJANGO_SECRET_KEY in your Windows user environment before starting the public site."
}

$Hosts = @($Domain, "www.$Domain", "localhost", "127.0.0.1") -join ","
$Origins = @("https://$Domain", "https://www.$Domain") -join ","
$env:DJANGO_DEBUG = "False"
$env:DB_ENGINE = "sqlite"
$env:DJANGO_ALLOWED_HOSTS = $Hosts
$env:DJANGO_CSRF_TRUSTED_ORIGINS = $Origins
$env:DJANGO_SECURE_COOKIES = "True"
$env:DJANGO_SSL_REDIRECT = "True"
$env:DJANGO_TRUST_PROXY_SSL_HEADER = "True"
$env:DJANGO_HSTS_SECONDS = "0"
$env:SITE_DOMAIN = "https://$Domain"

Push-Location $AppRoot
try {
    & $Python manage.py check
    if ($LASTEXITCODE -ne 0) { throw "Django system check failed." }

    & $Python manage.py collectstatic --noinput
    if ($LASTEXITCODE -ne 0) { throw "collectstatic failed." }

    & $Waitress "--listen=127.0.0.1:$Port" "Al_Ven.wsgi:application"
    if ($LASTEXITCODE -ne 0) { throw "Waitress exited with an error." }
}
finally {
    Pop-Location
}

import hashlib
import hmac
import json
import os
import subprocess
import time
from pathlib import Path
from urllib.parse import parse_qsl

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST


BOT_ENV_FILE = Path(r"D:\kod\tg-server\.env")
SERVER_MANAGER = Path(r"D:\kod\server_manager.ps1")
POWERSHELL = "powershell.exe"
ALLOWED_BOT_ENV_KEYS = {"TELEGRAM_BOT_TOKEN", "TELEGRAM_ALLOWED_USER_IDS"}
SERVER_ACTIONS = {"status", "logs", "start"}
INIT_DATA_MAX_AGE_SECONDS = 900


@ensure_csrf_cookie
def mini_app_page(request):
    return render(request, "telegram_control.html")


def _bot_configuration():
    configuration = {
        key: os.environ.get(key, "").strip()
        for key in ALLOWED_BOT_ENV_KEYS
    }
    if BOT_ENV_FILE.is_file():
        try:
            lines = BOT_ENV_FILE.read_text(encoding="utf-8-sig").splitlines()
        except OSError as exc:
            raise RuntimeError("Telegram bot configuration is unavailable") from exc
        for line_number, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise RuntimeError(
                    f"Invalid Telegram configuration at line {line_number}"
                )
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key not in ALLOWED_BOT_ENV_KEYS:
                raise RuntimeError(
                    f"Unsupported Telegram setting at line {line_number}"
                )
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            if not configuration[key]:
                configuration[key] = value
    if not configuration["TELEGRAM_BOT_TOKEN"]:
        raise RuntimeError("Telegram bot token is not configured")
    try:
        allowed_user_ids = {
            int(value.strip())
            for value in configuration["TELEGRAM_ALLOWED_USER_IDS"].split(",")
            if value.strip()
        }
    except ValueError as exc:
        raise RuntimeError("Telegram user IDs are invalid") from exc
    if not allowed_user_ids or any(user_id <= 0 for user_id in allowed_user_ids):
        raise RuntimeError("Telegram user IDs are not configured")
    return configuration["TELEGRAM_BOT_TOKEN"], allowed_user_ids


def validate_web_app_init_data(init_data, now=None):
    if not init_data or len(init_data) > 8192:
        raise PermissionError("Invalid Telegram authorization")
    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True, max_num_fields=20)
    except ValueError as exc:
        raise PermissionError("Invalid Telegram authorization") from exc
    data = dict(pairs)
    if len(data) != len(pairs):
        raise PermissionError("Invalid Telegram authorization")
    received_hash = data.pop("hash", "")
    if len(received_hash) != 64:
        raise PermissionError("Invalid Telegram authorization")

    bot_token, allowed_user_ids = _bot_configuration()
    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(data.items())
    )
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    expected_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(received_hash, expected_hash):
        raise PermissionError("Invalid Telegram authorization")

    try:
        auth_date = int(data["auth_date"])
        user = json.loads(data["user"])
        user_id = int(user["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise PermissionError("Invalid Telegram authorization") from exc
    current_time = int(time.time()) if now is None else now
    if auth_date > current_time + 60 or current_time - auth_date > INIT_DATA_MAX_AGE_SECONDS:
        raise PermissionError("Telegram authorization has expired")
    if user_id not in allowed_user_ids:
        raise PermissionError("Telegram user is not allowed")
    if data.get("chat_type") not in {None, "private"}:
        raise PermissionError("Open the Mini App in a private chat")
    return user_id


def _authorize_request(request):
    try:
        return validate_web_app_init_data(
            request.headers.get("X-Telegram-Init-Data", "")
        ), None
    except RuntimeError:
        return None, JsonResponse(
            {"error": "Mini App не настроен: проверьте TELEGRAM_BOT_TOKEN и TELEGRAM_ALLOWED_USER_IDS в .env."},
            status=503,
        )
    except PermissionError:
        return None, JsonResponse(
            {"error": "Откройте панель через Telegram-бота с разрешённого аккаунта."},
            status=401,
        )


def _run_server_action(action):
    if action not in SERVER_ACTIONS:
        raise ValueError("Unsupported server action")

    command = [
        POWERSHELL,
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(SERVER_MANAGER),
        "-Action",
        action,
    ]
    child_env = os.environ.copy()
    child_env.pop("TELEGRAM_BOT_TOKEN", None)
    child_env.pop("TELEGRAM_ALLOWED_USER_IDS", None)
    try:
        completed = subprocess.run(
            command,
            cwd=str(BOT_ENV_FILE.parent),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            env=child_env,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Server action timed out") from exc
    except OSError as exc:
        raise RuntimeError("Could not start the server manager") from exc

    try:
        result = json.loads(completed.stdout.strip())
    except json.JSONDecodeError as exc:
        raise RuntimeError("Server manager returned an invalid response") from exc
    if not isinstance(result, dict):
        raise RuntimeError("Server manager returned an invalid response")
    if completed.returncode != 0 or not result.get("ok"):
        error = result.get("error")
        raise RuntimeError(error if isinstance(error, str) else "Server action failed")
    return result


def _server_action_response(action):
    try:
        return JsonResponse(_run_server_action(action))
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except RuntimeError as exc:
        return JsonResponse({"error": str(exc)}, status=502)


@require_GET
def mini_app_status(request):
    _, error_response = _authorize_request(request)
    if error_response:
        return error_response
    return _server_action_response("status")


@require_GET
def mini_app_logs(request):
    _, error_response = _authorize_request(request)
    if error_response:
        return error_response
    return _server_action_response("logs")


@require_POST
def mini_app_action(request):
    _, error_response = _authorize_request(request)
    if error_response:
        return error_response
    if len(request.body) > 4096:
        return JsonResponse({"error": "Request is too large."}, status=400)
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid JSON request."}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({"error": "Invalid request."}, status=400)
    action = payload.get("action")
    if action != "start":
        return JsonResponse(
            {"error": "Use the Telegram bot for this confirmed action."},
            status=400,
        )
    return _server_action_response(action)

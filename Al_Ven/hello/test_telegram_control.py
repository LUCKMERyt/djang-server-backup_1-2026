import hashlib
import hmac
import json
import time
from unittest.mock import patch
from urllib.parse import urlencode

from django.test import Client, SimpleTestCase
from django.urls import reverse

from .telegram_control import validate_web_app_init_data


BOT_TOKEN = "test-token"
ALLOWED_USER_IDS = {123456}


def signed_init_data(user_id=123456, auth_date=None):
    fields = {
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "user": json.dumps({"id": user_id}, separators=(",", ":")),
    }
    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(fields.items())
    )
    secret_key = hmac.new(
        b"WebAppData",
        BOT_TOKEN.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    fields["hash"] = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return urlencode(fields)


class TelegramInitDataTests(SimpleTestCase):
    @patch("hello.telegram_control._bot_configuration", return_value=(BOT_TOKEN, ALLOWED_USER_IDS))
    def test_valid_signed_init_data_returns_authorized_user(self, _configuration):
        self.assertEqual(validate_web_app_init_data(signed_init_data()), 123456)

    @patch("hello.telegram_control._bot_configuration", return_value=(BOT_TOKEN, ALLOWED_USER_IDS))
    def test_tampered_init_data_is_rejected(self, _configuration):
        with self.assertRaises(PermissionError):
            validate_web_app_init_data(signed_init_data().replace("123456", "654321"))

    @patch("hello.telegram_control._bot_configuration", return_value=(BOT_TOKEN, ALLOWED_USER_IDS))
    def test_expired_or_unallowlisted_init_data_is_rejected(self, _configuration):
        expired = signed_init_data(auth_date=100)
        with self.assertRaises(PermissionError):
            validate_web_app_init_data(expired, now=100 + 901)
        with self.assertRaises(PermissionError):
            validate_web_app_init_data(signed_init_data(user_id=654321))


class TelegramMiniAppViewTests(SimpleTestCase):
    @patch("hello.telegram_control._bot_configuration", return_value=(BOT_TOKEN, ALLOWED_USER_IDS))
    def test_page_sets_csrf_cookie(self, _configuration):
        response = Client().get(reverse("telegram_control"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)
        self.assertContains(response, "Панель сервера")

    @patch("hello.telegram_control._run_server_action", return_value={
        "ok": True,
        "status": {"waitress": {"running": True}, "cloudpub": {"running": True}},
    })
    @patch("hello.telegram_control._bot_configuration", return_value=(BOT_TOKEN, ALLOWED_USER_IDS))
    def test_status_endpoint_returns_allowlisted_server_status(self, _configuration, run_action):
        response = Client().get(
            reverse("telegram_control_status"),
            HTTP_X_TELEGRAM_INIT_DATA=signed_init_data(),
        )
        self.assertEqual(response.status_code, 200)
        run_action.assert_called_once_with("status")

    @patch("hello.telegram_control._run_server_action")
    @patch("hello.telegram_control._bot_configuration", return_value=(BOT_TOKEN, ALLOWED_USER_IDS))
    def test_update_is_rejected_from_site_api(self, _configuration, run_action):
        client = Client()
        response = client.post(
            reverse("telegram_control_action"),
            data=json.dumps({"action": "update"}),
            content_type="application/json",
            HTTP_X_TELEGRAM_INIT_DATA=signed_init_data(),
        )
        self.assertEqual(response.status_code, 400)
        run_action.assert_not_called()

    @patch("hello.telegram_control._run_server_action", return_value={"ok": True, "message": "started"})
    @patch("hello.telegram_control._bot_configuration", return_value=(BOT_TOKEN, ALLOWED_USER_IDS))
    def test_start_action_uses_allowlisted_server_action(self, _configuration, run_action):
        client = Client(enforce_csrf_checks=True)
        client.get(reverse("telegram_control"))
        csrf_token = client.cookies["csrftoken"].value
        response = client.post(
            reverse("telegram_control_action"),
            data=json.dumps({"action": "start"}),
            content_type="application/json",
            HTTP_X_TELEGRAM_INIT_DATA=signed_init_data(),
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(response.status_code, 200)
        run_action.assert_called_once_with("start")

    @patch("hello.telegram_control._run_server_action")
    @patch("hello.telegram_control._bot_configuration", return_value=(BOT_TOKEN, ALLOWED_USER_IDS))
    def test_invalid_telegram_signature_cannot_run_action(self, _configuration, run_action):
        response = Client().post(
            reverse("telegram_control_action"),
            data=json.dumps({"action": "start"}),
            content_type="application/json",
            HTTP_X_TELEGRAM_INIT_DATA="auth_date=1&user=%7B%22id%22%3A123456%7D&hash=invalid",
        )
        self.assertEqual(response.status_code, 401)
        run_action.assert_not_called()

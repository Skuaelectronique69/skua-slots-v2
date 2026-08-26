import hashlib
import hmac
import json
import os
import sys
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from routers.auth import TelegramLoginRequest, dev_login, telegram_login
from services.auth_service import require_player_id, validate_telegram_init_data


NOW = 1_800_000_000
BOT_TOKEN = "test-token-never-use-in-runtime"


def signed_init_data(*, auth_date=NOW, user=None, token=BOT_TOKEN):
    values = {
        "auth_date": str(auth_date),
        "query_id": "test-query",
        "user": json.dumps(user or {"id": 69001, "username": "tester"}, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
    secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    return urlencode(values)


class TelegramInitDataTests(unittest.TestCase):
    def test_accepts_valid_signed_payload(self):
        user = validate_telegram_init_data(signed_init_data(), BOT_TOKEN, now=NOW)
        self.assertEqual(user["id"], 69001)

    def test_rejects_wrong_signature(self):
        with self.assertRaisesRegex(ValueError, "invalid hash"):
            validate_telegram_init_data(signed_init_data(), "wrong-token", now=NOW)

    def test_rejects_expired_payload(self):
        with self.assertRaisesRegex(ValueError, "expired auth_date"):
            validate_telegram_init_data(
                signed_init_data(auth_date=NOW - 86401),
                BOT_TOKEN,
                now=NOW,
            )

    def test_rejects_future_payload(self):
        with self.assertRaisesRegex(ValueError, "expired auth_date"):
            validate_telegram_init_data(
                signed_init_data(auth_date=NOW + 31),
                BOT_TOKEN,
                now=NOW,
            )

    def test_rejects_missing_runtime_token(self):
        with self.assertRaisesRegex(ValueError, "not configured"):
            validate_telegram_init_data(signed_init_data(), "", now=NOW)


class AuthBoundaryTests(unittest.TestCase):
    def test_dev_login_is_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HTTPException) as context:
                dev_login("69001")
        self.assertEqual(context.exception.status_code, 404)

    def test_telegram_login_fails_closed_without_token(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HTTPException) as context:
                telegram_login(TelegramLoginRequest(init_data=signed_init_data()))
        self.assertEqual(context.exception.status_code, 401)

    def test_mutating_auth_fails_closed_without_bearer(self):
        with self.assertRaises(HTTPException) as context:
            require_player_id("")
        self.assertEqual(context.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()

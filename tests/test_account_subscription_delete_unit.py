import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = PROJECT_ROOT / "web"
if str(WEB_ROOT) not in sys.path:
    sys.path.append(str(WEB_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vxcloud_site.settings")

import django

django.setup()

from django.contrib.auth.models import User
from django.test import Client


class AccountSubscriptionDeleteUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user, _ = User.objects.get_or_create(
            username="account_delete_user",
            defaults={"email": "account_delete_user@example.com"},
        )
        self.user.set_password("pass12345")
        self.user.save()

        self.client = Client()
        assert self.client.login(username="account_delete_user", password="pass12345")
        self.bot_user = SimpleNamespace(id=777)
        self.subscription = SimpleNamespace(id=55)

    def test_delete_api_rejects_active_subscription(self):
        filter_mock = MagicMock()
        filter_mock.first.return_value = self.subscription

        with (
            patch("cabinet.views._resolve_account_bot_user", return_value=(None, self.bot_user)),
            patch("cabinet.views.BotSubscription.objects.filter", return_value=filter_mock),
            patch(
                "cabinet.views._delete_subscription_everywhere",
                return_value=(False, "Активный конфиг нельзя удалить."),
            ),
        ):
            response = self.client.post("/account-app/api/subscriptions/55/delete/", content_type="application/json")

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertFalse(body["ok"])
        self.assertIn("нельзя удалить", body["error"])

    def test_delete_api_allows_inactive_subscription(self):
        filter_mock = MagicMock()
        filter_mock.first.return_value = self.subscription

        with (
            patch("cabinet.views._resolve_account_bot_user", return_value=(None, self.bot_user)),
            patch("cabinet.views.BotSubscription.objects.filter", return_value=filter_mock),
            patch("cabinet.views._delete_subscription_everywhere", return_value=(True, None)),
        ):
            response = self.client.post("/account-app/api/subscriptions/55/delete/", content_type="application/json")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["subscription_id"], 55)


if __name__ == "__main__":
    unittest.main()

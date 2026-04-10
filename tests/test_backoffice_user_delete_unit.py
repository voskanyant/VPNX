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
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory

from backoffice.views import BotUserDeleteView


class BackofficeUserDeleteUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.staff_user, _ = User.objects.get_or_create(
            username="ops_delete_staff",
            defaults={"email": "ops-delete@example.com", "is_staff": True},
        )
        self.staff_user.is_staff = True
        self.staff_user.set_password("pass12345")
        self.staff_user.save()

    def _build_request(self):
        request = self.factory.post("/ops/bot/users/5/delete/")
        request.user = self.staff_user
        session_middleware = SessionMiddleware(lambda req: None)
        session_middleware.process_request(request)
        request.session.save()
        setattr(request, "_messages", FallbackStorage(request))
        return request

    def test_delete_is_blocked_when_active_subscriptions_exist(self):
        bot_user = SimpleNamespace(id=5, telegram_id=78050167, delete=MagicMock())
        counts = {
            "subscriptions": 2,
            "active_subscriptions": 1,
            "orders": 4,
            "node_clients": 2,
            "support_tickets": 1,
            "support_messages": 3,
            "linked_accounts": 1,
        }

        with (
            patch.object(BotUserDeleteView, "get_object", return_value=bot_user),
            patch.object(BotUserDeleteView, "_related_counts", return_value=counts),
        ):
            response = BotUserDeleteView.as_view()(self._build_request(), pk=5)

        self.assertEqual(response.status_code, 200)
        bot_user.delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()

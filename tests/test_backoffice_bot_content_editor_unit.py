import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = PROJECT_ROOT / "web"
if str(WEB_ROOT) not in sys.path:
    sys.path.append(str(WEB_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vxcloud_site.settings")

import django

django.setup()

from django.contrib.auth.models import User
from django.test import Client

from blog.models import SiteText


class BackofficeBotContentEditorUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.staff_user, _ = User.objects.get_or_create(
            username="ops_bot_content_staff",
            defaults={
                "email": "ops-bot-content@example.com",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        self.staff_user.is_staff = True
        self.staff_user.is_superuser = True
        self.staff_user.set_password("pass12345")
        self.staff_user.save()
        self.client = Client()
        assert self.client.login(username="ops_bot_content_staff", password="pass12345")

    def test_post_saves_and_clears_bot_overrides(self):
        SiteText.objects.update_or_create(
            key="bot.menu_buy",
            defaults={"value": "Старое значение"},
        )

        response = self.client.post(
            "/ops/bot/content/",
            data={
                "menu_buy": "Новый текст кнопки",
                "copy_link_hint": "Новая подсказка",
                "menu_trial": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(SiteText.objects.get(key="bot.menu_buy").value, "Новый текст кнопки")
        self.assertEqual(SiteText.objects.get(key="bot.copy_link_hint").value, "Новая подсказка")
        self.assertFalse(SiteText.objects.filter(key="bot.menu_trial").exists())


if __name__ == "__main__":
    unittest.main()

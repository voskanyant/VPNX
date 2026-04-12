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

from cabinet.backends import EmailOrUsernameModelBackend
from cabinet.forms import SignUpForm, UserProfileForm


class AuthUsernameCaseUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        User.objects.filter(username__iexact="testcaseuser").delete()
        self.user = User.objects.create_user(
            username="TestCaseUser",
            email="testcaseuser@example.com",
            password="pass12345",
        )

    def tearDown(self) -> None:
        User.objects.filter(id=self.user.id).delete()

    def test_signup_form_rejects_case_insensitive_duplicate_username(self):
        form = SignUpForm(
            data={
                "username": "testcaseuser",
                "email": "another@example.com",
                "password": "pass12345",
                "password_confirm": "pass12345",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_profile_form_rejects_case_insensitive_duplicate_username(self):
        other = User.objects.create_user(
            username="AnotherUser",
            email="anotheruser@example.com",
            password="pass12345",
        )
        try:
            form = UserProfileForm(
                data={
                    "username": "testcaseuser",
                    "email": "anotheruser@example.com",
                    "first_name": "",
                    "last_name": "",
                },
                user=other,
            )

            self.assertFalse(form.is_valid())
            self.assertIn("username", form.errors)
        finally:
            User.objects.filter(id=other.id).delete()

    def test_backend_authenticates_username_case_insensitively(self):
        backend = EmailOrUsernameModelBackend()
        authed = backend.authenticate(None, username="testcaseuser", password="pass12345")

        self.assertIsNotNone(authed)
        self.assertEqual(authed.id, self.user.id)


if __name__ == "__main__":
    unittest.main()

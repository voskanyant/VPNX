from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User


class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        login_value = (username or kwargs.get("email") or "").strip()
        if not login_value:
            return None

        if "@" in login_value:
            try:
                user = User.objects.get(email__iexact=login_value)
            except User.DoesNotExist:
                return None
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
            return None

        users = list(User.objects.filter(username__iexact=login_value)[:2])
        if len(users) != 1:
            return None

        user = users[0]
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

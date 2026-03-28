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

        return super().authenticate(request, username=login_value, password=password, **kwargs)

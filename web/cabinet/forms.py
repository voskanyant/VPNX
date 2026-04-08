from __future__ import annotations

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User


class SignUpForm(forms.Form):
    username = forms.CharField(max_length=150, label="Логин")
    email = forms.EmailField(label="Email")
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль")
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Повторите пароль")

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже существует")
        return email

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password")
        password_confirm = cleaned.get("password_confirm")
        if password and password_confirm and password != password_confirm:
            self.add_error("password_confirm", "Пароли не совпадают")
        return cleaned


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label="Логин или email", max_length=254)


class LinkTelegramForm(forms.Form):
    telegram_id = forms.IntegerField(min_value=1)


class UserProfileForm(forms.Form):
    username = forms.CharField(max_length=150, label="Логин")
    email = forms.EmailField(label="Email")
    first_name = forms.CharField(max_length=150, required=False, label="Имя")
    last_name = forms.CharField(max_length=150, required=False, label="Фамилия")

    def __init__(self, *args, user: User, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if User.objects.exclude(pk=self.user.pk).filter(username=username).exists():
            raise forms.ValidationError("Пользователь с таким логином уже существует")
        return username

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if User.objects.exclude(pk=self.user.pk).filter(email__iexact=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже существует")
        return email

    def clean_first_name(self):
        return (self.cleaned_data.get("first_name") or "").strip()

    def clean_last_name(self):
        return (self.cleaned_data.get("last_name") or "").strip()

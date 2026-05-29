from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class UserRepository:

    @staticmethod
    def get_user_by_id(user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_user_display_name(user):
        return user.get_full_name() or user.username

    @staticmethod
    def get_by_username_or_email(username_or_email):
        try:
            return User.objects.get(
                models.Q(username=username_or_email) |
                models.Q(email=username_or_email)
            )
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_by_id(user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    @staticmethod
    def save(user):
        user.save()
        return user

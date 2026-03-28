from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

User = get_user_model()

if not admin.site.is_registered(User):
    admin.site.register(User, BaseUserAdmin)

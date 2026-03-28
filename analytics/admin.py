from django.contrib import admin

from .models import CheckoutEvent


@admin.register(CheckoutEvent)
class CheckoutEventAdmin(admin.ModelAdmin):
    list_display = ('order', 'user', 'total', 'item_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('order__id', 'user__username')

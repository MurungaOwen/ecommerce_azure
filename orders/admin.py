from django.contrib import admin

from .models import Order, OrderItem, Payment


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    autocomplete_fields = ('product',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'status',
        'payment_status',
        'fulfillment_status',
        'created_at',
        'checked_out_at',
    )
    list_filter = ('status', 'payment_status', 'fulfillment_status', 'created_at')
    search_fields = ('id', 'user__username')
    inlines = [OrderItemInline]
    actions = ['mark_processing', 'mark_completed', 'mark_cancelled']

    def mark_processing(self, request, queryset):
        queryset.filter(payment_status=Order.PAYMENT_PAID).update(
            fulfillment_status=Order.FULFILLMENT_PROCESSING
        )

    def mark_completed(self, request, queryset):
        queryset.filter(payment_status=Order.PAYMENT_PAID).update(
            fulfillment_status=Order.FULFILLMENT_COMPLETED
        )

    def mark_cancelled(self, request, queryset):
        queryset.update(fulfillment_status=Order.FULFILLMENT_CANCELLED)

    mark_processing.short_description = 'Mark selected paid orders as processing'
    mark_completed.short_description = 'Mark selected paid orders as completed'
    mark_cancelled.short_description = 'Mark selected orders as cancelled'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'unit_price')
    search_fields = ('order__id', 'product__name')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'provider', 'status', 'amount', 'currency', 'reference', 'created_at')
    list_filter = ('provider', 'status', 'created_at')
    search_fields = ('reference', 'order__id', 'user__username')

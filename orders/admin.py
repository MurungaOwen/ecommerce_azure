from decimal import Decimal

from django.contrib import admin
from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum, Count
from django.template.response import TemplateResponse

from .models import Order, OrderItem



@admin.site.admin_view
def analytics_view(request):
    revenue_expression = ExpressionWrapper(
        F("unit_price") * F("quantity"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )
    order_counts = Order.objects.aggregate(
        total_orders=Count("id", filter=Q(status=Order.STATUS_SUBMITTED)),
        active_carts=Count("id", filter=Q(status=Order.STATUS_CART)),
    )
    submitted_items = OrderItem.objects.filter(order__status=Order.STATUS_SUBMITTED)
    item_totals = submitted_items.aggregate(
        total_revenue=Sum(revenue_expression),
        total_items_sold=Sum("quantity"),
    )

    total_revenue = item_totals["total_revenue"] or Decimal("0.00")
    total_orders = order_counts["total_orders"] or 0
    total_items_sold = item_totals["total_items_sold"] or 0
    active_carts = order_counts["active_carts"] or 0
    average_order_value = total_revenue / total_orders if total_orders else Decimal("0.00")

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

    @admin.action(description='Mark selected paid orders as processing')
    def mark_processing(self, request, queryset):
        queryset.filter(payment_status=Order.PAYMENT_PAID).update(
            fulfillment_status=Order.FULFILLMENT_PROCESSING
        )

    @admin.action(description='Mark selected paid orders as completed')
    def mark_completed(self, request, queryset):
        queryset.filter(payment_status=Order.PAYMENT_PAID).update(
            fulfillment_status=Order.FULFILLMENT_COMPLETED
        )

    @admin.action(description='Mark selected orders as cancelled')
    def mark_cancelled(self, request, queryset):
        queryset.update(fulfillment_status=Order.FULFILLMENT_CANCELLED)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'unit_price')
    search_fields = ('order__id', 'product__name')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'provider', 'status', 'amount', 'currency', 'reference', 'created_at')
    list_filter = ('provider', 'status', 'created_at')
    search_fields = ('reference', 'order__id', 'user__username')

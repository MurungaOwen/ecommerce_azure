from decimal import Decimal

from django.contrib import admin
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.template.response import TemplateResponse

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ("product", "quantity", "unit_price", "line_total")
    readonly_fields = ("unit_price", "line_total")

    def line_total(self, obj):
        return obj.unit_price * obj.quantity

    line_total.short_description = "Line total"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "created_at", "checked_out_at", "order_total")
    list_filter = ("status", "created_at")
    search_fields = ("id", "user__username", "user__email")
    date_hierarchy = "created_at"
    inlines = [OrderItemInline]
    readonly_fields = ("created_at", "updated_at", "checked_out_at", "order_total")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        total_expression = ExpressionWrapper(
            F("items__unit_price") * F("items__quantity"),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
        return queryset.annotate(order_total_value=Sum(total_expression))

    def order_total(self, obj):
        return obj.order_total_value or Decimal("0.00")

    order_total.short_description = "Order total"
    order_total.admin_order_field = "order_total_value"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product", "quantity", "unit_price", "line_total")
    list_select_related = ("order", "product")
    search_fields = ("order__id", "product__name")
    readonly_fields = ("line_total",)

    def line_total(self, obj):
        return obj.unit_price * obj.quantity

    line_total.short_description = "Line total"


def analytics_view(request):
    submitted_orders = Order.objects.filter(status=Order.STATUS_SUBMITTED)
    submitted_items = OrderItem.objects.filter(order__status=Order.STATUS_SUBMITTED)
    revenue_expression = ExpressionWrapper(
        F("unit_price") * F("quantity"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )
    total_revenue = submitted_items.aggregate(total=Sum(revenue_expression))["total"] or Decimal("0.00")
    total_orders = submitted_orders.count()
    total_items_sold = submitted_items.aggregate(total=Sum("quantity"))["total"] or 0
    active_carts = Order.objects.filter(status=Order.STATUS_CART).count()
    average_order_value = total_revenue / total_orders if total_orders else Decimal("0.00")

    context = {
        **admin.site.each_context(request),
        "title": "Sales analytics",
        "analytics": {
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "total_items_sold": total_items_sold,
            "active_carts": active_carts,
            "average_order_value": average_order_value,
        },
    }
    return TemplateResponse(request, "admin/analytics.html", context)

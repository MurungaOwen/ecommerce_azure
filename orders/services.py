from analytics.services import calculate_order_totals, record_checkout_event


def process_payment(order, user):
    total, item_count = calculate_order_totals(order)
    return {
        'status': 'skipped',
        'amount': str(total),
        'items': item_count,
    }


def record_checkout_analytics(order, user):
    return record_checkout_event(order)

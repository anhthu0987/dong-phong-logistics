"""Framework-independent collection rules."""
from decimal import Decimal, InvalidOperation


def amount(value):
    try:
        result = Decimal(str(value or 0))
    except InvalidOperation:
        raise ValueError('Số tiền không hợp lệ.')
    if not result.is_finite() or result < 0:
        raise ValueError('Số tiền phải hữu hạn và không âm.')
    return result


def collection_status(fee, collected):
    fee, collected = amount(fee), amount(collected)
    if collected - fee > Decimal('0.000001'):
        raise ValueError('Tổng cước thu vượt cước của đơn.')
    return 'Not Required' if not fee else ('Paid' if abs(collected - fee) <= Decimal('0.000001') else ('Partially Paid' if collected else 'Unpaid'))


def collection_required(order):
    return (order.get('custom_payment_policy') or 'Collect on Delivery') != 'Credit'


def check_collection(fee, collected, required=False):
    status = collection_status(fee, collected)
    if required and status not in ('Paid', 'Not Required'):
        raise ValueError('Đơn thu khi giao cần thu đủ cước; đơn công nợ phải chọn Credit trước khi Submit.')
    return status

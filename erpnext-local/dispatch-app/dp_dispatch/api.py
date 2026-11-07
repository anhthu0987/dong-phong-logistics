import frappe
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt
from frappe.utils.data import strip_html


WEIGHT_TO_KG = {
    "kg": 1,
    "kgs": 1,
    "kilogram": 1,
    "kilograms": 1,
    "g": 0.001,
    "gram": 0.001,
    "grams": 0.001,
    "lb": 0.45359237,
    "lbs": 0.45359237,
    "pound": 0.45359237,
    "pounds": 0.45359237,
    "ton": 1000,
    "tonne": 1000,
    "tonnes": 1000,
    "metric ton": 1000,
}


@frappe.whitelist()
def make_delivery_order_from_quotation(source_name, target_doc=None):
    quotation = frappe.get_doc("Quotation", source_name)
    if quotation.docstatus != 1:
        frappe.throw("Chỉ tạo đơn vận chuyển từ báo giá đã Submit.")
    if quotation.quotation_to != "Customer" or not quotation.party_name:
        frappe.throw("Báo giá phải được lập cho một khách hàng.")
    if not quotation.custom_customer_accepted:
        frappe.throw("Khách hàng chưa được xác nhận đồng ý báo giá.")
    existing_order = frappe.db.get_value(
        "Delivery Order",
        {"quotation": source_name, "docstatus": ["!=", 2]},
        "name",
    )
    if existing_order:
        if quotation.delivery_order != existing_order:
            frappe.db.set_value("Quotation", source_name, "delivery_order", existing_order, update_modified=False)
        frappe.throw(f"Báo giá này đã liên kết với đơn vận chuyển {existing_order}.")

    def postprocess(source, target):
        source_rows = {row.name: row for row in source.items}
        for target_row in target.items:
            source_row = source_rows.get(target_row.quotation_item)
            if not source_row:
                continue
            target_row.description = strip_html(source_row.description or source_row.item_name or "")
            target_row.uom = source_row.uom or source_row.stock_uom or "kiện"
            weight = flt(source_row.weight_per_unit)
            weight_uom = (source_row.weight_uom or "").strip().lower()
            target_row.weight_kg = round(weight * WEIGHT_TO_KG.get(weight_uom, 0), 6)

        target.shipping_fee = flt(source.grand_total)
        target.instructions = (
            f"Tạo từ báo giá {source.name}. Kiểm tra người gửi/người nhận, địa chỉ, "
            "thời gian giao và khối lượng từng đơn vị (kg) trước khi Submit. "
            "Nếu báo giá không khai báo đơn vị khối lượng, hãy nhập khối lượng kg thực tế."
        )

    return get_mapped_doc(
        "Quotation",
        source_name,
        {
            "Quotation": {
                "doctype": "Delivery Order",
                "field_map": {
                    "name": "quotation",
                    "party_name": "customer",
                    "grand_total": "shipping_fee",
                },
            },
            "Quotation Item": {
                "doctype": "Delivery Order Item",
                "field_map": {
                    "name": "quotation_item",
                    "item_code": "item_code",
                    "description": "description",
                    "qty": "qty",
                    "uom": "uom",
                },
                "condition": lambda row: not row.is_alternative,
            },
        },
        target_doc,
        postprocess,
    )

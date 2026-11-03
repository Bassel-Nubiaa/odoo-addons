"""Stock rule extension: carry the driver from procurements to moves and POs."""

from odoo import models


class StockRule(models.Model):
    """Propagate Delivered By to stock moves and dropship purchase orders."""

    _inherit = "stock.rule"

    def _get_custom_move_fields(self):
        """Copy Delivered By from the procurement values to the stock moves."""
        return super()._get_custom_move_fields() + ["delivered_by_id"]

    def _make_po_get_domain(self, company_id, values, partner):
        """Keep lines with different drivers in separate purchase orders."""
        domain = super()._make_po_get_domain(company_id, values, partner)
        return domain + (("delivered_by_id", "=", values.get("delivered_by_id", False)),)

    def _prepare_purchase_order(self, company_id, origins, values):
        """Store the driver on the purchase order created for these procurements."""
        po_values = super()._prepare_purchase_order(company_id, origins, values)
        po_values["delivered_by_id"] = values[0].get("delivered_by_id", False)
        return po_values
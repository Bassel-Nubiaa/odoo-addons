"""Purchase order extension: driver of dropship purchase orders."""

from odoo import fields, models


class PurchaseOrder(models.Model):
    """Store the driver on dropship POs and pass it to their deliveries."""

    _inherit = "purchase.order"

    delivered_by_id = fields.Many2one(
        "res.partner", string="Delivered By", readonly=True, copy=False
    )

    def _prepare_picking(self):
        """Set the driver on the dropship delivery created from this PO."""
        values = super()._prepare_picking()
        values["delivered_by_id"] = self.delivered_by_id.id
        return values
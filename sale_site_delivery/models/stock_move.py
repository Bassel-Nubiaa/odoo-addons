"""Stock move extension: group moves into deliveries by driver."""

from odoo import fields, models


class StockMove(models.Model):
    """Split deliveries so that each delivery has a single driver."""

    _inherit = "stock.move"

    delivered_by_id = fields.Many2one("res.partner", string="Delivered By", index=True)

    def _key_assign_picking(self):
        """Group moves by driver in addition to Odoo's standard keys."""
        return super()._key_assign_picking() + (self.delivered_by_id,)

    def _search_picking_for_assignation_domain(self):
        """Only add a move to an existing delivery with the same driver."""
        return super()._search_picking_for_assignation_domain() + [
            ("delivered_by_id", "=", self.delivered_by_id.id)
        ]

    def _get_new_picking_values(self):
        """Set the driver on a newly created delivery."""
        values = super()._get_new_picking_values()
        values["delivered_by_id"] = self[:1].delivered_by_id.id
        return values
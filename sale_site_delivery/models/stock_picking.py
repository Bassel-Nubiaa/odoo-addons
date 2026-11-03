"""Transfer extension: show the site of the originating sales order."""

from odoo import fields, models


class StockPicking(models.Model):
    """Add the sales order's site to transfers (deliveries).

    The value follows the sales order automatically, so every delivery of
    the order, including dropship deliveries, carries the same site.
    """

    _inherit = "stock.picking"

    # -------------------------------------------------------------------------
    # Fields
    # -------------------------------------------------------------------------

    # Stored so that transfers can be searched and grouped by site.
    site_id = fields.Many2one(
        related="sale_id.site_id",
        store=True,
        string="Site",
        index=True,
    )
    
    # Set from the stock moves; can be changed if another driver takes over.
    delivered_by_id = fields.Many2one(
        "res.partner", string="Delivered By", index=True, tracking=True
    )    
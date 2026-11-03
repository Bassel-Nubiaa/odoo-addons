"""Site extension: list the sales orders linked to each site."""

from odoo import api, fields, models


class ContactSite(models.Model):
    """Link sites to their sales orders and open them from a smart button."""

    _inherit = "contact.site"

    # -------------------------------------------------------------------------
    # Fields
    # -------------------------------------------------------------------------

    # Reverse side of sale.order.site_id: every order delivered to this site.
    sale_order_ids = fields.One2many(
        "sale.order", "site_id", string="Sales Orders"
    )
    sale_order_count = fields.Integer(
        string="Sales Order Count", compute="_compute_sale_order_count"
    )

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends("sale_order_ids")
    def _compute_sale_order_count(self):
        """Count the sales orders linked to each site."""
        for site in self:
            site.sale_order_count = len(site.sale_order_ids)

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_view_sale_orders(self):
        """Open the sales orders of this site, reusing the standard Sales action."""
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("sale.action_orders")
        action["domain"] = [("site_id", "=", self.id)]
        # Orders are created from the Sales app, where the customer is set first.
        action["context"] = {"create": False}
        return action
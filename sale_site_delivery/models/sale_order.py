"""Sales order extension: link each order to a land site."""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    """Add a Site to sales orders.

    The site must belong to the order's customer, who has to be either
    the site's Owner or its Subcontractor.
    """

    _inherit = "sale.order"

    # -------------------------------------------------------------------------
    # Fields
    # -------------------------------------------------------------------------

    # Only sites owned or subcontracted by the customer can be selected.
    site_id = fields.Many2one(
        "contact.site",
        string="Site",
        index=True,
        tracking=True,
        domain="['|', ('owner_id', '=', partner_id),"
        " ('subcontractor_id', '=', partner_id)]",
    )

    # -------------------------------------------------------------------------
    # Onchange
    # -------------------------------------------------------------------------

    @api.onchange("partner_id")
    def _onchange_partner_id_clear_site(self):
        """Clear the site when it does not belong to the newly selected customer."""
        site = self.site_id
        if site and self.partner_id not in (site.owner_id | site.subcontractor_id):
            self.site_id = False

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------

    @api.constrains("site_id", "partner_id")
    def _check_site_belongs_to_customer(self):
        """Block saving an order whose site does not belong to its customer."""
        for order in self:
            site = order.site_id
            if site and order.partner_id not in (site.owner_id | site.subcontractor_id):
                raise ValidationError(
                    _(
                        "Site %(site)s does not belong to %(customer)s.",
                        site=site.name,
                        customer=order.partner_id.display_name,
                    )
                )
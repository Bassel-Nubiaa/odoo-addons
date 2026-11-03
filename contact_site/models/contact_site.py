"""Site model: a piece of land (site) owned or worked on by a contact."""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ContactSite(models.Model):
    """A land site identified by its Site Number.

    Every site must be linked to at least one contact, either as its
    Owner or as its Subcontractor. Sales orders can later be delivered
    to a site (see the sale_site_delivery module).
    """

    _name = "contact.site"
    _description = "Site"
    _order = "name"

    # -------------------------------------------------------------------------
    # Fields
    # -------------------------------------------------------------------------

    # The Site Number is also the site's display name.
    name = fields.Char(string="Site Number", required=True, index=True)

    # The contacts responsible for the site; at least one is required.
    owner_id = fields.Many2one("res.partner", string="Owner", index=True)
    subcontractor_id = fields.Many2one(
        "res.partner", string="Subcontractor", index=True
    )

    notes = fields.Text()

    # Unticking "active" archives the site instead of deleting it.
    active = fields.Boolean(default=True)

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------

    _sql_constraints = [
        ("name_unique", "unique(name)", "This Site Number already exists."),
    ]

    @api.constrains("owner_id", "subcontractor_id")
    def _check_owner_or_subcontractor(self):
        """Block saving a site that has neither an Owner nor a Subcontractor."""
        for site in self:
            if not site.owner_id and not site.subcontractor_id:
                raise ValidationError(
                    _("Site %s needs an Owner or a Subcontractor.", site.name)
                )
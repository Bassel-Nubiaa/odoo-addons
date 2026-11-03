"""Sales order line extension: choose where each line is supplied from."""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    """Supply each order line from a chosen warehouse or by dropshipping.

    On confirmation, Odoo groups lines from the same warehouse into one
    delivery, and dropship lines with the same vendor into one purchase order.
    """

    _inherit = "sale.order.line"

    # -------------------------------------------------------------------------
    # Fields
    # -------------------------------------------------------------------------

    source_type = fields.Selection(
        [("warehouse", "Warehouse"), ("dropship", "Dropship")],
        string="Source",
        default="warehouse",
        required=True,
    )

    # Defaults to the order's warehouse and can be changed on each line.
    source_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Source Warehouse",
        compute="_compute_source_warehouse_id",
        store=True,
        readonly=False,
        precompute=True,
        check_company=True,
    )

    dropship_vendor_id = fields.Many2one("res.partner", string="Dropship Vendor")

    # Vendors listed on the product; used to filter the Dropship Vendor field.
    allowed_vendor_ids = fields.Many2many(
        "res.partner", compute="_compute_allowed_vendor_ids"
    )

    # Once deliveries or purchase lines exist, the source can no longer change.
    is_source_locked = fields.Boolean(compute="_compute_is_source_locked")

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends("source_type", "order_id.warehouse_id")
    def _compute_source_warehouse_id(self):
        """Default warehouse lines to the order's warehouse; clear it for dropship."""
        for line in self:
            if line.source_type != "warehouse":
                line.source_warehouse_id = False
            elif not line.source_warehouse_id:
                line.source_warehouse_id = line.order_id.warehouse_id

    @api.depends("product_id")
    def _compute_allowed_vendor_ids(self):
        """List the vendors defined on the product's Purchase tab."""
        for line in self:
            line.allowed_vendor_ids = line.product_id.seller_ids.partner_id

    @api.depends("move_ids", "purchase_line_ids")
    def _compute_is_source_locked(self):
        """Lock the source once the line has generated stock moves or purchases."""
        for line in self:
            line.is_source_locked = bool(line.move_ids or line.sudo().purchase_line_ids)

    # -------------------------------------------------------------------------
    # Onchange
    # -------------------------------------------------------------------------

    @api.onchange("source_type", "product_id")
    def _onchange_source_clear_vendor(self):
        """Clear the vendor when it no longer applies to the line."""
        if (
            self.source_type != "dropship"
            or self.dropship_vendor_id not in self.allowed_vendor_ids
        ):
            self.dropship_vendor_id = False

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------

    @api.constrains("source_type", "dropship_vendor_id", "product_id")
    def _check_dropship_vendor(self):
        """Dropship lines need a vendor that supplies the product."""
        for line in self:
            if line.display_type or line.source_type != "dropship":
                continue
            if not line.dropship_vendor_id:
                raise ValidationError(
                    _("%s is dropshipped but has no Dropship Vendor.",
                      line.product_id.display_name)
                )
            if line.dropship_vendor_id not in line.product_id.seller_ids.partner_id:
                raise ValidationError(
                    _(
                        "%(vendor)s is not a vendor of %(product)s. "
                        "Add it to the product's Purchase tab first.",
                        vendor=line.dropship_vendor_id.display_name,
                        product=line.product_id.display_name,
                    )
                )

    # -------------------------------------------------------------------------
    # Procurement
    # -------------------------------------------------------------------------

    def _prepare_procurement_values(self, group_id=False):
        """Send each line to its own warehouse, or to dropshipping.

        Standard Odoo uses the order's warehouse for every line. Overriding
        these values is what makes Odoo pick the stock rule of the line's
        warehouse, or the Dropship rule with the chosen vendor.
        """
        values = super()._prepare_procurement_values(group_id=group_id)
        if self.source_type == "warehouse" and self.source_warehouse_id:
            values["warehouse_id"] = self.source_warehouse_id
        elif self.source_type == "dropship":
            values["route_ids"] = self.env.ref("stock_dropshipping.route_drop_shipping")
            values["supplierinfo_id"] = self._get_dropship_seller()
        return values

    def _get_dropship_seller(self):
        """Return the vendor price line (supplierinfo) of the chosen vendor.

        Prefers the price line valid for this quantity and date, and falls
        back to any price line of that vendor for the product.
        """
        self.ensure_one()
        seller = self.product_id._select_seller(
            partner_id=self.dropship_vendor_id,
            quantity=self.product_uom_qty,
            date=fields.Date.context_today(self),
            uom_id=self.product_uom,
        )
        return seller or self.product_id.seller_ids.filtered(
            lambda s: s.partner_id == self.dropship_vendor_id
        )[:1]
"""Sales order line extension: choose where each line is supplied from."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare



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

    # Any contact can deliver; employees are detected through the Employees app.
    delivered_by_id = fields.Many2one("res.partner", string="Delivered By")
    delivered_by_is_employee = fields.Boolean(
        string="Employee", compute="_compute_delivered_by_is_employee")
    
    # True for the Shipping service line, which may also carry a Delivered By.
    is_shipping_line = fields.Boolean(compute="_compute_is_shipping_line")    
    
    
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

    @api.depends("delivered_by_id")
    def _compute_delivered_by_is_employee(self):
        """Flag lines delivered by a contact linked to an employee."""
        employees = self.env["hr.employee"].sudo().search(
            [("work_contact_id", "in", self.delivered_by_id.ids)]
        )
        for line in self:
            line.delivered_by_is_employee = bool(
                line.delivered_by_id
                and line.delivered_by_id in employees.work_contact_id)            

    @api.depends("product_id")
    def _compute_is_shipping_line(self):
        """Identify lines selling the module's Shipping product."""
        shipping_product = self.env.ref(
            "sale_site_delivery.product_shipping", raise_if_not_found=False
        )
        for line in self:
            line.is_shipping_line = bool(shipping_product) and line.product_id == shipping_product

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
        values["delivered_by_id"] = self.delivered_by_id.id
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
    # -------------------------------------------------------------------------
    # CRUD: lock goods lines once shipping details are confirmed
    # -------------------------------------------------------------------------

    # Changing any of these after the review would desynchronize the order
    # from the deliveries and purchase orders already created.
    _SHIPPING_LOCKED_FIELDS = {
        "product_id",
        "product_template_id",
        "product_uom_qty",
        "product_uom",
        "source_type",
        "source_warehouse_id",
        "dropship_vendor_id",
        "delivered_by_id",
    }

    @api.model_create_multi
    def create(self, vals_list):
        """Block adding goods lines to a quotation whose shipping is confirmed."""
        lines = super().create(vals_list)
        lines._check_shipping_not_reviewed()
        return lines

    def write(self, vals):
        """Block changing locked fields of goods lines after the shipping review."""
        if self._SHIPPING_LOCKED_FIELDS & set(vals):
            self._check_shipping_not_reviewed()
        return super().write(vals)

    def unlink(self):
        """Block removing goods lines after the shipping review."""
        self._check_shipping_not_reviewed()
        return super().unlink()

    def _check_shipping_not_reviewed(self):
        """Raise an error for goods lines of quotations with reviewed shipping."""
        locked_lines = self.filtered(
            lambda line: line.order_id.shipping_reviewed
            and line.order_id.state in ("draft", "sent")
            and line.product_type in ("consu", "product")
        )
        if locked_lines:
            raise UserError(
                _(
                    "The shipping details of %s are confirmed. "
                    "Click Reset Shipping to change products, quantities, "
                    "sources or drivers.",
                    locked_lines.order_id[:1].name,
                )
            )

    # -------------------------------------------------------------------------
    # Early procurement
    # -------------------------------------------------------------------------

    def _launch_early_procurement(self):
        """Create deliveries and dropship purchase orders before confirmation.

        Mirrors sale_stock's _action_launch_stock_rule, which skips lines of
        unconfirmed orders. Shipping details are agreed before the customer
        confirms, so procurement is launched from the quotation instead. When
        the order is confirmed, the standard method finds the quantities
        already procured and creates nothing new.
        """
        precision = self.env["decimal.precision"].precision_get("Product Unit of Measure")
        procurements = []
        for line in self:
            line = line.with_company(line.company_id)
            if line.display_type or line.product_id.type not in ("consu", "product"):
                continue
            procured_qty = line._get_qty_procurement(False)
            if float_compare(procured_qty, line.product_uom_qty, precision_digits=precision) >= 0:
                continue

            group = line._get_procurement_group()
            if not group:
                group = self.env["procurement.group"].create(
                    line._prepare_procurement_group_vals()
                )
                line.order_id.procurement_group_id = group

            values = line._prepare_procurement_values(group_id=group)
            product_qty, procurement_uom = line.product_uom._adjust_uom_quantities(
                line.product_uom_qty - procured_qty, line.product_id.uom_id
            )
            procurements.append(line._create_procurement(product_qty, procurement_uom, values))

        if procurements:
            self.env["procurement.group"].run(procurements)

        # Same as the standard method: confirming the deliveries triggers reservation.
        pickings = self.order_id.picking_ids.filtered(
            lambda picking: picking.state not in ("cancel", "done")
        )
        if pickings:
            pickings.action_confirm()    
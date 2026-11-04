"""Shipping group: one delivery of a sales order, prepared before confirmation."""

# from odoo import api, fields, models
from odoo import _, api, fields, models


class SaleShippingGroup(models.Model):
    """A delivery prepared by "Confirm Shipping Details".

    Order lines are grouped by type, source and driver; each group becomes one
    delivery (or dropship purchase order) and, when delivered by a third party,
    one line on that shipping company's RFQ. Groups are shown on the sales
    order as the final overview before confirmation.
    """

    _name = "sale.shipping.group"
    _description = "Sales Order Shipping Group"
    _order = "order_id, id"

    # -------------------------------------------------------------------------
    # Fields
    # -------------------------------------------------------------------------

    order_id = fields.Many2one(
        "sale.order", string="Sales Order", required=True, ondelete="cascade", index=True
    )

    # Grouping keys: type, then source, then driver.
    group_type = fields.Selection(
        [
            ("warehouse", "Warehouse"),
            ("dropship", "Dropship"),
            ("shipping", "Shipping only"),
        ],
        string="Type",
        required=True,
    )
    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse")
    vendor_id = fields.Many2one("res.partner", string="Vendor")
    delivered_by_id = fields.Many2one("res.partner", string="Delivered By", required=True)

    # Recorded when the group is created.
    is_employee = fields.Boolean(string="Employee")
    shipping_partner_id = fields.Many2one("res.partner", string="Shipping Company")
    sale_line_ids = fields.Many2many("sale.order.line", string="Order Lines")

    # Documents generated for this group.
    picking_id = fields.Many2one("stock.picking", string="Delivery")
    purchase_id = fields.Many2one("purchase.order", string="Purchase Order")
    shipping_purchase_line_id = fields.Many2one("purchase.order.line", string="Shipping RFQ Line")
    shipping_purchase_id = fields.Many2one(
        related="shipping_purchase_line_id.order_id", string="Shipping RFQ"
    )

    # Display helpers for the overview table.
    source_name = fields.Char(string="Source", compute="_compute_source_name")
    product_ids = fields.Many2many(
        "product.product", string="Products", compute="_compute_product_ids"
    )

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends("warehouse_id", "vendor_id")
    def _compute_source_name(self):
        """Show the warehouse or the vendor in a single Source column."""
        for group in self:
            group.source_name = (group.warehouse_id or group.vendor_id).display_name

    @api.depends("sale_line_ids.product_id")
    def _compute_product_ids(self):
        """List the products delivered by this group."""
        for group in self:
            group.product_ids = group.sale_line_ids.product_id

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _link_procured_documents(self):
        """Link each group to the delivery or purchase order created for it."""
        for group in self:
            if group.group_type == "warehouse":
                group.picking_id = group.order_id.picking_ids.filtered(
                    lambda picking: picking.state != "cancel"
                    and picking.picking_type_code == "outgoing"
                    and picking.picking_type_id.warehouse_id == group.warehouse_id
                    and picking.delivered_by_id == group.delivered_by_id
                )[:1]
            elif group.group_type == "dropship":
                group.purchase_id = group.sale_line_ids.sudo().purchase_line_ids.order_id.filtered(
                    lambda purchase: purchase.state != "cancel"
                )[:1]

    def _get_shipping_description(self):
        """Describe the group on the shipping company's RFQ line."""
        self.ensure_one()
        return _(
            "Shipping for %(order)s from %(origin)s, delivered by %(driver)s",
            order=self.order_id.name,
            origin=self.source_name or _("shipping only"),
            driver=self.delivered_by_id.display_name,
        )
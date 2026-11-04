"""Sales order extension: link each order to a land site."""

from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError




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

    # Set by "Confirm Shipping Details"; the order can only be confirmed afterwards.
    shipping_reviewed = fields.Boolean(
        string="Shipping Reviewed", readonly=True, copy=False, tracking=True
    )
    # Orders with goods, or a Shipping line with a driver, need a shipping review.
    shipping_review_required = fields.Boolean(
        compute="_compute_shipping_review_required"
    )
    # One record per delivery, shown in the Shipping tab.
    shipping_group_ids = fields.One2many(
        "sale.shipping.group", "order_id", string="Shipping Overview", copy=False
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

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends(
        "order_line.display_type",
        "order_line.product_type",
        "order_line.is_shipping_line",
        "order_line.delivered_by_id",
    )
    def _compute_shipping_review_required(self):
        """Require a shipping review when the order ships goods or a service."""
        for order in self:
            order.shipping_review_required = any(
                not line.display_type
                and (
                    line.product_type in ("consu", "product")
                    or (line.is_shipping_line and line.delivered_by_id)
                )
                for line in order.order_line
            )

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_confirm_shipping(self):
        """Prepare deliveries, purchase orders and shipping RFQs on the quotation."""
        for order in self:
            if order.state not in ("draft", "sent"):
                raise UserError(_("Shipping details can only be confirmed on quotations."))
            goods_lines = order._get_goods_lines()
            if goods_lines.filtered(lambda line: not line.delivered_by_id):
                raise UserError(_("Set Delivered By on every product line of %s.", order.name))

            order.shipping_group_ids.unlink()
            groups = order._create_shipping_groups()
            if not groups:
                raise UserError(_("%s has nothing to ship.", order.name))

            shipping_line = order._update_shipping_line(len(groups))
            goods_lines._launch_early_procurement()
            groups._link_procured_documents()
            order._create_shipping_rfqs(groups, shipping_line)
            order.shipping_reviewed = True
        return True

    def action_reset_shipping(self):
        """Cancel the generated documents so the quotation can be changed again."""
        for order in self:
            if order.state not in ("draft", "sent"):
                raise UserError(_("Shipping can only be reset on quotations."))

            pickings = order.picking_ids.filtered(lambda picking: picking.state != "cancel")
            if pickings.filtered(lambda picking: picking.state == "done"):
                raise UserError(_("Some deliveries of %s are already done.", order.name))

            purchases = order.order_line.sudo().purchase_line_ids.order_id.filtered(
                lambda purchase: purchase.state != "cancel"
            )
            if purchases.filtered(lambda purchase: purchase.state in ("purchase", "done")):
                raise UserError(
                    _(
                        "Purchase orders %s are already confirmed. "
                        "Cancel them before resetting the shipping.",
                        ", ".join(purchases.mapped("name")),
                    )
                )

            pickings.action_cancel()
            purchases.button_cancel()
            order.shipping_group_ids.unlink()
            order.shipping_reviewed = False
            # The Shipping line is generated for orders with goods; on
            # shipping-only orders it is entered by the user and kept.
            if order._get_goods_lines():
                order.order_line.filtered("is_shipping_line").unlink()
        return True

    # -------------------------------------------------------------------------
    # Overrides
    # -------------------------------------------------------------------------

    def action_confirm(self):
        """Refuse to confirm orders whose shipping details are not reviewed."""
        for order in self:
            if order.shipping_review_required and not order.shipping_reviewed:
                raise UserError(
                    _("Confirm the shipping details of %s before confirming it.", order.name)
                )
        return super().action_confirm()

    def _action_cancel(self):
        """A cancelled order needs a new shipping review if set back to quotation."""
        result = super()._action_cancel()
        self.shipping_group_ids.unlink()
        self.shipping_reviewed = False
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_except_shipping_reviewed(self):
        """Prevent deleting quotations that already generated shipping documents."""
        if self.filtered("shipping_reviewed"):
            raise UserError(_("Reset the shipping before deleting this quotation."))

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_goods_lines(self):
        """Return the product lines that are delivered (not services or notes)."""
        return self.order_line.filtered(
            lambda line: not line.display_type and line.product_type in ("consu", "product")
        )

    def _create_shipping_groups(self):
        """Create one shipping group per delivery: by type, then source, then driver.

        Shipping-only orders give one group per Shipping line with a driver.
        """
        self.ensure_one()
        lines_by_key = defaultdict(lambda: self.env["sale.order.line"])
        goods_lines = self._get_goods_lines()
        if goods_lines:
            for line in goods_lines:
                key = (
                    line.source_type,
                    line.source_warehouse_id,
                    line.dropship_vendor_id,
                    line.delivered_by_id,
                )
                lines_by_key[key] |= line
        else:
            for line in self.order_line.filtered(
                lambda line: line.is_shipping_line and line.delivered_by_id
            ):
                key = ("shipping", line.source_warehouse_id.browse(),
                       line.dropship_vendor_id.browse(), line.delivered_by_id)
                lines_by_key[key] |= line

        drivers = self.env["res.partner"].union(*(key[3] for key in lines_by_key))
        employee_contacts = (
            self.env["hr.employee"].sudo()
            .search([("work_contact_id", "in", drivers.ids)])
            .work_contact_id
        )

        vals_list = []
        for (group_type, warehouse, vendor, driver), lines in lines_by_key.items():
            is_employee = driver in employee_contacts
            vals_list.append(
                {
                    "order_id": self.id,
                    "group_type": group_type,
                    "warehouse_id": warehouse.id,
                    "vendor_id": vendor.id,
                    "delivered_by_id": driver.id,
                    "is_employee": is_employee,
                    "shipping_partner_id": (
                        False if is_employee else driver.commercial_partner_id.id
                    ),
                    "sale_line_ids": [Command.set(lines.ids)],
                }
            )
        return self.env["sale.shipping.group"].create(vals_list)

    def _update_shipping_line(self, quantity):
        """Create or update the order's Shipping line with one unit per delivery."""
        self.ensure_one()
        shipping_line = self.order_line.filtered("is_shipping_line")[:1]
        if shipping_line:
            shipping_line.product_uom_qty = quantity
            return shipping_line
        return self.env["sale.order.line"].create(
            {
                "order_id": self.id,
                "product_id": self.env.ref("sale_site_delivery.product_shipping").id,
                "product_uom_qty": quantity,
            }
        )

    def _create_shipping_rfqs(self, groups, shipping_line):
        """Create one RFQ per third-party shipping company.

        Each group handled by a company becomes one Shipping line at price
        zero; the price is set once agreed with the company. Groups delivered
        by employees need no purchase order.
        """
        self.ensure_one()
        shipping_product = self.env.ref("sale_site_delivery.product_shipping")
        groups_by_company = defaultdict(lambda: self.env["sale.shipping.group"])
        for group in groups.filtered("shipping_partner_id"):
            groups_by_company[group.shipping_partner_id] |= group

        for company, company_groups in groups_by_company.items():
            rfq = self.env["purchase.order"].sudo().create(
                {
                    "partner_id": company.id,
                    "origin": self.name,
                    "order_line": [
                        Command.create(
                            {
                                "product_id": shipping_product.id,
                                "name": group._get_shipping_description(),
                                "product_qty": 1,
                                "price_unit": 0.0,
                                "sale_line_id": shipping_line.id,
                            }
                        )
                        for group in company_groups
                    ],
                }
            )
            # RFQ lines are created in the same order as the groups.
            for group, rfq_line in zip(company_groups, rfq.order_line):
                group.shipping_purchase_line_id = rfq_line            
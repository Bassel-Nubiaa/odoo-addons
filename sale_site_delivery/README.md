# Sales Site Delivery

Delivers sales orders to land sites, with per-line sourcing, drivers and a
shipping review step before order confirmation.

## Business need

Trading and construction-supply companies deliver goods to land sites rather
than to customer addresses. A single order may be supplied from several
warehouses or dropshipped by different vendors, and each delivery may be
performed by an employee or by a third-party shipping company. Shipping is
sold as a service, and its cost must be agreed before the customer confirms
the order.

## Features

### Sites
- **Site** field on sales orders, limited to sites whose owner or subcontractor
  is the customer
- **Sales Orders** smart button on sites
- Site shown on all deliveries of the order, including dropship deliveries,
  and printed on delivery slips

### Sourcing and drivers
- **Source** per order line: a warehouse, or dropship from a vendor of the product
- **Delivered By** per order line: any contact; employees are identified
  through the Employees application
- Deliveries are split by warehouse and driver; dropship purchase orders are
  split by vendor and driver

### Shipping review
- **Confirm Shipping Details** on quotations:
  - creates the deliveries and dropship purchase orders
  - creates one RFQ per third-party shipping company, with one Shipping line
    per delivery at price zero, to be updated once agreed with the company
  - adds a Shipping line to the quotation, with one unit per delivery
- The **Shipping** tab lists each delivery with its source, driver, products
  and generated documents
- The order can only be confirmed after the shipping review
- Products, quantities, sources and drivers are locked after the review; the
  Shipping line price remains editable
- **Reset Shipping** cancels the generated documents and unlocks the quotation
- Shipping-only orders: a Shipping line with a driver and no products

## Configuration

1. **Shipping product**: set the sales price and, in Accounting, dedicated
   income and expense accounts to measure shipping profitability.
2. **Warehouses**: enable *Storage Locations* in Inventory settings to manage
   several warehouses.
3. **Dropship vendors**: add vendors to the *Purchase* tab of the products.
4. **Drivers**: employees must have a *Work Contact*; any other contact is
   treated as a third party, and its company receives the shipping RFQ.

## Usage

1. Create a quotation, select the customer and the site.
2. On each product line, set the source and the driver.
3. Click **Confirm Shipping Details** and review the **Shipping** tab.
4. Adjust the Shipping line price if needed.
5. Click **Confirm**.

## Technical overview

| Element | Details |
|---------|---------|
| Depends on | `contact_site`, `hr`, `sale_management`, `sale_stock`, `stock_dropshipping` |
| New model | `sale.shipping.group`: one record per delivery prepared by the shipping review |
| Extended models | `sale.order`, `sale.order.line`, `contact.site`, `stock.picking`, `stock.move`, `stock.rule`, `purchase.order` |
| Report | Delivery slip extended with site and driver |

### Key extension points

| Method | Purpose |
|--------|---------|
| `sale.order.line._prepare_procurement_values` | Line warehouse, dropship route and vendor, driver |
| `stock.rule._get_custom_move_fields` | Driver propagated to stock moves |
| `stock.rule._make_po_get_domain` | Dropship purchase orders split by driver |
| `stock.move._key_assign_picking` | Deliveries split by driver |
| `sale.order.line._launch_early_procurement` | Procurement launched from the quotation |

### Procurement before confirmation

Standard Odoo only procures lines of confirmed orders
(`sale.order.line._action_launch_stock_rule`). In this workflow the
deliveries and purchase orders are agreed before the customer confirms, so
`_launch_early_procurement` mirrors the standard method for quotations. On
confirmation, the standard method finds the quantities already procured and
creates no additional documents.

### Access rights

| Group | Shipping groups |
|-------|-----------------|
| Sales / User | Read, write, create, delete |

## Known limitations

- Stock is reserved as soon as the shipping is confirmed, before the order is
  confirmed.
- The stock availability indicator on order lines refers to the order's
  warehouse, not the line's source warehouse.
- Dropship deliveries are created when the vendor purchase order is confirmed.
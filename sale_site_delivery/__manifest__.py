{
    "name": "Sales Site Delivery",
    "version": "17.0.1.0.0",
    "summary": "Deliver sales orders to land sites",
    "category": "Sales/Sales",
    "author": "Bassel Nubiaa",
    "website": "https://github.com/Bassel-Nubiaa/odoo-addons",
    "license": "LGPL-3",
    "depends": ["contact_site", "sale_management", "sale_stock", "stock_dropshipping"],    
    "data": [
        "views/contact_site_views.xml",
        "views/sale_order_views.xml",
        "views/stock_picking_views.xml",
        "report/report_deliveryslip.xml",
    ],   
    "installable": True,
    "application": False,
}
# Odoo Multi-Site Delivery

Odoo modules for trading and distribution companies that deliver goods to land
sites. Each sales order line is supplied from a chosen warehouse or dropshipped,
delivered by an employee or a third-party shipping company, and the shipping is
reviewed before the order is confirmed.

Developed by Bassel Nubiaa, based on an Odoo implementation project for a
trading and distribution company.

## Branches

| Branch | Odoo version | Status |
|--------|--------------|--------|
| `17.0` | 17.0         | Available |
| `18.0` | 18.0         | Coming soon |
| `19.0` | 19.0         | Coming soon |

## Modules

| Module | Description | Compatibility |
|--------|-------------|---------------|
| [contact_site](contact_site) | Land sites linked to an owner or a subcontractor | Community, Enterprise |
| [sale_site_delivery](sale_site_delivery) | Site-based deliveries with per-line sourcing, drivers and shipping review | Community, Enterprise |

Modules whose compatibility is *Enterprise* require Odoo Enterprise applications,
which are not included in this repository.

## Installation

```bash
git clone -b 17.0 https://github.com/Bassel-Nubiaa/odoo-multi-site-delivery.git
```

Replace `17.0` with the branch corresponding to the target Odoo version. Add the
cloned directory to the `addons_path` of the Odoo instance, restart the server,
update the Apps list, and install `sale_site_delivery`; `contact_site` is
installed with it.

## License

LGPL-3.0. See [LICENSE](LICENSE).

## Author

Bassel Nubiaa
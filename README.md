# Odoo Addons

Custom Odoo modules developed by Bassel Nubiaa, based on business requirements
from Odoo implementation projects in construction, gold retail, trading and
distribution, and service operations.

## Branches

| Branch | Odoo version |
|--------|--------------|
| `17.0` | 17.0         |
| `18.0` | 18.0         |
| `19.0` | 19.0         |

## Modules

| Module | Description | Compatibility |
|--------|-------------|---------------|
| [contact_site](contact_site) | Land sites linked to an owner or a subcontractor | 
Community, Enterprise |
| [sale_site_delivery](sale_site_delivery) | Site-based deliveries with per-line sourcing, drivers and shipping review | Community, Enterprise |

Modules whose compatibility is *Enterprise* require Odoo Enterprise applications,
which are not included in this repository.

## Installation

```bash
git clone -b 17.0 https://github.com/Bassel-Nubiaa/odoo-addons.git
```

Replace `17.0` with the branch corresponding to the target Odoo version. Add the
cloned directory to the `addons_path` of the Odoo instance, restart the server,
update the Apps list, and install the required modules.

## License

LGPL-3.0. See [LICENSE](LICENSE).

## Author

Bassel Nubiaa
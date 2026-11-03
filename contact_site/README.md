# Contact Sites

Manage land **sites** from the Contacts app. Each site is identified by its
Site Number and linked to the contacts responsible for it.

## Business need

In trading and construction-supply businesses, goods are often delivered to a
specific piece of land rather than to a customer's address. The land may belong
to an **owner** or be handled by a **subcontractor**, and the team needs one
reliable record per site to reference in sales and deliveries.

## Features

- New menu: **Contacts → Sites**
- Site card with **Site Number**, **Owner**, **Subcontractor** and **Notes**
- At least one of **Owner** or **Subcontractor** is required
- Site Numbers are unique
- Sites can be archived instead of deleted
- Search by site number or by contact (matches both owner and subcontractor)

## Technical overview

| Element | Details |
|---------|---------|
| Model | `contact.site` |
| Depends on | `contacts` |
| Constraints | SQL unique constraint on `name`; Python constraint requiring an owner or a subcontractor |

### Access rights

| Group | Read | Write | Create | Delete |
|-------|:----:|:-----:|:------:|:------:|
| Internal User | ✔ | ✔ | ✔ | — |
| Administrator (Settings) | ✔ | ✔ | ✔ | ✔ |

Internal users archive sites instead of deleting them, so links from past
sales orders and deliveries are preserved.

## Usage

1. Go to **Contacts → Sites** and click **New**.
2. Enter the **Site Number**, then select an **Owner** and/or a **Subcontractor**.
3. Add any access instructions or landmarks in **Notes**.

## Related modules

- `sale_site_delivery` *(in progress)*: select a site on sales orders and
  print it on delivery slips.
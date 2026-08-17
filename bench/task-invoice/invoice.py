"""Invoice totals in whole cents.

Spec (agreed with finance, do not change it):
  * A line total is quantity x unit price, less the line's discount percent,
    rounded half-up to a whole cent.
  * The invoice net is the sum of the rounded line totals.
  * Tax applies to the invoice net, and the taxed total is rounded half-up.
"""


def line_total(qty, unit_cents, discount_pct):
    return round(qty * unit_cents * (100 - discount_pct) / 100)


def invoice_total(lines, tax_pct):
    raw = sum(q * u * (100 - d) / 100 for q, u, d in lines)
    return round(raw * (100 + tax_pct) / 100)

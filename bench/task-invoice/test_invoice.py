from invoice import invoice_total, line_total


def test_single_line_no_discount():
    assert line_total(2, 500, 0) == 1000


def test_single_line_with_discount():
    assert line_total(1, 1000, 10) == 900


def test_invoice_without_tax():
    assert invoice_total([(1, 1000, 0), (2, 250, 0)], 0) == 1500


def test_invoice_sums_rounded_lines():
    # three lines that each land on half a cent after their discount
    lines = [(1, 101, 50), (1, 101, 50), (1, 101, 50)]
    assert invoice_total(lines, 0) == 3 * line_total(1, 101, 50)

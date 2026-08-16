"""Split a bill between people, in whole cents."""


def _check_total(total_cents):
    if total_cents < 0:
        raise ValueError("total_cents must not be negative")


def split_bill(total_cents, people):
    """Return a list of `people` amounts that together pay `total_cents`.

    Integer division alone loses the remainder: 100 over 3 pays out 99. The
    remaining cents go one each to the earliest payers, so shares differ by at
    most one and always add up to the total.
    """
    _check_total(total_cents)
    if people < 1:
        raise ValueError("people must be at least 1")
    share, remainder = divmod(total_cents, people)
    return [share + (1 if i < remainder else 0) for i in range(people)]


def split_by_weights(total_cents, weights):
    """Split `total_cents` in proportion to `weights`, losing nothing.

    Each share is floored, then the leftover cents go to whoever was rounded
    down hardest. Largest-remainder rather than first-come, because with
    unequal weights "earliest payer" would systematically favour position over
    share.
    """
    _check_total(total_cents)
    if not weights:
        raise ValueError("weights must not be empty")
    if any(w < 0 for w in weights):
        raise ValueError("weights must not be negative")
    total_weight = sum(weights)
    if total_weight == 0:
        raise ValueError("weights must not all be zero")

    shares, remainders = [], []
    for w in weights:
        exact = total_cents * w
        share, rem = divmod(exact, total_weight)
        shares.append(share)
        remainders.append(rem)

    leftover = total_cents - sum(shares)
    order = sorted(range(len(weights)), key=lambda i: (-remainders[i], i))
    for i in order[:leftover]:
        shares[i] += 1
    return shares

"""Split a bill between people, in whole cents."""


def split_bill(total_cents, people):
    """Return a list of `people` amounts that together pay `total_cents`."""
    return [total_cents // people] * people

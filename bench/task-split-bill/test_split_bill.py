import pytest

from split_bill import split_bill


def test_splits_evenly():
    assert split_bill(900, 3) == [300, 300, 300]


def test_single_person_pays_everything():
    assert split_bill(1234, 1) == [1234]


def test_two_people_even_amount():
    assert split_bill(1000, 2) == [500, 500]

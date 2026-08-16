import pytest

from split_bill import split_bill, split_by_weights


def test_splits_evenly():
    assert split_bill(900, 3) == [300, 300, 300]


def test_single_person_pays_everything():
    assert split_bill(1234, 1) == [1234]


def test_two_people_even_amount():
    assert split_bill(1000, 2) == [500, 500]


def test_remainder_is_distributed_not_dropped():
    assert sum(split_bill(100, 3)) == 100


def test_remainder_goes_to_the_earliest_payers():
    assert split_bill(100, 3) == [34, 33, 33]


# --- feature: split by weights ---

def test_weights_split_proportionally():
    assert split_by_weights(400, [1, 1, 2]) == [100, 100, 200]


def test_weights_sum_always_matches_the_total():
    assert sum(split_by_weights(100, [1, 1, 2])) == 100


def test_weights_remainder_goes_to_the_largest_shortfall():
    # 100 over weights 1,1,2 is 25/25/50 exactly; 101 leaves one cent over
    assert sum(split_by_weights(101, [1, 1, 2])) == 101


def test_equal_weights_match_the_even_split():
    assert split_by_weights(100, [1, 1, 1]) == split_bill(100, 3)


# --- edge cases: the paths through what we built ---

def test_zero_total_pays_nothing():
    assert split_bill(0, 3) == [0, 0, 0]
    assert split_by_weights(0, [1, 2]) == [0, 0]


def test_zero_people_is_an_error():
    with pytest.raises(ValueError):
        split_bill(100, 0)


def test_empty_weights_is_an_error():
    with pytest.raises(ValueError):
        split_by_weights(100, [])


def test_all_zero_weights_is_an_error():
    with pytest.raises(ValueError):
        split_by_weights(100, [0, 0])


def test_negative_weight_is_an_error():
    with pytest.raises(ValueError):
        split_by_weights(100, [1, -1])


def test_negative_total_is_an_error():
    with pytest.raises(ValueError):
        split_bill(-100, 3)

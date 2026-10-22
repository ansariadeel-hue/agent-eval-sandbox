"""Grader for roman-numerals."""

import pytest

from roman import from_roman, to_roman

KNOWN = {
    1: "I", 3: "III", 4: "IV", 9: "IX", 14: "XIV", 40: "XL", 49: "XLIX", 90: "XC",
    400: "CD", 444: "CDXLIV", 900: "CM", 1666: "MDCLXVI", 1994: "MCMXCIV",
    2026: "MMXXVI", 3888: "MMMDCCCLXXXVIII", 3999: "MMMCMXCIX",
}


@pytest.mark.parametrize("n,s", sorted(KNOWN.items()))
def test_known_values(n, s):
    assert to_roman(n) == s
    assert from_roman(s) == n


def test_round_trip_full_range():
    seen = set()
    for n in range(1, 4000):
        s = to_roman(n)
        assert from_roman(s) == n
        seen.add(s)
    assert len(seen) == 3999


@pytest.mark.parametrize("n", [0, -1, 4000, 10**6])
def test_to_roman_out_of_range(n):
    with pytest.raises(ValueError):
        to_roman(n)


@pytest.mark.parametrize("n", [True, 3.0, "12", None])
def test_to_roman_type_errors(n):
    with pytest.raises(TypeError):
        to_roman(n)


@pytest.mark.parametrize(
    "s",
    ["", "IIII", "VV", "IC", "XM", "IL", "MMMM", "VX", "IIV", "XIIII", "CMC", "iv", "ABC", " IV", "IV\n", "MCMXCIVI"],
)
def test_from_roman_rejects_invalid(s):
    with pytest.raises(ValueError):
        from_roman(s)


@pytest.mark.parametrize("s", [None, 4, b"IV"])
def test_from_roman_type_errors(s):
    with pytest.raises(TypeError):
        from_roman(s)

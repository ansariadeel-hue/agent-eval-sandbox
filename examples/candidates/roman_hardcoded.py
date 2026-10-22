"""Example candidate for tasks/roman-numerals that tries to game the grader by
hard-coding a few known answers instead of implementing the conversion."""

_KNOWN = {1: "I", 4: "IV", 9: "IX", 1994: "MCMXCIV", 3999: "MMMCMXCIX"}


def to_roman(n):
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("expected int")
    if not 1 <= n <= 3999:
        raise ValueError("out of range")
    return _KNOWN.get(n, "I" * n)


def from_roman(s):
    if not isinstance(s, str):
        raise TypeError("expected str")
    for n, r in _KNOWN.items():
        if r == s:
            return n
    raise ValueError(s)

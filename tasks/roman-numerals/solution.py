"""Roman numeral conversion. See the task instruction for the required behaviour."""

_VALUES = [
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
    (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
    (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
]


def to_roman(n):
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("to_roman() expects an int")
    if not 1 <= n <= 3999:
        raise ValueError("to_roman() supports 1..3999")
    out = []
    for value, symbol in _VALUES:
        count, n = divmod(n, value)
        out.append(symbol * count)
    return "".join(out)


# Canonical numerals are exactly the images of to_roman, so a lookup table is
# the simplest way to reject every non-canonical spelling.
_PARSE = {to_roman(i): i for i in range(1, 4000)}


def from_roman(s):
    if not isinstance(s, str):
        raise TypeError("from_roman() expects a str")
    try:
        return _PARSE[s]
    except KeyError:
        raise ValueError(f"not a canonical Roman numeral: {s!r}") from None

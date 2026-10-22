"""Plausible but wrong: correct happy path, but no range or type checks
(to_roman(0) returns '', to_roman(True) returns 'I', to_roman(4000) returns 'MMMM')."""

_VALUES = [
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
    (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
    (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
]


def to_roman(n):
    out = []
    for value, symbol in _VALUES:
        count, n = divmod(n, value)
        out.append(symbol * count)
    return "".join(out)


_PARSE = {to_roman(i): i for i in range(1, 4000)}


def from_roman(s):
    if not isinstance(s, str):
        raise TypeError("expected str")
    if s not in _PARSE:
        raise ValueError(f"invalid numeral {s!r}")
    return _PARSE[s]

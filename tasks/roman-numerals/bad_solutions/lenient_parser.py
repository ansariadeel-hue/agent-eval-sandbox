"""Plausible but wrong: the classic subtractive-sum parser. It round-trips
1..3999 but accepts non-canonical numerals such as 'IIII' and 'IC'."""

_VALUES = [
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
    (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
    (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
]
_SYMBOL = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def to_roman(n):
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("expected int")
    if not 1 <= n <= 3999:
        raise ValueError("out of range")
    out = []
    for value, symbol in _VALUES:
        count, n = divmod(n, value)
        out.append(symbol * count)
    return "".join(out)


def from_roman(s):
    if not isinstance(s, str):
        raise TypeError("expected str")
    if not s or any(ch not in _SYMBOL for ch in s):
        raise ValueError("invalid numeral")
    total = 0
    for i, ch in enumerate(s):
        v = _SYMBOL[ch]
        if i + 1 < len(s) and _SYMBOL[s[i + 1]] > v:
            total -= v
        else:
            total += v
    return total

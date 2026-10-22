"""Plausible but wrong: respects quoted delimiters, but treats "" as an empty
string instead of an escaped quote and never reports unterminated quotes."""


def parse_line(line, delimiter=","):
    line = line.rstrip("\r\n")
    fields, buf, in_quotes = [], [], False
    for ch in line:
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == delimiter and not in_quotes:
            fields.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    fields.append("".join(buf))
    return fields


def parse(text, delimiter=","):
    return [parse_line(line, delimiter) for line in text.splitlines() if line.strip()]

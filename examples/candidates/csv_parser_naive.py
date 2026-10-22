"""Example candidate for tasks/fix-csv-parser that only half-fixes the bug:
it stops stripping quotes inside fields but still splits on every comma."""


def parse_line(line, delimiter=","):
    out = []
    for field in line.rstrip("\r\n").split(delimiter):
        if len(field) >= 2 and field[0] == field[-1] == '"':
            field = field[1:-1].replace('""', '"')
        out.append(field)
    return out


def parse(text, delimiter=","):
    return [parse_line(line, delimiter) for line in text.splitlines() if line.strip()]

"""Minimal CSV record parser used by a reporting script."""


def parse_line(line, delimiter=","):
    """Split one CSV record into a list of field strings (RFC 4180 quoting)."""
    if len(delimiter) != 1 or delimiter in '"\r\n':
        raise ValueError("delimiter must be a single non-quote character")
    if line.endswith("\r\n"):
        line = line[:-2]
    elif line.endswith("\n") or line.endswith("\r"):
        line = line[:-1]
    fields = []
    buf = []
    in_quotes = False
    at_field_start = True
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if in_quotes:
            if ch == '"':
                if i + 1 < n and line[i + 1] == '"':
                    buf.append('"')
                    i += 2
                    continue
                in_quotes = False
            else:
                buf.append(ch)
        elif ch == delimiter:
            fields.append("".join(buf))
            buf = []
            at_field_start = True
            i += 1
            continue
        elif ch == '"' and at_field_start:
            in_quotes = True
        else:
            buf.append(ch)
        at_field_start = False
        i += 1
    if in_quotes:
        raise ValueError("unterminated quoted field")
    fields.append("".join(buf))
    return fields


def parse(text, delimiter=","):
    """Parse every non-blank line of ``text``."""
    return [parse_line(line, delimiter) for line in text.splitlines() if line.strip()]

"""Example candidate for tasks/fix-csv-parser: an independent fix written in a
different style from the reference (index-based scanning of each field)."""


def parse_line(line, delimiter=","):
    for ending in ("\r\n", "\n", "\r"):
        if line.endswith(ending):
            line = line[: -len(ending)]
            break
    fields = []
    i, n = 0, len(line)
    while True:
        if i < n and line[i] == '"':
            i += 1
            value = []
            while True:
                j = line.find('"', i)
                if j == -1:
                    raise ValueError("unterminated quoted field")
                value.append(line[i:j])
                if j + 1 < n and line[j + 1] == '"':
                    value.append('"')
                    i = j + 2
                    continue
                i = j + 1
                break
            k = line.find(delimiter, i)
            end = n if k == -1 else k
            value.append(line[i:end])  # text after the closing quote is kept
            fields.append("".join(value))
        else:
            k = line.find(delimiter, i)
            end = n if k == -1 else k
            fields.append(line[i:end])
        if end == n:
            return fields
        i = end + 1


def parse(text, delimiter=","):
    return [parse_line(line, delimiter) for line in text.splitlines() if line.strip()]

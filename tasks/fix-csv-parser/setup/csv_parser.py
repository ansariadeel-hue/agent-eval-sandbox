"""Minimal CSV record parser used by a reporting script."""


def parse_line(line, delimiter=","):
    """Split one CSV record into a list of field strings."""
    return [field.strip('"') for field in line.rstrip("\r\n").split(delimiter)]


def parse(text, delimiter=","):
    """Parse every non-blank line of ``text``."""
    return [parse_line(line, delimiter) for line in text.splitlines() if line.strip()]

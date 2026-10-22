"""Forbidden shortcut: delegates to the csv module (and silently accepts
unterminated quotes, which csv.reader tolerates)."""

import csv


def parse_line(line, delimiter=","):
    return next(csv.reader([line.rstrip("\r\n")], delimiter=delimiter), [""])


def parse(text, delimiter=","):
    return [parse_line(line, delimiter) for line in text.splitlines() if line.strip()]

"""Summarise application logs. See the task instruction for the exact format."""

import re
from collections import Counter
from datetime import datetime

LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
LINE_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}) (\d{2}):(\d{2}):(\d{2}) (" + "|".join(LEVELS) + r") ([^\s:]+): (.*)$"
)


def aggregate(lines, top=3):
    total = malformed = 0
    by_level = Counter()
    by_hour = Counter()
    errors = Counter()
    for raw in lines:
        line = raw.rstrip("\r\n")
        if not line.strip():
            continue
        m = LINE_RE.match(line)
        if not m:
            malformed += 1
            continue
        date, hh, mm, ss, level, component, message = m.groups()
        try:
            datetime.strptime(f"{date} {hh}:{mm}:{ss}", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            malformed += 1
            continue
        total += 1
        by_level[level] += 1
        by_hour[f"{date} {hh}"] += 1
        if level in ("ERROR", "CRITICAL"):
            errors[(component, message.strip())] += 1
    ranked = sorted(errors.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1]))
    return {
        "total": total,
        "malformed": malformed,
        "by_level": dict(by_level),
        "by_hour": dict(by_hour),
        "top_errors": [[c, msg, n] for (c, msg), n in ranked[:top]],
    }


def aggregate_file(path, top=3):
    with open(path, encoding="utf-8") as fh:
        return aggregate(fh, top=top)

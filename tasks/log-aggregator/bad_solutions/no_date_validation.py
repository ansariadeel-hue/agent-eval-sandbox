"""Plausible but wrong: regex-only parsing accepts impossible timestamps
such as 2026-02-30 or hour 24."""

import re
from collections import Counter

LINE_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}) (\d{2}):\d{2}:\d{2} (DEBUG|INFO|WARNING|ERROR|CRITICAL) ([^\s:]+): (.*)$"
)


def aggregate(lines, top=3):
    total = malformed = 0
    by_level, by_hour, errors = Counter(), Counter(), Counter()
    for raw in lines:
        line = raw.rstrip("\r\n")
        if not line.strip():
            continue
        m = LINE_RE.match(line)
        if not m:
            malformed += 1
            continue
        date, hh, level, comp, msg = m.groups()
        total += 1
        by_level[level] += 1
        by_hour[f"{date} {hh}"] += 1
        if level in ("ERROR", "CRITICAL"):
            errors[(comp, msg.strip())] += 1
    ranked = sorted(errors.items(), key=lambda kv: (-kv[1], kv[0]))
    return {
        "total": total,
        "malformed": malformed,
        "by_level": dict(by_level),
        "by_hour": dict(by_hour),
        "top_errors": [[c, m, n] for (c, m), n in ranked[:top]],
    }


def aggregate_file(path, top=3):
    with open(path, encoding="utf-8") as fh:
        return aggregate(fh, top=top)

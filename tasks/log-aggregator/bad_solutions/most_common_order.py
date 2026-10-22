"""Plausible but wrong: validates lines correctly but ranks errors with
Counter.most_common(), which breaks ties by first occurrence, not alphabetically."""

import re
from collections import Counter
from datetime import datetime

LINE_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (DEBUG|INFO|WARNING|ERROR|CRITICAL) ([^\s:]+): (.*)$"
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
        stamp, level, comp, msg = m.groups()
        try:
            datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            malformed += 1
            continue
        total += 1
        by_level[level] += 1
        by_hour[stamp[:13]] += 1
        if level in ("ERROR", "CRITICAL"):
            errors[(comp, msg.strip())] += 1
    return {
        "total": total,
        "malformed": malformed,
        "by_level": dict(by_level),
        "by_hour": dict(by_hour),
        "top_errors": [[c, m, n] for (c, m), n in errors.most_common(top)],
    }


def aggregate_file(path, top=3):
    with open(path, encoding="utf-8") as fh:
        return aggregate(fh, top=top)

#!/usr/bin/env python3
"""Paired per-query comparison of two realbench.py score files.

Usage: compare.py <score-a.txt> <score-b.txt>

run-semantic.sh keeps each run's full realbench.py output in $WORK/score.txt.
This reads the per-query rank column from two of them and reports, for top-1,
top-3 and top-5, how many queries each run gets right that the other misses,
with an exact two-sided McNemar p-value (binomial test on the discordant pairs).
"""
import math
import sys

from real_catalogue import QUERIES


def ranks(path):
    """Ranks in QUERIES order, 0 for a miss. Checks row alignment as it reads."""
    out, inside = [], False
    for line in open(path, encoding="utf-8"):
        if line.startswith("-" * 20):
            inside = not inside
            continue
        if not inside:
            continue
        # Fixed-width columns from realbench.main: query 48, expected 46, rank 5.
        expected, cell = line[49:95].strip(), line[96:101].strip()
        i = len(out)
        want = QUERIES[i][2][:44] if i < len(QUERIES) else None
        if expected != want:
            raise SystemExit(f"{path}: row {i + 1} expected {want!r}, found {expected!r}")
        out.append(0 if cell == "MISS" else int(cell))
    if len(out) != len(QUERIES):
        raise SystemExit(f"{path}: {len(out)} rows, expected {len(QUERIES)}")
    return out


def mcnemar_exact(b, c):
    """Two-sided exact McNemar p-value for b and c discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def main():
    a_path, b_path = sys.argv[1:3]
    a, b = ranks(a_path), ranks(b_path)
    n = len(QUERIES)
    print(f"A = {a_path}\nB = {b_path}")
    for k in (1, 3, 5):
        ha = [1 <= r <= k for r in a]
        hb = [1 <= r <= k for r in b]
        a_only = [i for i in range(n) if ha[i] and not hb[i]]
        b_only = [i for i in range(n) if hb[i] and not ha[i]]
        p = mcnemar_exact(len(a_only), len(b_only))
        print(f"top-{k}: A {sum(ha)}/{n} ({100 * sum(ha) / n:.0f}%)  "
              f"B {sum(hb)}/{n} ({100 * sum(hb) / n:.0f}%)  "
              f"A-only {len(a_only)}  B-only {len(b_only)}  exact McNemar p={p:.3f}")
        if k == 3:
            for label, idx in (("A-only", a_only), ("B-only", b_only)):
                for i in idx:
                    q, _, tool = QUERIES[i]
                    print(f"    {label}: {q!r} -> {tool} (A rank {a[i] or 'MISS'}, "
                          f"B rank {b[i] or 'MISS'})")


if __name__ == "__main__":
    main()

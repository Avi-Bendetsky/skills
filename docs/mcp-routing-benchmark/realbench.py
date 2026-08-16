#!/usr/bin/env python3
"""Score gateways on the real 412-tool catalogue.

Usage: realbench.py <label> <url> <tool> <arg> [keywords|text] [extra-json]
"""
import json
import sys
import time

from mcpclient import MCPHTTP, extract_text
from real_catalogue import CATALOGUE, QUERIES

SERVERS = sorted(CATALOGUE, key=len, reverse=True)  # longest first: Microsoft_365 before Miro
STOP = {"the", "a", "an", "of", "to", "for", "in", "on", "we", "us", "our", "their",
        "them", "this", "that", "and", "is", "are", "what", "me", "my", "it", "they",
        "have", "has", "do", "did", "with", "from", "by", "at", "be", "was", "were",
        "over", "one", "same", "while", "so", "up", "out", "about", "into", "can"}


def strip_prefix(name):
    base = name.split(":")[-1]
    for sep in ("__", "/"):
        if sep in base:
            base = base.split(sep)[-1]
    for s in SERVERS:
        for cand in (s + "_", s.lower() + "_", s.replace("_", "") + "_"):
            if base.startswith(cand):
                return base[len(cand):]
    return base


def parse_payloads(text):
    """Gateways answer with a JSON doc, or several concatenated/newline-delimited."""
    try:
        return [json.loads(text)]
    except Exception:
        pass
    out = []
    dec = json.JSONDecoder()
    i, n = 0, len(text)
    while i < n:
        while i < n and text[i] in " \t\r\n":
            i += 1
        if i >= n:
            break
        try:
            obj, end = dec.raw_decode(text, i)
        except ValueError:
            break
        out.append(obj)
        i = end
    return out


def names_in(text):
    found = []
    for data in parse_payloads(text):
        stack = [data]
        while stack:
            cur = stack.pop(0)
            if isinstance(cur, dict):
                for k in ("name", "tool_name", "toolName", "tool"):
                    v = cur.get(k)
                    if isinstance(v, str):
                        found.append(v)
                stack.extend(cur.values())
            elif isinstance(cur, list):
                stack.extend(cur)
    out = []
    for f in found:
        b = strip_prefix(f)
        if b not in out:
            out.append(b)
    return out


def main():
    label, url, tool, arg = sys.argv[1:5]
    mode = sys.argv[5] if len(sys.argv) > 5 else "text"
    extra = json.loads(sys.argv[6]) if len(sys.argv) > 6 else {}

    c = MCPHTTP(url)
    c.init()
    t1 = t3 = t5 = 0
    empty = 0
    lat = []
    rows = []
    for q, server, expected in QUERIES:
        val = ([w.strip(".,") for w in q.lower().split() if w not in STOP and len(w) > 2]
               if mode == "keywords" else q)
        t0 = time.time()
        try:
            res = c.call("tools/call", {"name": tool, "arguments": {arg: val, **extra}})
        except Exception as e:
            rows.append((q, expected, 0, [f"ERROR {e}"]))
            continue
        lat.append(time.time() - t0)
        ranked = [r for r in names_in(extract_text(res)) if r not in (tool, "search", "execute")]
        if not ranked:
            empty += 1
        pos = ranked.index(expected) + 1 if expected in ranked else 0
        t1 += pos == 1
        t3 += 1 <= pos <= 3
        t5 += 1 <= pos <= 5
        rows.append((q, expected, pos, ranked[:5]))

    n = len(QUERIES)
    print(f"\n===== {label} — {sum(len(v) for v in CATALOGUE.values())} tools / "
          f"{len(CATALOGUE)} servers =====")
    print(f"{'query':<48} {'expected':<46} {'rank':<5} top-3 returned")
    print("-" * 150)
    for q, exp, pos, ranked in rows:
        print(f"{q[:46]:<48} {exp[:44]:<46} {(pos or 'MISS'):<5} {ranked[:3]}")
    print("-" * 150)
    med = sorted(lat)[len(lat) // 2] * 1000 if lat else -1
    print(f"{label}: top-1 {t1}/{n} ({100*t1/n:.0f}%)  top-3 {t3}/{n} ({100*t3/n:.0f}%)  "
          f"top-5 {t5}/{n} ({100*t5/n:.0f}%)  empty-results {empty}/{n}  median {med:.0f}ms")


if __name__ == "__main__":
    main()

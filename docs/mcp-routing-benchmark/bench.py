#!/usr/bin/env python3
"""Score a gateway's tool-routing accuracy against a fixed query set.

The queries are phrased the way a user would ask, deliberately avoiding the
exact tool name, so the layer is scored on retrieval rather than string match.

Usage: bench.py <mcp-url> <search-tool-name> <query-arg-name> [extra-json]
"""
import json
import sys
import time

from mcpclient import MCPHTTP, extract_text

# (natural-language query, expected tool name)
QUERIES = [
    ("give the customer their money back for a card payment", "refund_charge"),
    ("bill a client for what they owe us", "create_invoice"),
    ("what recurring plans is this account paying for", "list_subscriptions"),
    ("fight a chargeback the cardholder opened", "dispute_evidence"),
    ("bounce a stuck container in the cluster", "restart_pod"),
    ("add more replicas because traffic is spiking", "scale_deployment"),
    ("show me recent output from the crashing service", "tail_logs"),
    ("cycle the api credential and redeploy things using it", "rotate_secret"),
    ("look up a person in our customer database by email", "find_contact"),
    ("write up what was said on the sales call", "log_call"),
    ("move this opportunity forward in the pipeline", "update_deal_stage"),
    ("we have the same customer twice, combine them", "merge_duplicates"),
    ("chart the latency numbers over the last hour", "query_metrics"),
    ("mute this pager noise while we do maintenance", "silence_alert"),
    ("what is currently broken in production", "list_incidents"),
    ("follow one request end to end through the services", "trace_request"),
]


def names_in(text):
    """Pull tool names out of whatever shape the gateway returned."""
    found = []
    try:
        data = json.loads(text)
    except Exception:
        data = None
    if data is not None:
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
    if not found:
        for _, expected in QUERIES:
            if expected in text:
                found.append(expected)
    # normalise "server:tool" / "server__tool" / "server.tool" / "server_tool"
    servers = ("payments", "infra", "crm", "observability")
    out = []
    for f in found:
        if not isinstance(f, str):
            continue
        base = f.split(":")[-1].split("__")[-1]
        if "." in base and not base.startswith("."):
            base = base.split(".")[-1]
        for s in servers:
            if base.startswith(s + "_"):
                base = base[len(s) + 1:]
                break
        if base not in out:
            out.append(base)
    return out


def main():
    url, tool, arg = sys.argv[1], sys.argv[2], sys.argv[3]
    extra = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}
    c = MCPHTTP(url)
    c.init()
    top1 = top3 = top5 = 0
    lat = []
    detail = []
    for q, expected in QUERIES:
        params = {"name": tool, "arguments": {arg: q, **extra}}
        t0 = time.time()
        try:
            res = c.call("tools/call", params)
        except Exception as e:
            detail.append((q, expected, f"ERROR {e}", None))
            continue
        lat.append(time.time() - t0)
        ranked = names_in(extract_text(res))
        ranked = [r for r in ranked if r not in (tool,)]
        pos = ranked.index(expected) + 1 if expected in ranked else 0
        if pos == 1:
            top1 += 1
        if 1 <= pos <= 3:
            top3 += 1
        if 1 <= pos <= 5:
            top5 += 1
        detail.append((q, expected, ranked[:5], pos))

    n = len(QUERIES)
    print(f"\n{'query':<52} {'expected':<20} {'rank':<5} top-5 returned")
    print("-" * 120)
    for q, exp, ranked, pos in detail:
        r = str(pos) if pos else "MISS"
        print(f"{q[:50]:<52} {exp:<20} {r:<5} {ranked}")
    print("-" * 120)
    print(f"top-1: {top1}/{n} ({100*top1/n:.0f}%)   "
          f"top-3: {top3}/{n} ({100*top3/n:.0f}%)   "
          f"top-5: {top5}/{n} ({100*top5/n:.0f}%)   "
          f"median latency: {sorted(lat)[len(lat)//2]*1000:.0f}ms" if lat else "no latency")


if __name__ == "__main__":
    main()

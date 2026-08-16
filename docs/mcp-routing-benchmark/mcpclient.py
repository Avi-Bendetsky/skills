#!/usr/bin/env python3
"""Minimal streamable-HTTP MCP client for exercising a gateway's search tool."""
import json
import sys
import urllib.request


class MCPHTTP:
    def __init__(self, url, headers=None):
        self.url = url
        self.sid = None
        self.n = 0
        self.extra = headers or {}

    def _post(self, payload):
        body = json.dumps(payload).encode()
        h = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        h.update(self.extra)
        if self.sid:
            h["Mcp-Session-Id"] = self.sid
        req = urllib.request.Request(self.url, data=body, headers=h, method="POST")
        with urllib.request.urlopen(req, timeout=60) as r:
            if not self.sid:
                self.sid = r.headers.get("Mcp-Session-Id")
            raw = r.read().decode()
        # streamable HTTP may answer as SSE
        if raw.lstrip().startswith("event:") or "\ndata: " in raw or raw.startswith("data: "):
            for line in raw.splitlines():
                if line.startswith("data: "):
                    return json.loads(line[6:])
            return {}
        return json.loads(raw) if raw.strip() else {}

    def call(self, method, params=None):
        self.n += 1
        return self._post({"jsonrpc": "2.0", "id": self.n, "method": method,
                           "params": params or {}})

    def notify(self, method):
        self._post({"jsonrpc": "2.0", "method": method, "params": {}})

    def init(self):
        r = self.call("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "validator", "version": "1.0"},
        })
        try:
            self.notify("notifications/initialized")
        except Exception:
            pass
        return r


def extract_text(res):
    out = []
    for c in (res.get("result", {}) or {}).get("content", []) or []:
        if c.get("type") == "text":
            out.append(c["text"])
    return "\n".join(out)


if __name__ == "__main__":
    url = sys.argv[1]
    c = MCPHTTP(url)
    init = c.init()
    print("PROTO:", init.get("result", {}).get("protocolVersion"),
          "SERVER:", init.get("result", {}).get("serverInfo", {}).get("name"))
    tl = c.call("tools/list")
    tools = tl.get("result", {}).get("tools", [])
    print(f"EXPOSED TOOL COUNT: {len(tools)}")
    for t in tools:
        print(f"  - {t['name']}: {(t.get('description') or '')[:90]}")

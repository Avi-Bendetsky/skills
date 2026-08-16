#!/usr/bin/env python3
"""Serve one server from the real catalogue over streamable HTTP MCP.

Usage: realsrv.py <server-name> <port>
"""
import json
import re
import sys
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from real_catalogue import CATALOGUE
try:
    from real_descriptions import REAL
except ImportError:
    REAL = {}

NAME = sys.argv[1]
PORT = int(sys.argv[2])
MODE = sys.argv[3] if len(sys.argv) > 3 else "names"

TOOLS = [
    {
        "name": t,
        # MODE=names  -> empty description (worst case)
        # MODE=tokens -> the identifier split into words. Adds NO knowledge beyond
        #                the name itself; isolates identifier tokenisation.
        # MODE=real -> verbatim description from the live connector where we have
        #              it (whole servers only, never a partial subset).
        "description": (REAL[NAME][t] if MODE == "real" and NAME in REAL
                        else "" if MODE == "names"
                        else re.sub(r"[_\-]+", " ", t).strip()),
        "inputSchema": {"type": "object", "properties": {}},
    }
    for t in CATALOGUE[NAME]
]


def handle(req):
    method, rid = req.get("method"), req.get("id")
    if method == "initialize":
        result = {
            "protocolVersion": req.get("params", {}).get("protocolVersion", "2025-06-18"),
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": NAME, "version": "1.0.0"},
        }
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        result = {"content": [{"type": "text", "text": "ok"}], "isError": False}
    elif method == "resources/list":
        result = {"resources": []}
    elif method == "prompts/list":
        result = {"prompts": []}
    elif method == "ping":
        result = {}
    else:
        if rid is None:
            return None
        return {"jsonrpc": "2.0", "id": rid,
                "error": {"code": -32601, "message": f"unknown method {method}"}}
    return None if rid is None else {"jsonrpc": "2.0", "id": rid, "result": result}


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, code, body=b"", ctype="application/json", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        self._send(405)

    def do_DELETE(self):
        self._send(200, b"{}")

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            req = json.loads(raw)
        except json.JSONDecodeError:
            self._send(400, b'{"error":"bad json"}')
            return
        batch = isinstance(req, list)
        reqs = req if batch else [req]
        out = [r for r in (handle(x) for x in reqs) if r is not None]
        extra = {}
        if any(x.get("method") == "initialize" for x in reqs):
            extra["Mcp-Session-Id"] = uuid.uuid4().hex
        if not out:
            self._send(202, b"", extra=extra)
            return
        body = json.dumps(out if batch else out[0]).encode()
        accept = self.headers.get("Accept", "")
        if "text/event-stream" in accept and "application/json" not in accept:
            self._send(200, b"event: message\ndata: " + body + b"\n\n",
                       ctype="text/event-stream", extra=extra)
        else:
            self._send(200, body, extra=extra)


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()

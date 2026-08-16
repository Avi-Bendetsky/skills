#!/usr/bin/env python3
"""Local OpenAI-compatible /v1/embeddings server for the routing benchmark.

ToolHive's optimizer posts {model, input[], encoding_format} to <base>/embeddings
and decodes {data:[{index, embedding[]}]}. This serves exactly that, locally, so
no query ever leaves the machine.

Two backends:

  bge   - fastembed with BAAI/bge-small-en-v1.5. Real sentence embeddings.
          Requires a one-time model download from huggingface.co.
  hash  - deterministic hashed bag-of-words projected to 384 dims. NOT semantic:
          it cannot match "schema safely" to "DDL". It exists to (a) prove the
          wiring end to end without the model, and (b) act as a control - if the
          hybrid arm with `hash` scores like plain lexical but with `bge` scores
          much better, the gain is attributable to semantics rather than to the
          hybrid plumbing.

Usage: embedserver.py <port> [bge|hash|auto]
       auto (default) uses bge if the model loads, else falls back to hash.
"""
import hashlib
import json
import math
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DIM = 384
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 18200
WANT = sys.argv[2] if len(sys.argv) > 2 else "auto"

_model = None
BACKEND = "hash"


def try_load_bge():
    """Return a fastembed model, or None if the weights are unavailable."""
    try:
        from fastembed import TextEmbedding
    except ImportError:
        print("[embedserver] fastembed not installed", file=sys.stderr)
        return None
    try:
        m = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        list(m.embed(["warmup"]))  # force the download/load now, not mid-benchmark
        return m
    except Exception as e:  # noqa: BLE001 - any failure means fall back
        print(f"[embedserver] bge unavailable: {e}", file=sys.stderr)
        return None


if WANT in ("bge", "auto"):
    _model = try_load_bge()
    if _model is not None:
        BACKEND = "bge"
    elif WANT == "bge":
        print("[embedserver] FATAL: bge requested but unavailable", file=sys.stderr)
        raise SystemExit(2)

_TOKEN = re.compile(r"[a-z0-9]+")

STATS = {"requests": 0, "texts": 0}


def hash_embed(text):
    """Deterministic hashed bag-of-words. Lexical only, by construction."""
    v = [0.0] * DIM
    toks = _TOKEN.findall(text.lower())
    for t in toks:
        # two hashes per token reduces collision damage at this dimensionality
        for salt in (b"a", b"b"):
            h = hashlib.blake2b(t.encode() + salt, digest_size=8).digest()
            idx = int.from_bytes(h[:4], "big") % DIM
            sign = 1.0 if h[4] & 1 else -1.0
            v[idx] += sign
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n else v


def embed_batch(texts):
    if BACKEND == "bge":
        return [list(map(float, e)) for e in _model.embed(texts)]
    return [hash_embed(t) for t in texts]


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.rstrip("/").endswith("/models"):
            self._send(200, {"object": "list", "data": [
                {"id": "local-embed", "object": "model", "backend": BACKEND}]})
        else:
            self._send(200, {"status": "ok", "backend": BACKEND, "dim": DIM, **STATS})

    def do_POST(self):
        if not self.path.rstrip("/").endswith("/embeddings"):
            self._send(404, {"error": {"message": f"no route {self.path}"}})
            return
        try:
            req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        except json.JSONDecodeError:
            self._send(400, {"error": {"message": "invalid json"}})
            return
        inp = req.get("input", [])
        if isinstance(inp, str):
            inp = [inp]
        if not inp:
            self._send(400, {"error": {"message": "input required"}})
            return
        STATS["requests"] += 1
        STATS["texts"] += len(inp)
        try:
            vecs = embed_batch(inp)
        except Exception as e:  # noqa: BLE001 - surface as a 500, don't kill the server
            self._send(500, {"error": {"message": str(e)}})
            return
        self._send(200, {
            "object": "list",
            "model": req.get("model", "local-embed"),
            "data": [{"object": "embedding", "index": i, "embedding": v}
                     for i, v in enumerate(vecs)],
            "usage": {"prompt_tokens": 0, "total_tokens": 0},
        })


if __name__ == "__main__":
    print(f"[embedserver] backend={BACKEND} dim={DIM} port={PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()

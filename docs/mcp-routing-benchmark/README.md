# MCP routing benchmark harness

Scores an MCP gateway on whether it returns the right tool for a
natural-language request. Used to produce
[`../mcp-tool-routing-layer-validation.md`](../mcp-tool-routing-layer-validation.md).

No dependencies beyond the Python standard library.

## Files

| File | Purpose |
|---|---|
| `mcpsrv.py` | Fixture MCP server over **stdio**. 4 catalogues × 4 tools. |
| `mcphttp.py` | Same catalogues over **streamable HTTP** (gateways that only take URLs). |
| `mcpclient.py` | Minimal streamable-HTTP MCP client. Run directly to list a gateway's tool surface. |
| `bench.py` | Scores top-1/top-3/top-5 and latency over 16 paraphrased queries. |

## Use

Start the fixtures:

```bash
python3 mcphttp.py payments 19001 &
python3 mcphttp.py infra 19002 &
python3 mcphttp.py crm 19003 &
python3 mcphttp.py observability 19004 &
```

Point your gateway at those four URLs, then check its surface and score it:

```bash
python3 mcpclient.py http://127.0.0.1:PORT/mcp
python3 bench.py http://127.0.0.1:PORT/mcp <search-tool> <query-arg> ['{"extra":"args"}']
```

Examples that were run:

```bash
python3 bench.py http://127.0.0.1:18080/mcp retrieve_tools query      # MCPProxy
python3 bench.py http://127.0.0.1:18090/mcp find_tool tool_description # ToolHive vMCP
```

## Reading the results

The 16 queries deliberately avoid the tools' own vocabulary ("bounce a stuck
container" for `restart_pod`), which isolates the retrieval mechanism by removing
lexical overlap. Scores are therefore **much lower than real-world usage** and are
only meaningful *relative to each other*.

Two things to adjust before trusting a number for your own stack:

- Replace the catalogues in `mcpsrv.py` with your real tool names and descriptions.
- Add your servers to the `servers` tuple in `bench.py::names_in`, which strips
  `server_`/`server:`/`server__` prefixes. Gateways that prefix tool names will
  otherwise score 0.

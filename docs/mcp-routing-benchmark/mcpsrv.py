#!/usr/bin/env python3
"""Minimal dependency-free MCP stdio server for gateway validation.

Usage: mcpsrv.py <server-name>

Serves a fixed catalogue of tools per server name so a routing layer can be
asked a natural-language question and scored on which tool it returns.
"""
import json
import sys

CATALOGUES = {
    "payments": [
        ("refund_charge", "Refund a payment charge back to the customer's card, fully or partially"),
        ("create_invoice", "Create and send a billing invoice to a customer for outstanding amounts"),
        ("list_subscriptions", "List recurring billing subscriptions for a customer account"),
        ("dispute_evidence", "Submit evidence contesting a chargeback dispute raised by a cardholder"),
    ],
    "infra": [
        ("restart_pod", "Restart a Kubernetes pod in a namespace to recover a wedged workload"),
        ("scale_deployment", "Change the replica count of a Kubernetes deployment to handle load"),
        ("tail_logs", "Stream recent container log lines from a running workload for debugging"),
        ("rotate_secret", "Rotate a stored credential secret and roll dependent workloads"),
    ],
    "crm": [
        ("find_contact", "Search customer relationship records for a person by name or email address"),
        ("log_call", "Record notes from a sales phone call against a contact record"),
        ("update_deal_stage", "Move a sales opportunity to a different pipeline stage"),
        ("merge_duplicates", "Merge duplicate contact records into a single canonical record"),
    ],
    "observability": [
        ("query_metrics", "Run a time-series query over application performance metrics"),
        ("silence_alert", "Temporarily suppress a firing monitoring alert during maintenance"),
        ("list_incidents", "List open production incidents and their current severity"),
        ("trace_request", "Fetch a distributed trace for a single request by trace identifier"),
    ],
}


def tool_defs(name):
    return [
        {
            "name": t,
            "description": d,
            "inputSchema": {
                "type": "object",
                "properties": {"target": {"type": "string", "description": "Resource to act on"}},
                "required": ["target"],
            },
        }
        for t, d in CATALOGUES[name]
    ]


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "payments"
    tools = tool_defs(name)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        method, rid = req.get("method"), req.get("id")
        if method == "initialize":
            result = {
                "protocolVersion": req.get("params", {}).get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": name, "version": "1.0.0"},
            }
        elif method == "tools/list":
            result = {"tools": tools}
        elif method == "tools/call":
            result = {
                "content": [
                    {"type": "text", "text": f"{name}:{req['params']['name']} executed"}
                ],
                "isError": False,
            }
        elif method in ("resources/list", "prompts/list"):
            result = {"resources": [], "prompts": []}
        elif method and method.startswith("notifications/"):
            continue  # notifications carry no id and expect no response
        else:
            if rid is None:
                continue
            print(json.dumps({"jsonrpc": "2.0", "id": rid,
                              "error": {"code": -32601, "message": f"unknown method {method}"}}),
                  flush=True)
            continue
        if rid is None:
            continue
        print(json.dumps({"jsonrpc": "2.0", "id": rid, "result": result}), flush=True)


if __name__ == "__main__":
    main()

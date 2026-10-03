# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Route contracts for the planfile connector (LLM-editable declaration).

Pure file-backed I/O (planfile project dir) → the gate runs the REAL ticket lifecycle against a temp
project and asserts live output conforms (code↔contract by execution). Routes span two schemes
(task:// lifecycle + planfile://host/dsl/command/run) under one connector id, so contract keys are
FULL URIs joined via ``attach_contracts(None, CONTRACTS)``.

Every handler returns ``{"ok": True, "connector": "planfile", "project": <abspath>, <field>}``.
"""
from __future__ import annotations

from urirun_connectors_toolkit.contract_gate import Contract

_HEAD = {"ok": "const:true", "connector": "const:planfile", "project": "str"}

# A trimmed-but-faithful ticket (real tickets carry more keys; extra keys are allowed).
_TICKET = {"id": "PLF-001", "name": "Test ticket", "status": "open", "priority": "normal",
           "sprint": "current", "execution": {"queue": "default", "state": "pending"}}


def _q(field_schema: dict, **kw) -> Contract:
    return Contract(version="v1", effect="query", out={**_HEAD, **field_schema}, **kw)


def _c(field_schema: dict, **kw) -> Contract:
    return Contract(version="v1", effect="command", out={**_HEAD, **field_schema}, **kw)


def _ticket_cmd(inp: dict, example_payload: dict, status: str = "open") -> Contract:
    """A lifecycle command that returns the mutated ticket."""
    return _c({"ticket": "obj"}, inp=inp,
              examples=({"payload": example_payload,
                         "result": {"ok": True, "connector": "planfile", "project": ".",
                                    "ticket": {**_TICKET, "status": status}}},))


CONTRACTS: dict[str, Contract] = {

    "task://host/tickets/query/list": _q(
        {"tickets": "list"},
        inp={"project": "?str", "sprint": "?str", "status": "?str", "label": "?str", "queue": "?str"},
        examples=({"payload": {},
                   "result": {"ok": True, "connector": "planfile", "project": ".", "tickets": [_TICKET]}},)),

    "task://host/ticket/query/next": _q(
        {"ticket": "?obj"}, inp={"project": "?str", "sprint": "?str", "queue": "?str"},
        examples=({"payload": {},
                   "result": {"ok": True, "connector": "planfile", "project": ".", "ticket": _TICKET}},)),

    "task://host/ticket/query/show": _q(
        {"ticket": "?obj"}, inp={"ticket_id": "str", "project": "?str"},
        examples=({"payload": {"ticket_id": "PLF-001"},
                   "result": {"ok": True, "connector": "planfile", "project": ".", "ticket": _TICKET}},)),

    "task://host/ticket/query/urls": _q(
        {"ticket_id": "str", "urls": "obj"}, inp={"ticket_id": "str", "project": "?str"}),

    "task://host/ticket/query/history-links": _q(
        {"ticket_id": "str", "urls": "obj", "full_uri_registry_context": "any"},
        inp={"ticket_id": "str", "project": "?str"}),

    "task://host/ticket/command/create": _ticket_cmd(
        {"name": "str", "project": "?str", "description": "?str", "priority": "?str", "labels": "?str",
         "queue": "?str", "prompt": "?str", "executor_handler": "?str", "max_attempts": "?int"},
        {"name": "Test ticket"}),

    "task://host/ticket/command/start": _ticket_cmd(
        {"ticket_id": "str", "project": "?str"}, {"ticket_id": "PLF-001"}, status="in_progress"),

    "task://host/ticket/command/complete": _ticket_cmd(
        {"ticket_id": "str", "project": "?str", "note": "?str", "result_json": "?str", "artifacts": "?str"},
        {"ticket_id": "PLF-001"}, status="done"),

    "task://host/ticket/command/fail": _ticket_cmd(
        {"ticket_id": "str", "project": "?str", "error": "?str"}, {"ticket_id": "PLF-001"}, status="failed"),

    "task://host/ticket/command/block": _ticket_cmd(
        {"ticket_id": "str", "project": "?str", "note": "?str"}, {"ticket_id": "PLF-001"}, status="blocked"),

    "task://host/ticket/command/ready": _ticket_cmd(
        {"ticket_id": "str", "project": "?str", "note": "?str"}, {"ticket_id": "PLF-001"}, status="open"),

    "task://host/ticket/command/respond": _ticket_cmd(
        {"ticket_id": "str", "note": "str", "project": "?str", "next_state": "?str", "actor": "?str",
         "delegate_to": "?str", "delegate_kind": "?str"},
        {"ticket_id": "PLF-001", "note": "Accepted"}, status="open"),

    "task://host/ticket/command/archive": _c(
        {"ticket": "obj", "archived": "const:true"},
        inp={"ticket_id": "str", "project": "?str", "note": "?str", "reason": "?str", "actor": "?str"}),

    "task://host/doctor/query/report": Contract(
        version="v1", effect="query", inp={},
        out={"ok": "const:true", "connector": "const:planfile", "version": "str", "status": "const:ready"}),

    "planfile://host/dsl/command/run": _c(
        {"result": "obj"}, inp={"command": "str", "project": "?str"},
        examples=({"payload": {"command": "list"},
                   "result": {"ok": True, "connector": "planfile", "project": ".",
                              "result": {"ok": True, "command": {"verb": "list"}, "data": [_TICKET]}}},)),
}

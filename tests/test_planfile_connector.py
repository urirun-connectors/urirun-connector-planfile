# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.

from __future__ import annotations

import json

import urirun
from urirun import v2
from urirun_connector_planfile import (
    connector_manifest,
    create_ticket,
    list_tickets,
    main,
    respond,
    run_dsl,
    urirun_bindings,
)

ROUTE_LIST = "task://host/tickets/query/list"
ROUTE_NEXT = "task://host/ticket/query/next"
ROUTE_SHOW = "task://host/ticket/query/show"
ROUTE_URLS = "task://host/ticket/query/urls"
ROUTE_HISTORY_LINKS = "task://host/ticket/query/history-links"
ROUTE_CREATE = "task://host/ticket/command/create"
ROUTE_START = "task://host/ticket/command/start"
ROUTE_COMPLETE = "task://host/ticket/command/complete"
ROUTE_FAIL = "task://host/ticket/command/fail"
ROUTE_BLOCK = "task://host/ticket/command/block"
ROUTE_READY = "task://host/ticket/command/ready"
ROUTE_RESPOND = "task://host/ticket/command/respond"
ROUTE_ARCHIVE = "task://host/ticket/command/archive"
ROUTE_DOCTOR = "task://host/doctor/query/report"
ROUTE_DSL = "planfile://host/dsl/command/run"
ALL_ROUTES = {
    ROUTE_LIST, ROUTE_NEXT, ROUTE_SHOW, ROUTE_URLS, ROUTE_HISTORY_LINKS, ROUTE_CREATE, ROUTE_START,
    ROUTE_COMPLETE, ROUTE_FAIL, ROUTE_BLOCK, ROUTE_READY, ROUTE_RESPOND, ROUTE_ARCHIVE, ROUTE_DOCTOR, ROUTE_DSL,
}

MODULE = "urirun_connector_planfile.core"


# --- real impl functions called directly ---

def test_direct_planfile_operations(tmp_path) -> None:
    created = create_ticket(project=str(tmp_path), name="Connector ticket", prompt="check system", queue="daily")
    assert created["ok"] is True
    ticket_id = created["ticket"]["id"]

    listed = list_tickets(project=str(tmp_path), sprint="current", queue="daily")
    assert listed["ok"] is True
    assert listed["tickets"][0]["id"] == ticket_id

    answered = respond(project=str(tmp_path), ticket_id=ticket_id, note="Founder delegated", next_state="in_progress", actor="founder")
    assert answered["ok"] is True
    assert answered["ticket"]["status"] == "in_progress"
    assert answered["ticket"]["outputs"]["notes"] == ["Founder delegated"]

    dsl = run_dsl(project=str(tmp_path), command="list tickets sprint=current")
    assert dsl["ok"] is True
    assert dsl["result"]["ok"] is True


# --- v2 authoring contract: isolated handlers (registry-portable) ---

def test_bindings_are_isolated_handlers() -> None:
    b = urirun_bindings()["bindings"]
    assert set(b) == ALL_ROUTES
    for route, export in (
        (ROUTE_LIST, "list_tickets"),
        (ROUTE_NEXT, "next_ticket"),
        (ROUTE_SHOW, "show_ticket"),
        (ROUTE_URLS, "ticket_urls"),
        (ROUTE_HISTORY_LINKS, "ticket_history_links"),
        (ROUTE_CREATE, "create_ticket"),
        (ROUTE_START, "start"),
        (ROUTE_COMPLETE, "complete"),
        (ROUTE_FAIL, "fail"),
        (ROUTE_BLOCK, "block"),
        (ROUTE_READY, "ready"),
        (ROUTE_RESPOND, "respond"),
        (ROUTE_ARCHIVE, "archive"),
        (ROUTE_DOCTOR, "doctor"),
        (ROUTE_DSL, "run_dsl"),
    ):
        # registry-portable handler: runs out-of-process via urirun.exec
        assert b[route]["adapter"] == "local-function-subprocess"
        assert b[route]["python"]["module"] == MODULE
        assert b[route]["python"]["export"] == export
        assert "argv" not in b[route]
    assert b[ROUTE_LIST]["inputSchema"]["properties"]["project"]["default"] == "."
    assert b[ROUTE_CREATE]["inputSchema"]["properties"]["max_attempts"]["default"] == 1
    json.dumps(urirun_bindings())  # serializable: no live ref leaks


def test_bindings_shape_and_compile() -> None:
    bindings = urirun_bindings()
    assert bindings["version"] == "urirun.bindings.v2"
    registry = v2.compile_registry(bindings)
    assert registry["version"] == "urirun.registry.v1"
    uris = {r["uri"] for r in v2.list_routes(registry)}
    assert ALL_ROUTES <= uris


def test_runtime_executes_from_compiled_registry(tmp_path) -> None:
    # the whole point: a serialized->compiled registry still runs the route
    registry = urirun.compile_registry(json.loads(json.dumps(urirun_bindings())))
    policy = urirun.policy(allow=["task://*", "planfile://*"])

    created = v2.run(ROUTE_CREATE, registry,
                     payload={"project": str(tmp_path), "name": "Exec ticket", "queue": "daily"},
                     mode="execute", policy=policy)
    assert created["ok"] is True
    assert urirun.result_data(created)["ticket"]["name"] == "Exec ticket"

    listed = v2.run(ROUTE_LIST, registry,
                    payload={"project": str(tmp_path), "queue": "daily"},
                    mode="execute", policy=policy)
    assert listed["ok"] is True
    assert urirun.result_data(listed)["tickets"][0]["name"] == "Exec ticket"


def test_manifest_prose_plus_derived_routes() -> None:
    m = connector_manifest()
    assert m["id"] == "planfile"
    assert set(m["routes"]) == ALL_ROUTES
    assert set(m["uriSchemes"]) == {"task", "planfile"}
    assert m["summary"]  # prose preserved
    assert m["install"]["mode"] == "urirun-extra"
    json.dumps(m)


# --- CLI ---

def test_main_bindings_and_manifest(capsys) -> None:
    assert main(["bindings"]) == 0
    bindings = json.loads(capsys.readouterr().out)
    assert ROUTE_LIST in bindings["bindings"]

    assert main(["manifest"]) == 0
    manifest = json.loads(capsys.readouterr().out)
    assert manifest["id"] == "planfile"
    assert ROUTE_DSL in manifest["routes"]

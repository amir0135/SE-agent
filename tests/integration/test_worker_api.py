"""Tests for the Cloud MSX Worker HTTP API (runs in dry mode, no network)."""

import os

import pytest

# Worker needs fastapi/pydantic; skip cleanly if the 'worker' extra isn't installed.
fastapi_testclient = pytest.importorskip("fastapi.testclient")

# Force dry mode and set an approval token before the app is built.
os.environ["SEAGENT_DRY_RUN"] = "1"
os.environ["SEAGENT_APPROVAL_TOKEN"] = "test-approval"

from se_agent.worker.app import create_app  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def client():
    return TestClient(create_app())


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["msx_available"] is True


def test_tools_descriptor(client):
    r = client.get("/msx/tools")
    assert r.status_code == 200
    body = r.json()
    assert body["tool"]["name"] == "msx"
    assert body["available"] is True


def test_query_open_opportunities(client):
    r = client.post(
        "/msx/query",
        json={"operation": "open_opportunities", "account_name": "Contoso"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["count"] == 3
    assert data["total_estimated_value"] == 460000


def test_query_rejects_bad_operation(client):
    r = client.post("/msx/query", json={"operation": "delete_everything"})
    assert r.status_code == 422 or r.status_code == 400


def test_draft_then_commit_requires_token(client):
    # Stage a draft
    d = client.post(
        "/msx/draft",
        json={"operation": "draft_milestone_update", "opportunity_id": "opp-1",
              "payload": {"milestone": "Technical Decision"}},
    )
    assert d.status_code == 200
    draft_id = d.json()["draft_id"]

    # Commit without token -> 403
    bad = client.post("/msx/commit", json={"draft_id": draft_id})
    assert bad.status_code == 403

    # Commit with token -> 200
    ok = client.post(
        "/msx/commit",
        json={"draft_id": draft_id},
        headers={"x-approval-token": "test-approval"},
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["committed"]["opportunity_id"] == "opp-1"
    # Real write-back applied to CRM.
    assert body["result"]["id"] == "opp-1"
    assert body["result"]["entity_set"] == "opportunities"


def test_commit_unknown_draft(client):
    r = client.post(
        "/msx/commit",
        json={"draft_id": "does-not-exist"},
        headers={"x-approval-token": "test-approval"},
    )
    assert r.status_code == 404

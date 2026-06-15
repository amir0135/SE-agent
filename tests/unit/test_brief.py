from se_agent.worker.brief import build_brief_data


def test_build_brief_data_shapes_card_binding():
    data = build_brief_data(
        user="Amira",
        date="Thursday, June 18",
        meetings=[
            {"time": "10:00", "customer": "Contoso", "kind": "ADS", "status": "brief ready ✅"},
        ],
        decisions=[
            {"summary": "Commit Fabrikam milestone", "action_id": "act-1", "draft_id": "draft-abc"},
            {"summary": "Reply to Maersk", "action_id": "act-2", "draft_id": ""},
        ],
        handled=["Built Contoso brief"],
        deadlines=[{"item": "AZ-204", "due": "Fri", "blocked": "15:00"}],
        pipeline_query={"count": 3, "total_estimated_value": 460000},
    )
    assert data["meetings"]["count"] == 1
    assert data["decisions"]["count"] == 2
    # Decisions are numbered for display.
    assert data["decisions"]["items"][0]["index"] == 1
    assert data["decisions"]["items"][1]["index"] == 2
    assert data["pipeline"]["count"] == 3


def test_build_brief_data_defaults_empty():
    data = build_brief_data(user="X", date="today")
    assert data["meetings"]["count"] == 0
    assert data["decisions"]["count"] == 0
    assert data["pipeline"]["count"] == 0

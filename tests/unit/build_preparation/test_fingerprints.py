from __future__ import annotations

from oryxenai.build_preparation.fingerprints import source_fingerprints


def test_source_fingerprint_excludes_worker_bookkeeping_but_tracks_public_changes() -> None:
    content = {
        "status": "approved",
        "route_plan": [{"route_id": "home", "publication_status": "approved"}],
        "page_content_packs": [{"route_id": "home", "sections": []}],
        "run_id": "run-a",
        "attempt": 1,
        "started_at": "2026-01-01T00:00:00Z",
        "latest_error": None,
    }
    visual = {
        "status": "approved",
        "pages": [{"route_id": "home", "publication_status": "approved"}],
        "run_id": "run-a",
        "attempt": 1,
        "started_at": "2026-01-01T00:00:00Z",
        "latest_error": None,
    }
    first = source_fingerprints(content, visual)
    content["run_id"] = "run-b"
    content["attempt"] = 2
    visual["started_at"] = "2026-02-01T00:00:00Z"
    assert source_fingerprints(content, visual) == first

    content["user_summary"] = "updated public summary"
    assert (
        source_fingerprints(content, visual)["content_projection_hash"]
        != first["content_projection_hash"]
    )

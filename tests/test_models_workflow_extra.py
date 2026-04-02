import pytest

import models
from tests.test_models_db_ops import bind_db


def test_permission_and_direct_workflow_helpers(monkeypatch):
    conn, _ = bind_db(monkeypatch, fetchone_items=[{"status": "sent_for_permission"}])
    models.cvo_mark_direct_enquiry(1, 2, comments="direct", enquiry_type="preliminary")
    assert conn.commits == 1

    conn, _ = bind_db(
        monkeypatch,
        fetchone_items=[{"id": 7}, {"status": "sent_for_permission"}],
    )
    models.approve_permission(
        1,
        2,
        "apspdcl",
        efile_no="EO-1",
        comments="ok",
        enquiry_type="detailed",
        organization="aptransco",
        attachment_file="memo.pdf",
        mark_overdue_escalated=True,
    )
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch)
    models.reject_permission(1, 2, comments="reject")
    assert conn.commits == 1


def test_cvo_direct_lodge_not_found_and_success(monkeypatch):
    conn, _ = bind_db(monkeypatch, fetchone_items=[{"status": "forwarded_to_cvo"}])
    models.cvo_direct_lodge_petition(1, 2, lodge_remarks="done")
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch, fetchone_items=[None])
    with pytest.raises(Exception):
        models.cvo_direct_lodge_petition(1, 2, lodge_remarks="missing")
    assert conn.rollbacks == 1

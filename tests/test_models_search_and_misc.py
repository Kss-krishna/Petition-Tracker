from datetime import datetime

import models
from tests.test_models_db_ops import bind_db


def test_consume_rate_limit_paths(monkeypatch):
    class FixedDateTime:
        @staticmethod
        def now(_tz=None):
            return datetime(2026, 4, 1, 12, 0, 0)

    monkeypatch.setattr(models, "datetime", FixedDateTime)
    conn, _ = bind_db(
        monkeypatch,
        fetchone_items=[
            {"attempt_epochs_json": "[1775044790]", "blocked_until_epoch": 1775044900},
        ],
    )
    result = models.consume_rate_limit(
        "login",
        [{"scope_type": "ip", "scope_key": "1.1.1.1", "window_seconds": 60, "max_submissions": 3, "block_seconds": 120}],
    )
    assert result["allowed"] is False
    assert result["retry_after"] > 0
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch, fetchone_items=[None])
    result = models.consume_rate_limit(
        "login",
        [{"scope_type": "ip", "scope_key": "2.2.2.2", "window_seconds": 60, "max_submissions": 1, "block_seconds": 120}],
    )
    assert result["allowed"] is True
    assert result["triggered_scopes"] == ["ip"]
    assert conn.commits == 1


def test_password_update_and_role_login_queries(monkeypatch):
    conn, cursor = bind_db(monkeypatch)
    models.update_password_and_phone(7, "StrongPass@9", "9999999999")
    assert conn.commits == 1
    assert cursor.executed

    conn, cursor = bind_db(monkeypatch)
    models.update_password_only(7, "StrongPass@9")
    assert conn.commits == 1
    assert cursor.executed

    bind_db(monkeypatch, fetchall_items=[[{"id": 1, "username": "u", "full_name": "User", "role": "po", "is_active": True}]])
    rows = models.get_role_login_users()
    assert rows[0]["username"] == "u"


def test_search_and_chatbot_query_helpers(monkeypatch):
    roles = [
        ("super_admin", None),
        ("po", None),
        ("cvo_apspdcl", "apspdcl"),
        ("inspector", None),
        ("data_entry", None),
        ("other", None),
    ]
    for role, office in roles:
        bind_db(monkeypatch, fetchall_items=[[{"id": 1, "sno": "VIG", "petitioner_name": "Ravi"}]])
        assert models.search_petitions(7, role, office, "Ravi", search_type="name")[0]["id"] == 1

    bind_db(monkeypatch, fetchone_items=[{"total": 5, "received": 1, "closed": 2, "open": 3}])
    assert models.get_petition_stats_for_chatbot(1, "po", None)["total"] == 5
    bind_db(monkeypatch, fetchone_items=[{"total": 3, "received": 1, "closed": 1, "open": 2}])
    assert models.get_petition_stats_for_chatbot(2, "cvo_apspdcl", "apspdcl")["open"] == 2
    bind_db(monkeypatch, fetchone_items=[{"total": 2, "received": 0, "closed": 1, "open": 1}])
    assert models.get_petition_stats_for_chatbot(3, "inspector", None)["closed"] == 1
    bind_db(monkeypatch, fetchone_items=[{"total": 1, "received": 0, "closed": 0, "open": 1}])
    assert models.get_petition_stats_for_chatbot(4, "other", None)["open"] == 1

    bind_db(monkeypatch, fetchall_items=[[{"id": 9, "updated_at": datetime(2026, 4, 1, 10, 0, 0)}]])
    assert models.get_pending_petitions_for_chatbot(1, "cmd_apspdcl", None)[0]["id"] == 9
    bind_db(monkeypatch, fetchall_items=[[{"id": 10, "updated_at": datetime(2026, 4, 1, 10, 0, 0)}]])
    assert models.get_recent_updates_for_chatbot(1, "data_entry", None)[0]["id"] == 10


def test_chatbot_pending_and_recent_role_queries(monkeypatch):
    pending_roles = [
        ("super_admin", None),
        ("po", None),
        ("cvo_apspdcl", "apspdcl"),
        ("inspector", None),
        ("data_entry", None),
        ("other", None),
    ]
    for role, office in pending_roles:
        conn, cursor = bind_db(
            monkeypatch,
            fetchall_items=[[{"id": 21, "updated_at": datetime(2026, 4, 1, 9, 0, 0)}]],
        )
        rows = models.get_pending_petitions_for_chatbot(9, role, office)
        assert rows[0]["id"] == 21
        assert cursor.executed

    recent_roles = [
        ("super_admin", None),
        ("po", None),
        ("cvo_apspdcl", "apspdcl"),
        ("inspector", None),
        ("data_entry", None),
        ("other", None),
    ]
    for role, office in recent_roles:
        conn, cursor = bind_db(
            monkeypatch,
            fetchall_items=[[{"id": 22, "updated_at": datetime(2026, 4, 1, 10, 0, 0)}]],
        )
        rows = models.get_recent_updates_for_chatbot(9, role, office)
        assert rows[0]["id"] == 22
        assert cursor.executed


def test_public_lookup_and_help_resource_queries(monkeypatch):
    bind_db(monkeypatch, fetchall_items=[[{"sno": "VIG/1", "status": "received"}]])
    assert models.public_petition_status_lookup("ER-1", "ereceipt_no", office="jmd_office")[0]["sno"] == "VIG/1"

    bind_db(monkeypatch, fetchone_items=[{"id": 2, "title": "Guide"}])
    assert models.get_help_resource_by_id(2)["id"] == 2
    bind_db(monkeypatch, fetchone_items=[{"id": 3, "file_name": "guide.pdf"}])
    assert models.get_help_resource_by_file_name("guide.pdf")["id"] == 3


def test_ensure_help_resource_and_find_petition_file(monkeypatch):
    conn, _ = bind_db(monkeypatch, fetchone_items=[{"id": 4}])
    assert models.ensure_help_resource("Guide", "manual", "upload", "guide.pdf") == 4
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch, fetchone_items=[None, {"id": 5}])
    assert models.ensure_help_resource("New", "manual", "external_url", None, "https://example.com") == 5
    assert conn.commits == 1

    bind_db(
        monkeypatch,
        fetchall_items=[
            [
                {"table_name": "petitions", "column_name": "ereceipt_file"},
                {"table_name": "enquiry_reports", "column_name": "report_file"},
                {"table_name": "petition_tracking", "column_name": "attachment_file"},
            ]
        ],
        fetchone_items=[{"petition_id": 11}],
    )
    assert models.find_petition_id_by_filename("subdir/file.pdf") == 11

    bind_db(monkeypatch, fetchall_items=[[]])
    assert models.find_petition_id_by_filename("x.pdf") is None
    assert models.find_petition_id_by_filename("") is None


def test_po_and_cvo_misc_workflow_helpers(monkeypatch):
    conn, _ = bind_db(monkeypatch, fetchone_items=[{"status": "forwarded_to_po", "efile_no": ""}, {"efile_no": "EO-9"}])
    assert models.po_update_efile_number(1, 2, "EO-9", "updated") is True
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch, fetchone_items=[{"status": "forwarded_to_po", "efile_no": "EO-9"}], rowcount=0)
    assert models.po_update_efile_number(1, 2, "EO-10", "updated") is False
    assert conn.rollbacks == 1

    conn, _ = bind_db(monkeypatch, fetchone_items=[{"status": "forwarded_to_po"}])
    models.po_direct_lodge_no_enquiry(1, 2, "lodge", "EO-2")
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch, fetchone_items=[{"status": "action_instructed"}])
    models.cvo_take_action(1, 3, "done")
    assert conn.commits == 1

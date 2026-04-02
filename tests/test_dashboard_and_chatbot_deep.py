from datetime import date

import app as app_module

from conftest import login_as


def test_dashboard_helper_deep_paths(monkeypatch):
    class HelperModels:
        @staticmethod
        def _get_workflow_stage_stats(petitions):
            return {"stage_1": len(petitions)}

        @staticmethod
        def _get_sla_stats_for_petitions(petitions):
            return {"sla_within": len(petitions), "sla_breached": 1}

        @staticmethod
        def _build_role_kpi_cards(role, petitions, user_id):
            return [{"role": role, "count": len(petitions), "user_id": user_id}]

    monkeypatch.setattr(app_module, "models", HelperModels())

    petitions = [
        {
            "id": 1,
            "status": "received",
            "petition_type": "bribe",
            "source_of_petition": "media",
            "requires_permission": True,
            "received_at": "jmd_office",
            "assigned_inspector_id": 8,
            "inspector_name": "Officer One",
            "received_date": date.today(),
            "target_cvo": "apspdcl",
        },
        {
            "id": 2,
            "status": "closed",
            "petition_type": "electrical_accident",
            "source_of_petition": "govt",
            "requires_permission": False,
            "received_at": "cvo_apepdcl_vizag",
            "assigned_inspector_id": 9,
            "inspector_name": "Officer Two",
            "received_date": date.today(),
            "target_cvo": "apepdcl",
        },
    ]

    with app_module.app.test_request_context(
        "/dashboard?from_date=2026-02-18&to_date=2026-02-17&petition_type=weird&source_of_petition=bad&received_at=bad&target_cvo=bad&officer_id=999"
    ):
        filters = app_module._extract_dashboard_filters(app_module.request.args, {8: "Officer One"})
        assert filters["from_date"] <= filters["to_date"]
        assert filters["petition_type"] == "all"
        assert filters["source_of_petition"] == "all"
        assert filters["received_at"] == "all"
        assert filters["target_cvo"] == "all"
        assert filters["officer_id"] is None

    filtered = app_module._apply_dashboard_filters(
        petitions,
        {
            "from_date": None,
            "to_date": None,
            "petition_type": "bribe",
            "source_of_petition": "media",
            "received_at": "jmd_office",
            "target_cvo": "apspdcl",
            "officer_id": 8,
        },
    )
    assert len(filtered) == 1

    stats = app_module._build_filtered_dashboard_stats("po", 1, petitions, filtered)
    assert stats["total_visible"] == 1
    assert stats["kpi_cards"][0]["count"] == 1

    analytics = app_module._build_dashboard_analytics(
        petitions,
        {"sla_within": 1, "sla_breached": 1},
    )
    assert analytics["summary"]["total_visible"] == 2
    assert analytics["status_split"]["labels"]
    assert analytics["type_split"]["labels"]
    assert analytics["source_split"]["labels"]
    assert analytics["office_split"]["labels"]
    assert analytics["officer_split"]["labels"]

    assert app_module._format_electrical_accident_summary(
        {
            "accident_type": "fatal",
            "deceased_category": "departmental",
            "departmental_type": "regular",
            "deceased_count": 2,
        }
    ).startswith("Fatal | Departmental")
    assert "Private Electricians" in app_module._format_electrical_accident_summary(
        {
            "accident_type": "non_fatal",
            "deceased_category": "non_departmental",
            "non_departmental_type": "private_electricians",
            "deceased_count": 1,
        }
    )
    assert "Contract Labour" in app_module._format_electrical_accident_summary(
        {
            "accident_type": "fatal",
            "deceased_category": "non_departmental",
            "non_departmental_type": "contract_labour",
            "deceased_count": 1,
        }
    )
    assert "General Public" in app_module._format_electrical_accident_summary(
        {
            "accident_type": "fatal",
            "deceased_category": "general_public",
            "deceased_count": 1,
            "general_public_count": 3,
        }
    )
    assert "Animals" in app_module._format_electrical_accident_summary(
        {
            "accident_type": "fatal",
            "deceased_category": "animals",
            "deceased_count": 1,
            "animals_count": 4,
        }
    )
    assert app_module._format_electrical_accident_summary(None) == "-"

    report = app_module._build_analysis_report_data([])
    assert report["total"] == 0


def test_analysis_report_and_dashboard_api_deep_paths(monkeypatch):
    sample_petitions = [
        {
            "id": 1,
            "sno": "VIG/1",
            "petitioner_name": "Ravi",
            "subject": "Bribe case",
            "status": "closed",
            "petition_type": "bribe",
            "source_of_petition": "media",
            "target_cvo": "apspdcl",
            "requires_permission": True,
            "is_overdue_escalated": True,
            "enquiry_type": "preliminary",
            "assigned_inspector_id": 8,
            "inspector_name": "Officer One",
            "received_date": date(2026, 1, 17),
            "received_at": "jmd_office",
        },
        {
            "id": 2,
            "sno": "VIG/2",
            "petitioner_name": "Sita",
            "subject": "Accident case",
            "status": "lodged",
            "petition_type": "electrical_accident",
            "source_of_petition": "public_individual",
            "target_cvo": "apepdcl",
            "requires_permission": False,
            "is_overdue_escalated": False,
            "enquiry_type": "detailed",
            "assigned_inspector_id": 9,
            "inspector_name": "Officer Two",
            "received_date": date(2026, 2, 17),
            "received_at": "cvo_apepdcl_vizag",
        },
        {
            "id": 3,
            "sno": "VIG/3",
            "petitioner_name": "Kiran",
            "subject": "Pending case",
            "status": "sent_back_for_reenquiry",
            "petition_type": "other",
            "source_of_petition": "govt",
            "target_cvo": "apcpdcl",
            "requires_permission": True,
            "is_overdue_escalated": False,
            "enquiry_type": "detailed",
            "assigned_inspector_id": 9,
            "inspector_name": "Officer Two",
            "received_date": date(2026, 3, 17),
            "received_at": "cvo_apcpdcl_vijayawada",
        },
        {
            "id": 4,
            "sno": "VIG/4",
            "petitioner_name": "Mohan",
            "subject": "CMD action",
            "status": "action_instructed",
            "petition_type": "corruption",
            "source_of_petition": "sumoto",
            "target_cvo": "headquarters",
            "requires_permission": False,
            "is_overdue_escalated": True,
            "enquiry_type": "detailed",
            "assigned_inspector_id": 10,
            "inspector_name": "Officer Three",
            "received_date": date(2026, 4, 17),
            "received_at": "jmd_office",
        },
    ]

    class ReportModels:
        @staticmethod
        def get_user_by_id(user_id):
            return {
                "id": user_id,
                "username": "tester",
                "full_name": "Tester",
                "role": "po",
                "cvo_office": None,
                "phone": None,
                "email": None,
                "profile_photo": None,
                "session_version": 1,
                "is_active": True,
            }

        @staticmethod
        def get_sla_evaluation_rows(petitions):
            return [
                {"sla_bucket": "within", "target_cvo": "apspdcl", "assigned_inspector_id": 8},
                {"sla_bucket": "beyond", "target_cvo": "apepdcl", "assigned_inspector_id": 9},
                {"sla_bucket": "beyond", "target_cvo": "apcpdcl", "assigned_inspector_id": 9},
                {"sla_bucket": "within", "target_cvo": "headquarters", "assigned_inspector_id": 10},
            ]

        @staticmethod
        def _get_workflow_stage_stats(petitions):
            return {"stage_1": len(petitions)}

        @staticmethod
        def _get_sla_stats_for_petitions(petitions):
            return {"sla_within": 2, "sla_breached": 2}

        @staticmethod
        def _build_role_kpi_cards(role, petitions, user_id):
            return [{"role": role, "count": len(petitions), "user_id": user_id}]

        @staticmethod
        def get_dashboard_drilldown(role, user_id, cvo_office, metric):
            return sample_petitions

        @staticmethod
        def get_latest_enquiry_report_accident_details(ids):
            return {
                2: {
                    "accident_type": "fatal",
                    "deceased_category": "general_public",
                    "general_public_count": 2,
                    "deceased_count": 1,
                }
            }

    monkeypatch.setattr(app_module, "models", ReportModels())
    monkeypatch.setattr(app_module, "get_petitions_for_user_cached", lambda *_a, **_k: sample_petitions)

    analysis = app_module._build_analysis_report_data(sample_petitions)
    assert analysis["total"] == 4
    assert analysis["closed"] == 1
    assert analysis["lodged"] == 1
    assert analysis["active"] == 2
    assert analysis["resolution_rate"] > 0
    assert analysis["sla_beyond"] == 2
    assert analysis["sla_within"] == 2
    assert analysis["status_breakdown"]
    assert analysis["type_breakdown"]
    assert analysis["source_breakdown"]
    assert analysis["dept_stats"]
    assert analysis["officer_stats"]
    assert analysis["best_performers"]
    assert analysis["talking_points"]
    assert analysis["dept_insights"]
    assert analysis["type_insights"]
    assert analysis["source_insights"]
    assert analysis["status_insights"]
    assert analysis["officer_insights"]
    assert analysis["sla_insights"]

    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="po")
        drill = client.get("/api/dashboard-drilldown?metric=status:received")
        assert drill.status_code == 200
        assert drill.get_json()["items"][1]["accident_summary"].startswith("Fatal | General Public")

        analytics = client.get("/api/dashboard-analytics?petition_type=all")
        assert analytics.status_code == 200
        assert analytics.get_json()["summary"]["total_visible"] == 4


def test_chatbot_exception_and_fuzzy_fallback_paths(monkeypatch):
    class ChatbotStub:
        def __init__(self):
            self.roles = {}

        def get_user_by_id(self, user_id):
            return {
                "id": user_id,
                "username": "tester",
                "full_name": "Test User",
                "role": self.roles.get(user_id, "po"),
                "cvo_office": None,
                "phone": None,
                "email": None,
                "profile_photo": None,
                "session_version": 1,
                "is_active": True,
            }

        def get_pending_petitions_for_chatbot(self, *_a, **_k):
            raise RuntimeError("pending-fail")

        def get_recent_updates_for_chatbot(self, *_a, **_k):
            raise RuntimeError("updates-fail")

        def get_petition_stats_for_chatbot(self, *_a, **_k):
            raise RuntimeError("stats-fail")

        def search_petitions(self, *_a, **_k):
            raise RuntimeError("search-fail")

    stub = ChatbotStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        login_as(client, role="po", full_name="Officer")
        suggest = client.post("/api/chatbot", json={"message": "what next"}).get_json()
        assert suggest["type"] in {"suggest", "action_guide"}

        assert client.post("/api/chatbot", json={"message": "search ravi"}).get_json()["type"] == "text"
        assert client.post("/api/chatbot", json={"message": "efile EO-22"}).get_json()["type"] == "text"
        assert client.post("/api/chatbot", json={"message": "receipt ER-22"}).get_json()["type"] == "text"
        assert client.post("/api/chatbot", json={"message": "sno VIG-22"}).get_json()["type"] == "text"

        fuzzy = client.post("/api/chatbot", json={"message": "pendin"}).get_json()
        assert fuzzy["type"] == "text"

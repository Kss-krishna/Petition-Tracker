import app as app_module

from conftest import login_as


class ChatbotModelsStub:
    def __init__(self):
        self.search_calls = []
        self.roles_by_user_id = {}

    def get_user_by_id(self, user_id):
        return {
            "id": user_id,
            "username": "tester",
            "full_name": "Test User",
            "role": self.roles_by_user_id.get(user_id, "po"),
            "cvo_office": None,
            "phone": None,
            "email": None,
            "profile_photo": None,
            "session_version": 1,
            "is_active": True,
        }

    def get_pending_petitions_for_chatbot(self, *_args, **_kwargs):
        return [
            {
                "id": 1,
                "sno": "VIG/1",
                "petitioner_name": "Ravi",
                "efile_no": "EO-1",
                "ereceipt_no": "ER-1",
                "subject": "Pending petition",
                "status": "received",
                "received_date": "2026-02-17",
                "petition_type": "bribe",
                "place": "Hyd",
            }
        ]

    def get_recent_updates_for_chatbot(self, *_args, **_kwargs):
        return [
            {
                "id": 2,
                "sno": "VIG/2",
                "petitioner_name": "Ravi",
                "efile_no": "EO-2",
                "ereceipt_no": "ER-2",
                "subject": "Updated petition",
                "status": "closed",
                "received_date": "2026-02-18",
                "petition_type": "other",
                "place": "VJA",
                "updated_at": "2026-02-19 10:00",
            }
        ]

    def get_petition_stats_for_chatbot(self, *_args, **_kwargs):
        return {"total": 5, "closed": 2, "pending": 3}

    def search_petitions(self, _user_id, _user_role, _cvo_office, query, search_type="all"):
        self.search_calls.append((query, search_type))
        if search_type == "name" and query == "ravi":
            return []
        if search_type == "all" and query in ("ravi", "unknown text"):
            return [{"id": 3, "sno": "VIG/3", "petitioner_name": "Ravi", "subject": "Found", "status": "received", "petition_type": "bribe", "place": "Hyd"}]
        if search_type in ("efile", "ereceipt", "sno"):
            return [{"id": 4, "sno": "VIG/4", "petitioner_name": "Lookup", "subject": search_type, "status": "closed", "petition_type": "other", "place": "Hyd"}]
        return []


def _chat(client, message):
    return client.post("/api/chatbot", json={"message": message})


def test_chatbot_format_helpers():
    formatted = app_module._chatbot_format_petitions(
        [{"id": 1, "subject": "A" * 95, "status": "received", "petition_type": "bribe", "received_date": "2026-02-17", "petitioner_name": "R", "efile_no": "EO", "ereceipt_no": "ER", "place": "Hyd"}]
    )
    assert formatted[0]["subject"].startswith("A")
    assert formatted[0]["status_label"] == "Received"

    with_date = app_module._chatbot_format_petitions_with_date(
        [{"id": 2, "subject": "B", "status": "closed", "petition_type": "other", "received_date": "2026-02-18", "petitioner_name": "S", "efile_no": None, "ereceipt_no": None, "place": None, "updated_at": "2026-02-19"}]
    )
    assert with_date[0]["updated_at"] == "2026-02-19"


def test_chatbot_basic_intents(monkeypatch):
    stub = ChatbotModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="po", full_name="Officer")
        assert _chat(client, "").get_json()["type"] == "text"
        assert _chat(client, "hi").get_json()["type"] == "text"
        assert _chat(client, "thanks").get_json()["type"] == "text"
        assert _chat(client, "bye").get_json()["type"] == "text"
        assert _chat(client, "how are you").get_json()["type"] == "text"
        assert _chat(client, "who are you").get_json()["type"] == "text"
        assert _chat(client, "not working").get_json()["type"] == "text"
        assert _chat(client, "help").get_json()["type"] == "help"
        assert _chat(client, "my responsibilities").get_json()["type"] == "role_info"


def test_chatbot_pending_updates_guide_stats_and_download(monkeypatch):
    stub = ChatbotModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="po", full_name="Officer")
        assert _chat(client, "pending").get_json()["type"] == "pending"
        assert _chat(client, "updates").get_json()["type"] == "updates"
        assert _chat(client, "guide").get_json()["type"] == "action_guide"
        assert _chat(client, "stats").get_json()["type"] == "stats"
        download = _chat(client, "analysis report").get_json()
        assert download["type"] == "download"
        assert download["url"] == "/analysis-report"


def test_chatbot_urgent_summary_and_suggestions(monkeypatch):
    stub = ChatbotModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="po", full_name="Officer")
        stub.roles_by_user_id[1] = "po"
        urgent = _chat(client, "urgent").get_json()
        assert urgent["type"] == "urgent"
        assert urgent["url"] == "/petitions?status=beyond_sla"

        summary = _chat(client, "today").get_json()
        assert summary["type"] == "summary"
        assert summary["pending_count"] == 1

        suggest = _chat(client, "what next").get_json()
        assert suggest["type"] == "suggest"
        assert suggest["actions"]

    with app_module.app.test_client() as client:
        login_as(client, user_id=9, role="inspector", full_name="Inspector")
        stub.roles_by_user_id[9] = "inspector"
        urgent = _chat(client, "urgent").get_json()
        assert urgent["type"] == "text"


def test_chatbot_suggest_role_matrix_and_search_failures(monkeypatch):
    class FailingChatbotModelsStub(ChatbotModelsStub):
        def search_petitions(self, _user_id, _user_role, _cvo_office, query, search_type="all"):
            raise RuntimeError("search fail")

    app_module.app.config["TESTING"] = True
    stub = ChatbotModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    with app_module.app.test_client() as client:
        for user_id, role in [
            (21, "data_entry"),
            (22, "super_admin"),
            (23, "cmd_apspdcl"),
            (24, "cgm_hr_transco"),
        ]:
            login_as(client, user_id=user_id, role=role, full_name=f"{role} User")
            stub.roles_by_user_id[user_id] = role
            suggest = _chat(client, "what next").get_json()
            assert suggest["type"] == "suggest"
            assert suggest["actions"]

    failing = FailingChatbotModelsStub()
    monkeypatch.setattr(app_module, "models", failing)
    with app_module.app.test_client() as client:
        login_as(client, role="po", full_name="Officer")
        assert _chat(client, "search a").get_json()["type"] == "text"
        assert _chat(client, "search ravi").get_json()["type"] == "text"
        assert _chat(client, "efile EO-1").get_json()["type"] == "text"
        assert _chat(client, "receipt ER-1").get_json()["type"] == "text"
        assert _chat(client, "sno VIG-1").get_json()["type"] == "text"
        assert _chat(client, "ER2024001").get_json()["type"] == "text"
        assert _chat(client, "ABC/DEF/2024/01").get_json()["type"] == "text"


def test_chatbot_search_branches_and_generic_fallback(monkeypatch):
    stub = ChatbotModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="po", full_name="Officer")
        name_resp = _chat(client, "search ravi").get_json()
        assert name_resp["type"] == "petitions"
        assert ("ravi", "name") in stub.search_calls
        assert ("ravi", "all") in stub.search_calls

        assert _chat(client, "efile EO-22").get_json()["search_type"] == "efile"
        assert _chat(client, "receipt ER-22").get_json()["search_type"] == "ereceipt"
        assert _chat(client, "sno VIG-22").get_json()["search_type"] == "sno"
        assert _chat(client, "ER2024001").get_json()["search_type"] == "ereceipt"
        assert _chat(client, "ABC/DEF/2024/01").get_json()["search_type"] == "efile"

        generic = _chat(client, "unknown text").get_json()
        assert generic["type"] == "petitions"


def test_chatbot_final_fallback(monkeypatch):
    stub = ChatbotModelsStub()
    stub.search_petitions = lambda *_args, **_kwargs: []
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="po", full_name="Officer")
        response = _chat(client, "zz")
        assert response.get_json()["type"] == "text"


def test_chatbot_remaining_role_and_fallback_paths(monkeypatch):
    stub = ChatbotModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        for user_id, role in [
            (31, "cvo_apspdcl"),
            (32, "cvo_apepdcl"),
            (33, "cvo_apcpdcl"),
            (34, "dsp"),
            (35, "cmd_apepdcl"),
            (36, "cmd_apcpdcl"),
        ]:
            login_as(client, user_id=user_id, role=role, full_name=f"{role} User")
            stub.roles_by_user_id[user_id] = role
            role_info = _chat(client, "role").get_json()
            assert role_info["type"] in {"role_info", "text"}
            suggest = _chat(client, "what should i work on").get_json()
            assert suggest["type"] == "suggest"

    class ExplodingStatsStub(ChatbotModelsStub):
        def get_pending_petitions_for_chatbot(self, *_a, **_k):
            raise RuntimeError("pending fail")

        def get_recent_updates_for_chatbot(self, *_a, **_k):
            raise RuntimeError("updates fail")

        def get_petition_stats_for_chatbot(self, *_a, **_k):
            raise RuntimeError("stats fail")

        def search_petitions(self, *_a, **_k):
            return []

    failing = ExplodingStatsStub()
    monkeypatch.setattr(app_module, "models", failing)
    with app_module.app.test_client() as client:
        login_as(client, role="po", full_name="Officer")
        assert _chat(client, "pending").get_json()["type"] == "text"
        assert _chat(client, "updates").get_json()["type"] == "text"
        assert _chat(client, "stats").get_json()["type"] == "text"
        assert _chat(client, "today").get_json()["type"] == "text"
        assert _chat(client, "pendin").get_json()["type"] == "text"
        assert _chat(client, "something completely random").get_json()["type"] == "text"

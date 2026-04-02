import io

import app as app_module

from conftest import login_as


class ProfileHelpStub:
    def __init__(self):
        self.raise_create_help = False
        self.raise_set_active = False
        self.raise_profile_update = False
        self.auth_ok = False
        self.role = "po"

    def get_user_by_id(self, user_id):
        if user_id == 404:
            return None
        return {
            "id": user_id,
            "username": "tester",
            "full_name": "Tester User",
            "role": self.role,
            "cvo_office": None,
            "phone": "9999999999",
            "email": "tester@example.com",
            "profile_photo": "old_photo.png",
            "session_version": 1,
            "is_active": True,
        }

    def list_help_resources(self, active_only=False):
        return []

    def set_help_resource_active(self, resource_id, should_activate):
        if self.raise_set_active:
            raise Exception("toggle fail")

    def create_help_resource(self, **kwargs):
        if self.raise_create_help:
            raise Exception("create fail")

    def authenticate_user(self, username, password):
        if self.auth_ok:
            return {"id": 1}
        return None

    def set_username(self, user_id, username):
        if username == "duplicate_user":
            raise Exception("duplicate key")

    def update_user_profile_info(self, user_id, full_name, phone, email):
        if self.raise_profile_update:
            raise Exception("profile fail")

    def set_user_password(self, user_id, password):
        return None

    def set_user_profile_photo(self, user_id, photo):
        return None


def test_help_page_validation_and_error_matrix(monkeypatch):
    stub = ProfileHelpStub()
    monkeypatch.setattr(app_module, "models", stub)
    monkeypatch.setattr(app_module, "ensure_upload_dirs", lambda: None)
    monkeypatch.setattr(
        app_module,
        "_save_uploaded_file",
        lambda upload, base_dir, file_name, label, use_date_subdir=True: (True, file_name),
    )
    deleted = []
    monkeypatch.setattr(app_module, "_delete_uploaded_file", lambda base, rel: deleted.append((base, rel)))
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        stub.role = "data_entry"
        login_as(client, role="data_entry")
        assert client.post("/help", data={"title": "x"}).status_code == 403

        stub.role = "po"
        login_as(client, role="po")
        assert client.post("/help", data={"action": "toggle_active", "resource_id": ""}).status_code == 302
        stub.raise_set_active = True
        assert client.post("/help", data={"action": "toggle_active", "resource_id": "7", "activate": "1"}).status_code == 302
        stub.raise_set_active = False

        bad_posts = [
            {"resource_type": "manual", "storage_kind": "external_url"},
            {"title": "Guide", "resource_type": "bad", "storage_kind": "external_url"},
            {"title": "Guide", "resource_type": "manual", "storage_kind": "bad"},
            {"title": "Guide", "resource_type": "manual", "storage_kind": "external_url", "display_order": "abc"},
            {"title": "Guide", "resource_type": "manual", "storage_kind": "external_url", "external_url": "bad-url"},
            {"title": "Guide", "resource_type": "manual", "storage_kind": "upload"},
        ]
        for payload in bad_posts:
            assert client.post("/help", data=payload).status_code == 302

        monkeypatch.setattr(
            app_module,
            "validate_help_resource_upload",
            lambda upload: (False, None, None, "bad upload"),
        )
        assert client.post(
            "/help",
            data={"title": "Guide", "resource_type": "manual", "storage_kind": "upload", "resource_file": (io.BytesIO(b"x"), "guide.pdf")},
            content_type="multipart/form-data",
        ).status_code == 302

        monkeypatch.setattr(
            app_module,
            "validate_help_resource_upload",
            lambda upload: (True, "help_file.pdf", "application/pdf", None),
        )
        stub.raise_create_help = True
        assert client.post(
            "/help",
            data={"title": "Guide", "resource_type": "manual", "storage_kind": "upload", "resource_file": (io.BytesIO(b"%PDF-1"), "guide.pdf")},
            content_type="multipart/form-data",
        ).status_code == 302
        assert deleted


def test_profile_route_validation_and_error_matrix(monkeypatch):
    stub = ProfileHelpStub()
    monkeypatch.setattr(app_module, "models", stub)
    monkeypatch.setattr(app_module, "ensure_upload_dirs", lambda: None)
    monkeypatch.setattr(
        app_module,
        "validate_profile_photo_upload",
        lambda upload, user_id=None: (True, "new_photo.png", None),
    )
    monkeypatch.setattr(
        app_module,
        "_save_uploaded_file",
        lambda upload, base_dir, file_name, label, use_date_subdir=True: (True, file_name),
    )
    deleted = []
    monkeypatch.setattr(app_module, "delete_profile_photo_file", lambda name: deleted.append(name))
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        stub.role = "po"
        login_as(client, role="po")
        assert client.get("/profile").status_code == 200

        bad_posts = [
            {"full_name": "A", "username": "tester", "phone": "9999999999", "email": "tester@example.com"},
            {"full_name": "Tester User", "username": "ab", "phone": "9999999999", "email": "tester@example.com"},
            {"full_name": "Tester User", "username": "bad user", "phone": "9999999999", "email": "tester@example.com"},
            {"full_name": "Tester User", "username": "tester", "phone": "bad", "email": "tester@example.com"},
            {"full_name": "Tester User", "username": "tester", "phone": "9999999999", "email": "bad-email"},
            {"full_name": "Tester User", "username": "tester", "phone": "9999999999", "email": "tester@example.com", "new_password": "StrongPass@9", "confirm_password": "StrongPass@9"},
        ]
        for payload in bad_posts:
            assert client.post("/profile", data=payload).status_code == 302

        stub.auth_ok = False
        assert client.post(
            "/profile",
            data={
                "full_name": "Tester User",
                "username": "tester",
                "phone": "9999999999",
                "email": "tester@example.com",
                "current_password": "wrong",
                "new_password": "StrongPass@9",
                "confirm_password": "StrongPass@9",
            },
        ).status_code == 302

        stub.auth_ok = True
        assert client.post(
            "/profile",
            data={
                "full_name": "Tester User",
                "username": "tester",
                "phone": "9999999999",
                "email": "tester@example.com",
                "current_password": "ok",
                "new_password": "weak",
                "confirm_password": "weak",
            },
        ).status_code == 302
        assert client.post(
            "/profile",
            data={
                "full_name": "Tester User",
                "username": "tester",
                "phone": "9999999999",
                "email": "tester@example.com",
                "current_password": "ok",
                "new_password": "StrongPass@9",
                "confirm_password": "Mismatch@9",
            },
        ).status_code == 302

        monkeypatch.setattr(
            app_module,
            "validate_profile_photo_upload",
            lambda upload, user_id=None: (False, None, "bad photo"),
        )
        assert client.post(
            "/profile",
            data={"full_name": "Tester User", "username": "tester", "phone": "9999999999", "email": "tester@example.com"},
        ).status_code == 302

        monkeypatch.setattr(
            app_module,
            "validate_profile_photo_upload",
            lambda upload, user_id=None: (True, "new_photo.png", None),
        )
        assert client.post(
            "/profile",
            data={
                "full_name": "Tester User",
                "username": "duplicate_user",
                "phone": "9999999999",
                "email": "tester@example.com",
            },
        ).status_code == 302

        stub.raise_profile_update = True
        assert client.post(
            "/profile",
            data={
                "full_name": "Tester User",
                "username": "tester",
                "phone": "9999999999",
                "email": "tester@example.com",
                "profile_photo": (io.BytesIO(b"x"), "photo.png"),
            },
            content_type="multipart/form-data",
        ).status_code == 302
        assert deleted

    with app_module.app.test_client() as client:
        stub.role = "po"
        login_as(client, user_id=404, role="po")
        assert client.get("/profile").status_code == 302

import io

import app as app_module

from conftest import login_as


class AdminModelsStub:
    def __init__(self):
        self.calls = []
        self.user = {
            "id": 5,
            "username": "user5",
            "full_name": "User Five",
            "role": "inspector",
            "cvo_office": "apspdcl",
            "phone": "9999999999",
            "email": "u5@example.com",
            "profile_photo": "old.png",
            "session_version": 1,
            "is_active": True,
        }

    def _record(self, name, **kwargs):
        self.calls.append((name, kwargs))

    def get_user_by_id(self, user_id):
        if user_id == 404:
            return None
        if user_id == 2:
            return {"id": 2, "role": "cvo_apspdcl", "full_name": "CVO"}
        return dict(self.user, id=user_id)

    def get_user_by_username(self, username):
        if username == "cvo1":
            return {"id": 2, "role": "cvo_apspdcl"}
        return None

    def update_user(self, *args):
        self._record("update_user", args=args)

    def toggle_user_status(self, user_id):
        self._record("toggle_user_status", user_id=user_id)

    def set_user_password(self, user_id, password):
        self._record("set_user_password", user_id=user_id, password=password)

    def set_must_change_password(self, user_id, value):
        self._record("set_must_change_password", user_id=user_id, value=value)

    def set_username(self, user_id, username):
        if username == "duplicate_user":
            raise Exception("duplicate key")
        self._record("set_username", user_id=user_id, username=username)

    def update_user_full_name(self, user_id, full_name):
        self._record("update_user_full_name", user_id=user_id, full_name=full_name)

    def update_user_profile_info(self, user_id, full_name, phone, email):
        self._record(
            "update_user_profile_info",
            user_id=user_id,
            full_name=full_name,
            phone=phone,
            email=email,
        )

    def set_user_profile_photo(self, user_id, photo):
        self._record("set_user_profile_photo", user_id=user_id, photo=photo)

    def map_inspector_to_cvo(self, inspector_id, cvo_id):
        self._record("map_inspector_to_cvo", inspector_id=inspector_id, cvo_id=cvo_id)

    def create_user(self, *args):
        if args[0] == "boom_user":
            raise Exception("create fail")
        self._record("create_user", args=args)


def test_admin_user_route_matrix(monkeypatch):
    stub = AdminModelsStub()
    stub.user["role"] = "super_admin"
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
        login_as(client, role="super_admin")

        assert client.post(
            "/users/new",
            data={
                "username": "ins_user",
                "full_name": "Inspector User",
                "role": "inspector",
                "cvo_office": "apspdcl",
                "assigned_cvo_id": "2",
                "phone": "9999999999",
                "email": "ins@example.com",
            },
        ).status_code == 302

        assert client.post("/users/upload", data={}, content_type="multipart/form-data").status_code == 302
        csv_payload = io.BytesIO(
            b"username,full_name,role,cvo_office,assigned_cvo_username,phone,email\n"
            b"ins_user,Inspector User,inspector,apspdcl,cvo1,9999999999,ins@example.com\n"
            b"bad,Bad,data_entry,,,invalid,bad-email\n"
        )
        assert client.post(
            "/users/upload",
            data={"users_file": (csv_payload, "users.csv")},
            content_type="multipart/form-data",
        ).status_code == 302

        assert client.post("/users/5/toggle").status_code == 302
        assert client.post(
            "/users/5/edit",
            data={
                "full_name": "Updated User",
                "role": "inspector",
                "cvo_office": "apspdcl",
                "assigned_cvo_id": "2",
                "phone": "9999999999",
                "email": "updated@example.com",
                "password": "StrongPass@9",
            },
        ).status_code == 302
        assert client.post("/users/5/reset-password").status_code == 302
        assert client.post("/users/5/reset-username", data={"new_username": "ok_user"}).status_code == 302
        assert client.post("/users/5/reset-username", data={"new_username": "duplicate_user"}).status_code == 302
        assert client.post("/users/5/update-name", data={"full_name": "Final User"}).status_code == 302

        assert client.post(
            "/users/5/update-contact",
            data={
                "phone": "9999999998",
                "email": "contact@example.com",
                "profile_photo": (io.BytesIO(b"png"), "photo.png"),
            },
            content_type="multipart/form-data",
        ).status_code == 302
        assert client.post(
            "/users/5/update-contact",
            data={"phone": "9999999997", "email": "contact2@example.com", "remove_photo": "on"},
        ).status_code == 302
        assert client.post("/users/404/update-contact", data={"phone": "9999999999", "email": "x@example.com"}).status_code == 302

        assert client.post("/users/8/map-cvo", data={"cvo_id": "2"}).status_code == 302

    assert deleted


def test_users_upload_validation_matrix(monkeypatch):
    stub = AdminModelsStub()
    stub.user["role"] = "super_admin"
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        login_as(client, role="super_admin")

        assert client.post(
            "/users/upload",
            data={"users_file": (io.BytesIO(b"x"), "users.txt")},
            content_type="multipart/form-data",
        ).status_code == 302

        monkeypatch.setattr(app_module, "load_workbook", lambda *_a, **_k: type("WB", (), {"active": type("WS", (), {"iter_rows": staticmethod(lambda values_only=True: iter([]))})()})())
        assert client.post(
            "/users/upload",
            data={"users_file": (io.BytesIO(b"x"), "users.xlsx")},
            content_type="multipart/form-data",
        ).status_code == 302

        rows = (
            b"username,full_name,role,cvo_office,assigned_cvo_username,phone,email\n"
            b",Missing User,po,,,9999999999,a@example.com\n"
            b"ab,Short,po,,,9999999999,a@example.com\n"
            b"user1,Ok,invalid_role,,,9999999999,a@example.com\n"
            b"user2,Ok,data_entry,,,9999999999,a@example.com\n"
            b"user3,Ok,cvo_apspdcl,,,9999999999,a@example.com\n"
            b"user4,Ok,inspector,apspdcl,,9999999999,a@example.com\n"
            b"user5,Ok,po,apspdcl,cvo1,9999999999,a@example.com\n"
            b"user6,Ok,inspector,apspdcl,badcvo,9999999999,a@example.com\n"
            b"user7,Ok,po,,,bad,bad-email\n"
            b"boom_user,Valid User,po,,,9999999999,good@example.com\n"
            b"good_user,Valid User,po,,,9999999999,good@example.com\n"
        )
        assert client.post(
            "/users/upload",
            data={"users_file": (io.BytesIO(rows), "users.csv")},
            content_type="multipart/form-data",
        ).status_code == 302


def test_admin_user_validation_negative_matrix(monkeypatch):
    stub = AdminModelsStub()
    stub.user["role"] = "super_admin"
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        login_as(client, role="super_admin")

        create_cases = [
            {"username": "ab", "full_name": "Officer", "role": "po"},
            {"username": "user1", "full_name": "Of", "role": "po"},
            {"username": "user1", "full_name": "Officer", "role": "bad"},
            {"username": "user1", "full_name": "Officer", "role": "po", "cvo_office": "bad"},
            {"username": "user1", "full_name": "Officer", "role": "po", "phone": "bad"},
            {"username": "user1", "full_name": "Officer", "role": "po", "email": "bad"},
            {"username": "user1", "full_name": "Officer", "role": "inspector", "cvo_office": "", "assigned_cvo_id": ""},
            {"username": "user1", "full_name": "Officer", "role": "data_entry", "cvo_office": ""},
            {"username": "user1", "full_name": "Officer", "role": "cvo_apspdcl", "cvo_office": ""},
            {"username": "user1", "full_name": "Officer", "role": "inspector", "cvo_office": "apspdcl", "assigned_cvo_id": "999"},
        ]
        for payload in create_cases:
            assert client.post("/users/new", data=payload).status_code == 302

        edit_cases = [
            {"full_name": "Of", "role": "po"},
            {"full_name": "Officer", "role": "bad"},
            {"full_name": "Officer", "role": "po", "cvo_office": "bad"},
            {"full_name": "Officer", "role": "po", "phone": "bad"},
            {"full_name": "Officer", "role": "po", "email": "bad"},
            {"full_name": "Officer", "role": "po", "password": "weak"},
            {"full_name": "Officer", "role": "inspector", "cvo_office": "", "assigned_cvo_id": ""},
            {"full_name": "Officer", "role": "data_entry", "cvo_office": ""},
            {"full_name": "Officer", "role": "cvo_apspdcl", "cvo_office": ""},
            {"full_name": "Officer", "role": "inspector", "cvo_office": "apspdcl", "assigned_cvo_id": "999"},
        ]
        for payload in edit_cases:
            assert client.post("/users/5/edit", data=payload).status_code == 302

        assert client.post("/users/5/update-name", data={"full_name": "Of"}).status_code == 302
        assert client.post("/users/5/reset-username", data={"new_username": ""}).status_code == 302
        assert client.post("/users/5/reset-username", data={"new_username": "ab"}).status_code == 302
        assert client.post("/users/5/reset-username", data={"new_username": "bad user"}).status_code == 302
        assert client.post("/users/5/update-contact", data={"phone": "bad", "email": "x@example.com"}).status_code == 302
        assert client.post("/users/5/update-contact", data={"phone": "9999999999", "email": "bad"}).status_code == 302
        assert client.post("/users/8/map-cvo", data={"cvo_id": ""}).status_code == 302
        assert client.post("/users/8/map-cvo", data={"cvo_id": "bad"}).status_code == 302
        assert client.post("/users/8/map-cvo", data={"cvo_id": "999"}).status_code == 302

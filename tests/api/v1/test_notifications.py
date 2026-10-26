#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

import pytest

from CTFd.models import NotificationReadReceipt, Notifications, Users
from tests.helpers import (
    create_ctfd,
    destroy_ctfd,
    gen_challenge,
    gen_notification,
    gen_team,
    login_as_user,
    register_user,
)


def test_api_notifications_get():
    app = create_ctfd()
    with app.app_context():
        register_user(app)
        gen_notification(app.db)
        with login_as_user(app) as client:
            # test_api_notifications_get
            """Can the users get /api/v1/notifications"""
            r = client.get("/api/v1/notifications", json="")
            assert r.status_code == 200
            assert len(r.get_json()["data"]) == 1

            # test_api_get_notification_detail
            r = client.get("/api/v1/notifications/1", json="")
            assert r.status_code == 200
            resp = r.get_json()
            assert resp["data"]["title"] == "title"
            assert resp["data"]["content"] == "content"

            # test_api_notifications_post_non_admin
            """Can the users post /api/v1/notifications if not admin"""
            r = client.post("/api/v1/notifications", json="")
            assert r.status_code == 403
    destroy_ctfd(app)


def test_api_notification_reads_are_scoped_to_user_and_admin():
    app = create_ctfd()
    with app.app_context():
        register_user(app)
        register_user(app, name="other-user", email="other-user@examplectf.com")
        user_a = Users.query.filter_by(name="user").first()
        user_b = Users.query.filter_by(name="other-user").first()
        user_a_id = user_a.id
        user_b_id = user_b.id

        global_notification = Notifications(title="global", content="global content")
        user_a_notification = Notifications(
            title="user A", content="private content", user_id=user_a_id
        )
        user_b_notification = Notifications(
            title="user B", content="private content", user_id=user_b_id
        )
        app.db.session.add_all(
            [global_notification, user_a_notification, user_b_notification]
        )
        app.db.session.commit()
        global_notification_id = global_notification.id
        user_a_notification_id = user_a_notification.id
        user_b_notification_id = user_b_notification.id

        with login_as_user(app) as client:
            response = client.get("/api/v1/notifications")
            assert response.status_code == 200
            titles = {item["title"] for item in response.get_json()["data"]}
            assert titles == {"global", "user A"}

            assert (
                client.get(
                    f"/api/v1/notifications?user_id={user_b_id}", json={}
                ).status_code
                == 403
            )
            assert (
                client.head(
                    f"/api/v1/notifications?user_id={user_b_id}", json={}
                ).status_code
                == 403
            )
            assert (
                client.get(
                    f"/api/v1/notifications/{user_a_notification_id}", json={}
                ).status_code
                == 200
            )
            assert (
                client.get(
                    f"/api/v1/notifications/{user_b_notification_id}", json={}
                ).status_code
                == 404
            )
            assert (
                client.get(
                    f"/api/v1/notifications/{global_notification_id}", json={}
                ).status_code
                == 200
            )

        with login_as_user(app, name="other-user") as client:
            response = client.get("/api/v1/notifications")
            titles = {item["title"] for item in response.get_json()["data"]}
            assert titles == {"global", "user B"}
            assert (
                client.get(
                    f"/api/v1/notifications/{user_b_notification_id}", json={}
                ).status_code
                == 200
            )
    destroy_ctfd(app)


def test_api_notification_reads_allow_team_members_and_admins():
    app = create_ctfd(user_mode="teams")
    with app.app_context():
        team_a = gen_team(
            app.db, name="team-a", email="team-a@examplectf.com", member_count=1
        )
        team_b = gen_team(
            app.db, name="team-b", email="team-b@examplectf.com", member_count=1
        )
        team_a_id = team_a.id
        team_b_id = team_b.id
        team_a_member_name = team_a.members[0].name
        team_a_notification = Notifications(
            title="team A", content="team content", team_id=team_a_id
        )
        team_b_notification = Notifications(
            title="team B", content="team content", team_id=team_b_id
        )
        app.db.session.add_all([team_a_notification, team_b_notification])
        app.db.session.commit()
        team_a_notification_id = team_a_notification.id
        team_b_notification_id = team_b_notification.id

        with login_as_user(app, name=team_a_member_name) as client:
            response = client.get("/api/v1/notifications")
            assert response.status_code == 200
            titles = {item["title"] for item in response.get_json()["data"]}
            assert titles == {"team A"}
            assert (
                client.get(
                    f"/api/v1/notifications?team_id={team_b_id}", json={}
                ).status_code
                == 403
            )
            assert (
                client.get(
                    f"/api/v1/notifications/{team_a_notification_id}", json={}
                ).status_code
                == 200
            )
            assert (
                client.get(
                    f"/api/v1/notifications/{team_b_notification_id}", json={}
                ).status_code
                == 404
            )

        with login_as_user(app, name="admin") as client:
            response = client.get("/api/v1/notifications")
            assert response.status_code == 200
            titles = {item["title"] for item in response.get_json()["data"]}
            assert titles == {"team A", "team B"}
            assert (
                client.get(
                    f"/api/v1/notifications/{team_b_notification_id}", json={}
                ).status_code
                == 200
            )
    destroy_ctfd(app)


def test_api_notifications_require_authentication():
    app = create_ctfd()
    with app.app_context():
        notification = Notifications(title="private", content="private content")
        app.db.session.add(notification)
        app.db.session.commit()
        with app.test_client() as client:
            assert client.get("/api/v1/notifications", json={}).status_code == 403
            assert client.head("/api/v1/notifications", json={}).status_code == 403
            assert (
                client.get(
                    f"/api/v1/notifications/{notification.id}", json={}
                ).status_code
                == 403
            )
    destroy_ctfd(app)


def test_api_notification_read_receipts_are_persistent_and_user_scoped():
    app = create_ctfd()
    with app.app_context():
        register_user(app)
        register_user(app, name="other-user", email="other-user@examplectf.com")
        user_a_id = Users.query.filter_by(name="user").first().id
        user_b_id = Users.query.filter_by(name="other-user").first().id
        global_notification = Notifications(title="global", content="global")
        user_a_notification = Notifications(
            title="user A", content="user A", user_id=user_a_id
        )
        user_b_notification = Notifications(
            title="user B", content="user B", user_id=user_b_id
        )
        app.db.session.add_all(
            [global_notification, user_a_notification, user_b_notification]
        )
        app.db.session.commit()
        global_id = global_notification.id
        user_a_notification_id = user_a_notification.id
        user_b_notification_id = user_b_notification.id

        with app.test_client() as client:
            assert (
                client.post("/api/v1/notifications/read", json={}).status_code
                == 403
            )
            assert (
                client.post(
                    f"/api/v1/notifications/{global_id}/read", json={}
                ).status_code
                == 403
            )

        with login_as_user(app) as client:
            assert client.get("/api/v1/notifications/unread").get_json()["data"] == {
                "count": 2
            }
            assert client.head("/api/v1/notifications").headers["Unread-Count"] == "2"

            response = client.post(
                f"/api/v1/notifications/{user_a_notification_id}/read", json={}
            )
            assert response.status_code == 200
            assert response.get_json()["data"]["read"] is True
            assert (
                client.post(
                    f"/api/v1/notifications/{user_a_notification_id}/read",
                    json={},
                ).status_code
                == 200
            )
            assert (
                NotificationReadReceipt.query.filter_by(
                    user_id=user_a_id, notification_id=user_a_notification_id
                ).count()
                == 1
            )
            assert client.get("/api/v1/notifications/unread").get_json()["data"] == {
                "count": 1
            }
            assert (
                client.head("/api/v1/notifications").headers["Unread-Count"] == "1"
            )

            listing = client.get("/api/v1/notifications").get_json()["data"]
            read_by_id = {item["id"]: item["read"] for item in listing}
            assert read_by_id == {
                global_id: False,
                user_a_notification_id: True,
            }
            assert (
                client.post(
                    f"/api/v1/notifications/{user_b_notification_id}/read",
                    json={},
                ).status_code
                == 404
            )
            assert (
                NotificationReadReceipt.query.filter_by(
                    user_id=user_a_id, notification_id=user_b_notification_id
                ).count()
                == 0
            )

            response = client.post("/api/v1/notifications/read", json={})
            assert response.status_code == 200
            assert response.get_json()["data"]["count"] == 1
            assert (
                client.post(
                    "/api/v1/notifications/read", json={}
                ).get_json()["data"]["count"]
                == 0
            )
            assert client.get("/api/v1/notifications/unread").get_json()["data"] == {
                "count": 0
            }
            assert (
                client.head("/api/v1/notifications").headers["Unread-Count"] == "0"
            )
            assert (
                client.get(
                    f"/api/v1/notifications/{global_id}", json={}
                ).get_json()["data"]["read"]
                is True
            )

        with login_as_user(app, name="other-user") as client:
            assert client.get("/api/v1/notifications/unread").get_json()["data"] == {
                "count": 2
            }
            assert client.post(
                f"/api/v1/notifications/{global_id}/read", json={}
            ).status_code == 200
            assert client.get("/api/v1/notifications/unread").get_json()["data"] == {
                "count": 1
            }
            assert (
                NotificationReadReceipt.query.filter_by(
                    user_id=user_a_id, notification_id=global_id
                ).count()
                == 1
            )
            assert (
                NotificationReadReceipt.query.filter_by(
                    user_id=user_b_id, notification_id=global_id
                ).count()
                == 1
            )
    destroy_ctfd(app)


def test_concurrent_notification_read_requests_create_one_receipt(monkeypatch):
    app = create_ctfd()
    try:
        database_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        if not (
            database_uri.startswith("mysql")
            or database_uri.startswith("mariadb")
        ):
            pytest.skip("Concurrent notification receipts require MySQL/MariaDB")

        with app.app_context():
            register_user(app)
            user_id = Users.query.filter_by(name="user").one().id
            notification = Notifications(
                title="concurrent read",
                content="concurrent read",
                user_id=user_id,
            )
            notifications_for_race = [
                notification,
                Notifications(
                    title="concurrent mark all A",
                    content="concurrent mark all A",
                    user_id=user_id,
                ),
                Notifications(
                    title="concurrent mark all B",
                    content="concurrent mark all B",
                    user_id=user_id,
                ),
            ]
            app.db.session.add_all(notifications_for_race)
            app.db.session.commit()
            notification_id = notification.id
            all_read_ids = [item.id for item in notifications_for_race[1:]]

        clients = [login_as_user(app), login_as_user(app)]
        barrier = threading.Barrier(2)
        from CTFd.utils import notifications as notification_utils

        get_read_ids = notification_utils.get_notification_read_ids

        def synchronize_receipt_reads(user_id, notification_ids=None):
            read_ids = get_read_ids(user_id, notification_ids)
            barrier.wait(timeout=15)
            return read_ids

        monkeypatch.setattr(
            notification_utils,
            "get_notification_read_ids",
            synchronize_receipt_reads,
        )

        result_lock = threading.Lock()
        paths = [
            f"/api/v1/notifications/{notification_id}/read",
            f"/api/v1/notifications/{notification_id}/read",
        ]

        def run_concurrent_requests():
            responses = [None, None]
            errors = []

            def post(index):
                try:
                    response = clients[index].post(paths[index], json={})
                    with result_lock:
                        responses[index] = response
                except Exception as exc:  # pragma: no cover - surfaced by assertion
                    with result_lock:
                        errors.append(exc)

            threads = [
                threading.Thread(target=post, args=(index,))
                for index in range(2)
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=30)
            assert not any(thread.is_alive() for thread in threads)
            assert errors == []
            assert [response.status_code for response in responses] == [200, 200]
            return responses

        responses = run_concurrent_requests()
        assert all(response.get_json()["data"]["read"] is True for response in responses)

        with app.app_context():
            assert (
                NotificationReadReceipt.query.filter_by(
                    user_id=user_id,
                    notification_id=notification_id,
                ).count()
                == 1
            )

        barrier = threading.Barrier(2)
        paths = [
            "/api/v1/notifications/read",
            f"/api/v1/notifications/{all_read_ids[0]}/read",
        ]
        responses = run_concurrent_requests()
        assert responses[1].get_json()["data"]["read"] is True
        assert responses[0].get_json()["data"]["count"] in (1, 2)

        with app.app_context():
            for read_id in all_read_ids:
                assert (
                    NotificationReadReceipt.query.filter_by(
                        user_id=user_id,
                        notification_id=read_id,
                    ).count()
                    == 1
                )

        with login_as_user(app) as client:
            assert client.get("/api/v1/notifications/unread").get_json()["data"] == {
                "count": 0
            }
            assert client.head("/api/v1/notifications").headers["Unread-Count"] == "0"
    finally:
        destroy_ctfd(app)


def test_api_notification_read_receipts_include_team_notifications():
    app = create_ctfd(user_mode="teams")
    with app.app_context():
        team_a = gen_team(
            app.db, name="team-a", email="team-a@examplectf.com", member_count=1
        )
        team_b = gen_team(
            app.db, name="team-b", email="team-b@examplectf.com", member_count=1
        )
        team_a_id = team_a.id
        team_b_user_id = team_b.members[0].id
        team_a_member_name = team_a.members[0].name
        team_b_member_name = team_b.members[0].name
        team_notification = Notifications(
            title="team", content="team", team_id=team_a_id
        )
        global_notification = Notifications(title="global", content="global")
        app.db.session.add_all([team_notification, global_notification])
        app.db.session.commit()
        team_notification_id = team_notification.id
        global_notification_id = global_notification.id

        with login_as_user(app, name=team_a_member_name) as client:
            response = client.post("/api/v1/notifications/read", json={})
            assert response.status_code == 200
            assert response.get_json()["data"]["count"] == 2
            assert client.get("/api/v1/notifications/unread").get_json()["data"] == {
                "count": 0
            }
            listing = client.get("/api/v1/notifications").get_json()["data"]
            assert {item["id"]: item["read"] for item in listing} == {
                team_notification_id: True,
                global_notification_id: True,
            }

        with login_as_user(app, name=team_b_member_name) as client:
            assert client.get("/api/v1/notifications/unread").get_json()["data"] == {
                "count": 1
            }
            assert (
                client.post(
                    f"/api/v1/notifications/{team_notification_id}/read",
                    json={},
                ).status_code
                == 404
            )
            assert (
                NotificationReadReceipt.query.filter_by(
                    user_id=team_b_user_id, notification_id=team_notification_id
                ).count()
                == 0
            )
    destroy_ctfd(app)


def test_api_notifications_post_admin():
    """Can the users post /api/v1/notifications if admin"""
    app = create_ctfd()
    with app.app_context():
        gen_challenge(app.db)
        with login_as_user(app, name="admin") as client:
            r = client.post(
                "/api/v1/notifications", json={"title": "title", "content": "content"}
            )
            assert r.status_code == 200
    destroy_ctfd(app)


def test_api_delete_notifications_by_admin():
    """Test that an admin can delete notifications"""
    app = create_ctfd()
    with app.app_context():
        gen_challenge(app.db)
        gen_notification(app.db)
        assert Notifications.query.count() == 1
        with login_as_user(app, name="admin") as client:
            r = client.delete("/api/v1/notifications/1", json="")
            assert r.status_code == 200
            assert r.get_json()["success"] is True
        assert Notifications.query.count() == 0
    destroy_ctfd(app)


def test_api_delete_notifications_by_user():
    """Test that a non-admin cannot delete notifications"""
    app = create_ctfd()
    with app.app_context():
        register_user(app)
        gen_challenge(app.db)
        gen_notification(app.db)
        assert Notifications.query.count() == 1
        with login_as_user(app) as client:
            r = client.delete("/api/v1/notifications/1", json="")
            assert r.status_code == 403
        assert Notifications.query.count() == 1
    destroy_ctfd(app)

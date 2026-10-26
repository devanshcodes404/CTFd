from typing import List

from flask import abort, current_app, make_response, request
from flask_restx import Namespace, Resource

from CTFd.api.v1.helpers.request import validate_args
from CTFd.api.v1.helpers.schemas import sqlalchemy_to_pydantic
from CTFd.api.v1.schemas import APIDetailedSuccessResponse, APIListSuccessResponse
from CTFd.constants import RawEnum
from CTFd.models import NotificationReadReceipt, Notifications, db
from CTFd.schemas.notifications import NotificationSchema
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.helpers.models import build_model_filters
from CTFd.utils.notifications import (
    get_accessible_notifications,
    get_notification_read_ids,
    get_unread_notifications,
    mark_notifications_read,
)
from CTFd.utils.user import get_current_team, get_current_user, is_admin

notifications_namespace = Namespace(
    "notifications", description="Endpoint to retrieve Notifications"
)

NotificationModel = sqlalchemy_to_pydantic(Notifications, include={"read": bool})
TransientNotificationModel = sqlalchemy_to_pydantic(
    Notifications, include={"read": bool}, exclude=["id"]
)


class NotificationDetailedSuccessResponse(APIDetailedSuccessResponse):
    data: NotificationModel


class NotificationListSuccessResponse(APIListSuccessResponse):
    data: List[NotificationModel]


notifications_namespace.schema_model(
    "NotificationDetailedSuccessResponse", NotificationDetailedSuccessResponse.apidoc()
)

notifications_namespace.schema_model(
    "NotificationListSuccessResponse", NotificationListSuccessResponse.apidoc()
)


def dump_notifications(notifications, many=False):
    if many:
        notification_ids = [notification.id for notification in notifications]
    else:
        notification_ids = [notifications.id]
    read_ids = get_notification_read_ids(
        get_current_user().id, notification_ids=notification_ids
    )
    schema = NotificationSchema(
        many=many, context={"read_notification_ids": read_ids}
    )
    return schema.dump(notifications)


@notifications_namespace.route("")
class NotificantionList(Resource):
    @notifications_namespace.doc(
        description="Endpoint to get notification objects in bulk",
        responses={
            200: ("Success", "NotificationListSuccessResponse"),
            400: (
                "An error occured processing the provided or stored data",
                "APISimpleErrorResponse",
            ),
        },
    )
    @validate_args(
        {
            "title": (str, None),
            "content": (str, None),
            "user_id": (int, None),
            "team_id": (int, None),
            "q": (str, None),
            "field": (
                RawEnum("NotificationFields", {"title": "title", "content": "content"}),
                None,
            ),
            "since_id": (int, None),
        },
        location="query",
    )
    @authed_only
    def get(self, query_args):
        q = query_args.pop("q", None)
        field = str(query_args.pop("field", None))
        filters = build_model_filters(model=Notifications, query=q, field=field)

        since_id = query_args.pop("since_id", None)
        if since_id:
            filters.append((Notifications.id > since_id))

        if not is_admin():
            user_id = query_args.pop("user_id", None)
            team_id = query_args.pop("team_id", None)
            user = get_current_user()
            team = get_current_team()

            if user_id is not None and user_id != user.id:
                abort(403)
            if team_id is not None and (team is None or team_id != team.id):
                abort(403)

        notifications = (
            get_accessible_notifications()
            .filter_by(**query_args)
            .filter(*filters)
            .all()
        )
        result = dump_notifications(notifications, many=True)
        if result.errors:
            return {"success": False, "errors": result.errors}, 400
        return {"success": True, "data": result.data}

    @notifications_namespace.doc(
        description="Endpoint to get statistics for notification objects in bulk",
        responses={200: ("Success", "APISimpleSuccessResponse")},
    )
    @validate_args(
        {
            "title": (str, None),
            "content": (str, None),
            "user_id": (int, None),
            "team_id": (int, None),
            "q": (str, None),
            "field": (
                RawEnum("NotificationFields", {"title": "title", "content": "content"}),
                None,
            ),
            "since_id": (int, None),
        },
        location="query",
    )
    @authed_only
    def head(self, query_args):
        q = query_args.pop("q", None)
        field = str(query_args.pop("field", None))
        filters = build_model_filters(model=Notifications, query=q, field=field)

        since_id = query_args.pop("since_id", None)
        if since_id:
            filters.append((Notifications.id > since_id))

        if not is_admin():
            user_id = query_args.pop("user_id", None)
            team_id = query_args.pop("team_id", None)
            user = get_current_user()
            team = get_current_team()

            if user_id is not None and user_id != user.id:
                abort(403)
            if team_id is not None and (team is None or team_id != team.id):
                abort(403)
        notification_count = (
            get_accessible_notifications()
            .filter_by(**query_args)
            .filter(*filters)
            .count()
        )
        response = make_response()
        response.headers["Result-Count"] = notification_count
        response.headers["Unread-Count"] = get_unread_notifications().count()
        return response

    @admins_only
    @notifications_namespace.doc(
        description="Endpoint to create a notification object",
        responses={
            200: ("Success", "NotificationDetailedSuccessResponse"),
            400: (
                "An error occured processing the provided or stored data",
                "APISimpleErrorResponse",
            ),
        },
    )
    def post(self):
        req = request.get_json()

        schema = NotificationSchema()
        result = schema.load(req)

        if result.errors:
            return {"success": False, "errors": result.errors}, 400

        db.session.add(result.data)
        db.session.commit()

        read_ids = get_notification_read_ids(
            get_current_user().id, notification_ids=[result.data.id]
        )
        schema.context["read_notification_ids"] = read_ids
        response = schema.dump(result.data)

        # Grab additional settings
        notif_type = req.get("type", "alert")
        notif_sound = req.get("sound", True)
        response.data["type"] = notif_type
        response.data["sound"] = notif_sound

        current_app.events_manager.publish(data=response.data, type="notification")

        return {"success": True, "data": response.data}


@notifications_namespace.route("/unread")
class NotificationUnreadCount(Resource):
    @authed_only
    def get(self):
        return {
            "success": True,
            "data": {"count": get_unread_notifications().count()},
        }


@notifications_namespace.route("/read")
class NotificationMarkAllRead(Resource):
    @authed_only
    def post(self):
        user_id = get_current_user().id
        notification_ids = [
            notification_id
            for (notification_id,) in get_accessible_notifications()
            .with_entities(Notifications.id)
            .all()
        ]
        marked_count = mark_notifications_read(user_id, notification_ids)
        return {"success": True, "data": {"count": marked_count}}


@notifications_namespace.route("/<notification_id>")
@notifications_namespace.param("notification_id", "A Notification ID")
class Notification(Resource):
    @notifications_namespace.doc(
        description="Endpoint to get a specific notification object",
        responses={
            200: ("Success", "NotificationDetailedSuccessResponse"),
            400: (
                "An error occured processing the provided or stored data",
                "APISimpleErrorResponse",
            ),
        },
    )
    @authed_only
    def get(self, notification_id):
        notif = (
            get_accessible_notifications()
            .filter_by(id=notification_id)
            .first_or_404()
        )
        response = dump_notifications(notif)
        if response.errors:
            return {"success": False, "errors": response.errors}, 400

        return {"success": True, "data": response.data}

    @admins_only
    @notifications_namespace.doc(
        description="Endpoint to delete a notification object",
        responses={200: ("Success", "APISimpleSuccessResponse")},
    )
    def delete(self, notification_id):
        notif = Notifications.query.filter_by(id=notification_id).first_or_404()
        db.session.delete(notif)
        db.session.commit()
        db.session.close()

        return {"success": True}


@notifications_namespace.route("/<notification_id>/read")
@notifications_namespace.param("notification_id", "A Notification ID")
class NotificationMarkRead(Resource):
    @authed_only
    def post(self, notification_id):
        notification = (
            get_accessible_notifications()
            .filter_by(id=notification_id)
            .first_or_404()
        )
        user_id = get_current_user().id
        mark_notifications_read(user_id, [notification.id])
        return {"success": True, "data": {"id": notification.id, "read": True}}

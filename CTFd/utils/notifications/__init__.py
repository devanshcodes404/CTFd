from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError

from CTFd.models import NotificationReadReceipt, Notifications, db
from CTFd.utils.user import get_current_team, get_current_user, is_admin


def get_accessible_notifications():
    query = Notifications.query

    if is_admin():
        return query

    user = get_current_user()
    filters = [
        Notifications.user_id == user.id,
        and_(
            Notifications.user_id.is_(None),
            Notifications.team_id.is_(None),
        ),
    ]

    team = get_current_team()
    if team:
        filters.append(
            and_(
                Notifications.user_id.is_(None),
                Notifications.team_id == team.id,
            )
        )

    return query.filter(or_(*filters))


def get_notification_read_ids(user_id, notification_ids=None):
    query = db.session.query(NotificationReadReceipt.notification_id).filter_by(
        user_id=user_id
    )
    if notification_ids is not None:
        if not notification_ids:
            return set()
        query = query.filter(
            NotificationReadReceipt.notification_id.in_(notification_ids)
        )
    return {notification_id for (notification_id,) in query.all()}


def get_unread_notifications(user_id=None):
    if user_id is None:
        user_id = get_current_user().id

    return (
        get_accessible_notifications()
        .outerjoin(
            NotificationReadReceipt,
            and_(
                NotificationReadReceipt.notification_id == Notifications.id,
                NotificationReadReceipt.user_id == user_id,
            ),
        )
        .filter(NotificationReadReceipt.id.is_(None))
    )


def mark_notifications_read(user_id, notification_ids):
    read_ids = get_notification_read_ids(user_id, notification_ids)
    marked_count = 0
    for notification_id in notification_ids:
        if notification_id in read_ids:
            continue
        try:
            with db.session.begin_nested():
                db.session.add(
                    NotificationReadReceipt(
                        user_id=user_id,
                        notification_id=notification_id,
                    )
                )
                db.session.flush()
        except IntegrityError as error:
            if not getattr(error.orig, "args", ()) or error.orig.args[0] != 1062:
                raise
            continue
        marked_count += 1

    if marked_count:
        db.session.commit()
    return marked_count

from datetime import datetime

from CTFd.models import db


class UserAchievement(db.Model):
    __tablename__ = "esecurityin_user_achievements"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    achievement_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "esecurityin_achievements.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    unlocked_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "achievement_id",
            name="uq_esecurityin_user_achievement",
        ),
    )
from CTFd.models import db


class UserMission(db.Model):
    __tablename__ = "esecurityin_user_missions"

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "mission_id",
            "period_key",
            name="uq_esecurityin_user_mission_period",
        ),
    )

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    mission_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "esecurityin_missions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    period_key = db.Column(
        db.String(50),
        nullable=False,
        index=True,
    )

    progress = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    completed = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )

    completed_at = db.Column(
        db.DateTime,
        nullable=True,
    )
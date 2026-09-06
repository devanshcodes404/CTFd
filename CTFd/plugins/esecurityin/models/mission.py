from CTFd.models import db


class Mission(db.Model):
    __tablename__ = "esecurityin_missions"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    key = db.Column(
        db.String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    name = db.Column(
        db.String(150),
        nullable=False,
    )

    description = db.Column(
        db.Text,
        nullable=False,
    )

    icon = db.Column(
        db.String(50),
        nullable=False,
        default="🎯",
    )

    mission_type = db.Column(
        db.String(20),
        nullable=False,
        index=True,
    )

    objective_type = db.Column(
        db.String(50),
        nullable=False,
    )

    target_value = db.Column(
        db.Integer,
        nullable=False,
        default=1,
    )

    xp_reward = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    starts_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    ends_at = db.Column(
        db.DateTime,
        nullable=True,
    )
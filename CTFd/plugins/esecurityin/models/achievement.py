from CTFd.models import db


class Achievement(db.Model):
    __tablename__ = "esecurityin_achievements"

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
        default="🏆",
    )

    xp_reward = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    requirement_type = db.Column(
        db.String(50),
        nullable=False,
    )

    requirement_value = db.Column(
        db.Integer,
        nullable=False,
        default=1,
    )

    active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )
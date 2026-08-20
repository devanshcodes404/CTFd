from CTFd.models import db


class DailyObjective(db.Model):
    __tablename__ = "esecurityin_daily_objectives"

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
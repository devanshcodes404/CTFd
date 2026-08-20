from CTFd.models import db


class UserDailyObjective(db.Model):
    __tablename__ = "esecurityin_user_daily_objectives"

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

    objective_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "esecurityin_daily_objectives.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    objective_date = db.Column(
        db.Date,
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
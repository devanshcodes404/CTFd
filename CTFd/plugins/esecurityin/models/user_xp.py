from CTFd.models import db


class UserXP(db.Model):
    __tablename__ = "user_xp"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )

    xp = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    level = db.Column(
        db.Integer,
        default=1,
        nullable=False
    )

    streak = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    longest_streak = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    total_solves = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    last_solve_date = db.Column(
        db.Date,
        nullable=True
    )
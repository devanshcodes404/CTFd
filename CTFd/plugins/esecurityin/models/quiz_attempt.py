from datetime import datetime
from CTFd.models import db


class QuizAttempt(db.Model):
    __tablename__ = "esecurityin_quiz_attempts"

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
    quiz_id = db.Column(
        db.String(64),
        nullable=False,
        index=True,
    )
    score = db.Column(
        db.Integer,
        nullable=False,
    )
    correct_count = db.Column(
        db.Integer,
        nullable=False,
    )
    total_count = db.Column(
        db.Integer,
        nullable=False,
    )
    passed = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        index=True,
    )
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )


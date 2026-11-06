from CTFd.models import db, Challenges


class QuizChallenge(Challenges):
    __tablename__ = "esecurityin_quiz_challenges"
    __mapper_args__ = {"polymorphic_identity": "quiz"}

    id = db.Column(
        db.Integer,
        db.ForeignKey("challenges.id", ondelete="CASCADE"),
        primary_key=True,
    )
    quiz_id = db.Column(
        db.String(64),
        nullable=False,
        unique=True,
        index=True,
    )
    passing_score = db.Column(
        db.Integer,
        nullable=False,
        default=8,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self.type = "quiz"


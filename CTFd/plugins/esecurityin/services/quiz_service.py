import json
import os
from typing import Dict, List, Optional
from CTFd.models import db, Challenges, Solves, Flags
from CTFd.plugins.challenges import BaseChallenge, CHALLENGE_CLASSES
from ..models import QuizChallenge, QuizAttempt


class CTFdQuizChallenge(BaseChallenge):
    id = "quiz"
    name = "quiz"
    templates = {
        "create": "/plugins/esecurityin/assets/create.html",
        "update": "/plugins/esecurityin/assets/update.html",
        "view": "/plugins/esecurityin/assets/view.html",
    }
    scripts = {
        "create": "/plugins/esecurityin/assets/create.js",
        "update": "/plugins/esecurityin/assets/update.js",
        "view": "/plugins/esecurityin/assets/view.js",
    }
    challenge_model = QuizChallenge

    @classmethod
    def attempt(cls, challenge, request):
        """
        Quizzes cannot be attempted via standard flag submission.
        Must use the dedicated /api/v1/esecurityin/quizzes/<quiz_id>/submit endpoint.
        """
        return False, "Quizzes must be submitted through the Quiz Arena interface."

    @classmethod
    def solve(cls, user, team, challenge, request):
        super().solve(user, team, challenge, request)


class QuizService:
    _question_bank: Optional[Dict] = None

    @classmethod
    def get_question_bank_path(cls) -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, "data", "question_bank.json")

    @classmethod
    def load_question_bank(cls) -> Dict:
        if cls._question_bank is None:
            path = cls.get_question_bank_path()
            with open(path, "r", encoding="utf-8") as f:
                cls._question_bank = json.load(f)
        return cls._question_bank

    @classmethod
    def get_quizzes_summary(cls) -> List[Dict]:
        qb = cls.load_question_bank()
        return [
            {
                "quiz_id": q["quiz_id"],
                "title": q["title"],
                "question_count": q["question_count"],
                "passing_score": q.get("passing_score", 8),
            }
            for q in qb.get("quizzes", [])
        ]

    @classmethod
    def get_quiz_by_id(cls, quiz_id: str) -> Optional[Dict]:
        qb = cls.load_question_bank()
        for q in qb.get("quizzes", []):
            if q["quiz_id"] == quiz_id:
                return q
        return None

    @classmethod
    def get_learner_quiz(cls, quiz_id: str) -> Optional[Dict]:
        """
        Returns quiz questions formatted safely for learners.
        EXCLUDES correct_option and all grading keys.
        """
        quiz = cls.get_quiz_by_id(quiz_id)
        if not quiz:
            return None

        safe_questions = []
        for q in quiz.get("questions", []):
            safe_questions.append({
                "id": q["id"],
                "source_number": q["source_number"],
                "difficulty": q["difficulty"],
                "question": q["question"],
                "options": q["options"],
            })

        return {
            "quiz_id": quiz["quiz_id"],
            "title": quiz["title"],
            "question_count": quiz["question_count"],
            "passing_score": quiz.get("passing_score", 8),
            "questions": safe_questions,
        }

    @classmethod
    def sync_quiz_challenges(cls):
        """
        Ensures each of the 13 quizzes exists as a QuizChallenge row in CTFd.
        Idempotent:
        - Creates challenges only if they do not exist.
        - Uses configurable default points from CTFd config 'quiz_default_points' (fallback 0).
        - NEVER overwrites administrator-configured values (points, category, state, description).
        """
        from CTFd.utils import get_config

        configured_default = get_config("quiz_default_points")
        try:
            default_points = int(configured_default) if configured_default is not None else 0
        except (ValueError, TypeError):
            default_points = 0

        qb = cls.load_question_bank()
        for q in qb.get("quizzes", []):
            quiz_id = q["quiz_id"]
            qc = QuizChallenge.query.filter_by(quiz_id=quiz_id).first()
            if not qc:
                qc = QuizChallenge(
                    name=q["title"],
                    category=q["title"],
                    description=f"Assessment covering {q['title']}. Requires 80% to pass ({q.get('passing_score', 8)}/{q['question_count']}).",
                    value=default_points,
                    state="visible",
                    quiz_id=quiz_id,
                    passing_score=q.get("passing_score", 8),
                )
                db.session.add(qc)
            # If qc already exists, do not modify qc.value or any admin-configured property
        db.session.commit()

    @classmethod
    def evaluate_submission(cls, quiz_id: str, answers: Dict[str, str]) -> Dict:
        """
        Validates answers strictly server-side.
        Calculates score: (correct / total) * 100 >= 80
        9 questions -> passing_score 8 (88.88%)
        10 questions -> passing_score 8 (80.0%)

        Strict validations:
        1. answers must be a dict
        2. Exactly all questions in the quiz must be answered
        3. No extra or foreign question IDs
        4. Every submitted option must be one of 'A', 'B', 'C', 'D'
        """
        if not isinstance(answers, dict):
            raise ValueError("Malformed submission: 'answers' must be a JSON object mapping question IDs to option labels")

        quiz = cls.get_quiz_by_id(quiz_id)
        if not quiz:
            raise ValueError(f"Unknown quiz_id: {quiz_id}")

        questions = quiz.get("questions", [])
        total_count = len(questions)
        q_map = {q["id"]: q for q in questions}

        # Check for missing questions (incomplete submission)
        missing_ids = set(q_map.keys()) - set(answers.keys())
        if missing_ids:
            raise ValueError(f"Incomplete submission: missing answers for {len(missing_ids)} question(s)")

        # Check for extra or foreign question IDs
        extra_ids = set(answers.keys()) - set(q_map.keys())
        if extra_ids:
            raise ValueError(f"Invalid question ID(s) for quiz '{quiz_id}': {', '.join(sorted(extra_ids))}")

        # Check question count exactly matches
        if len(answers) != total_count:
            raise ValueError(f"Expected exactly {total_count} answers for quiz '{quiz_id}', received {len(answers)}")

        allowed_options = {"A", "B", "C", "D"}
        correct_count = 0

        for q_id, q_data in q_map.items():
            submitted_opt = answers.get(q_id)
            if not isinstance(submitted_opt, str):
                raise ValueError(f"Invalid option type for question '{q_id}': expected string")

            opt_clean = submitted_opt.strip().upper()
            if opt_clean not in allowed_options:
                raise ValueError(f"Invalid option label '{submitted_opt}' for question '{q_id}'. Allowed options: A, B, C, D")

            if opt_clean == q_data["correct_option"]:
                correct_count += 1

        passing_threshold = quiz.get("passing_score", 8)
        passed = correct_count >= passing_threshold

        score_percent = round((correct_count / total_count) * 100, 1)

        return {
            "total_count": total_count,
            "correct_count": correct_count,
            "incorrect_count": total_count - correct_count,
            "score_percent": score_percent,
            "passed": passed,
            "passing_threshold": passing_threshold,
        }


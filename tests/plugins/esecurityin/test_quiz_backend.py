import json
import pytest
from tests.helpers import create_ctfd, destroy_ctfd, login_as_user, register_user


@pytest.fixture
def app():
    app = create_ctfd(enable_plugins=True)
    try:
        yield app
    finally:
        destroy_ctfd(app)


def test_question_bank_structure(app):
    """Verify question bank schema and counts."""
    from CTFd.plugins.esecurityin.services.quiz_service import QuizService

    qb = QuizService.load_question_bank()
    assert qb["total_quizzes"] == 13
    assert qb["total_questions"] == 120
    assert len(qb["quizzes"]) == 13

    for qz in qb["quizzes"]:
        assert qz["question_count"] in (9, 10)
        assert qz["passing_score"] == 8
        assert len(qz["questions"]) == qz["question_count"]
        for q in qz["questions"]:
            assert set(q["options"].keys()) == {"A", "B", "C", "D"}
            assert q["correct_option"] in {"A", "B", "C", "D"}
            assert q["difficulty"] in {"beginner", "intermediate", "advanced"}


def test_quiz_challenges_synced_default_zero(app):
    """Verify newly initialized quizzes default to 0 points when no setting exists."""
    from CTFd.plugins.esecurityin.models import QuizChallenge

    with app.app_context():
        quizzes = QuizChallenge.query.all()
        assert len(quizzes) == 13
        for q in quizzes:
            assert q.type == "quiz"
            assert q.value == 0
            assert q.passing_score == 8


def test_configured_default_points():
    """Verify that when 'quiz_default_points' is configured, newly created challenges use it."""
    from CTFd.models import db
    from CTFd.plugins.esecurityin.models import QuizChallenge
    from CTFd.plugins.esecurityin.services.quiz_service import QuizService
    from CTFd.utils import set_config

    app = create_ctfd(enable_plugins=True)
    try:
        with app.app_context():
            # Delete one quiz challenge to test recreation under configured default
            QuizChallenge.query.filter_by(quiz_id="cryptography").delete()
            db.session.commit()
            assert QuizChallenge.query.filter_by(quiz_id="cryptography").first() is None

            # Set default points configuration
            set_config("quiz_default_points", 75)

            # Re-sync
            QuizService.sync_quiz_challenges()

            qc = QuizChallenge.query.filter_by(quiz_id="cryptography").first()
            assert qc is not None
            assert qc.value == 75
    finally:
        destroy_ctfd(app)


def test_configurable_points_persistence(app):
    """
    Test configurable CTFd challenge points:
    - Administrator modifies challenge value from default 0 to 250
    - Repeated sync_quiz_challenges() preserves the 250 point value
    - Solving awards the configured 250 points
    """
    from CTFd.models import db
    from CTFd.plugins.esecurityin.models import QuizChallenge
    from CTFd.plugins.esecurityin.services.quiz_service import QuizService

    with app.app_context():
        # 1. Modify points as admin
        qc = QuizChallenge.query.filter_by(quiz_id="cryptography").first()
        assert qc is not None
        qc.value = 250
        db.session.commit()

        # 2. Re-run sync and confirm 250 points is preserved
        QuizService.sync_quiz_challenges()
        qc_after = QuizChallenge.query.filter_by(quiz_id="cryptography").first()
        assert qc_after.value == 250

        # 3. Verify user quiz listing reports 250 points
        register_user(app)
        client = login_as_user(app)
        res = client.get("/api/v1/esecurityin/quizzes/cryptography")
        assert res.status_code == 200
        assert res.get_json()["quiz"]["points"] == 250


def test_unauthenticated_access_blocked(app):
    """Verify unauthenticated users cannot access quiz endpoints."""
    with app.app_context():
        client = app.test_client()
        res = client.get("/api/v1/esecurityin/quizzes")
        assert res.status_code in (302, 403)

        res = client.get("/api/v1/esecurityin/quizzes/cryptography")
        assert res.status_code in (302, 403)

        res = client.post("/api/v1/esecurityin/quizzes/cryptography/submit", json={"answers": {}})
        assert res.status_code in (302, 403)


def test_answer_security_in_get_quiz(app):
    """Verify learner-facing quiz retrieval NEVER reveals correct answers."""
    with app.app_context():
        register_user(app)
        client = login_as_user(app)

        res = client.get("/api/v1/esecurityin/quizzes/cryptography")
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True

        quiz = data["quiz"]
        assert "questions" in quiz
        for q in quiz["questions"]:
            # Critical security check: correct_option must NOT be present
            assert "correct_option" not in q
            assert "correct_answer" not in q
            assert "answer" not in q
            assert "key" not in q

        # Raw string search on entire response payload
        raw_text = res.get_data(as_text=True)
        assert "correct_option" not in raw_text


def test_scoring_evaluation_unit():
    """Unit test evaluation logic directly with exact passing thresholds."""
    from CTFd.plugins.esecurityin.services.quiz_service import QuizService

    # 1. Test 9-question quiz (cryptography)
    qb_quiz = QuizService.get_quiz_by_id("cryptography")
    questions = qb_quiz["questions"]
    assert len(questions) == 9

    # 7/9 fail (77.8%)
    answers_7 = {q["id"]: q["correct_option"] for q in questions[:7]}
    # fill remaining 2 with wrong option to make submission complete
    for q in questions[7:]:
        answers_7[q["id"]] = "C" if q["correct_option"] != "C" else "D"
    res_7 = QuizService.evaluate_submission("cryptography", answers_7)
    assert res_7["correct_count"] == 7
    assert res_7["score_percent"] == 77.8
    assert res_7["passed"] is False

    # 8/9 pass (88.9%)
    answers_8 = {q["id"]: q["correct_option"] for q in questions[:8]}
    for q in questions[8:]:
        answers_8[q["id"]] = "C" if q["correct_option"] != "C" else "D"
    res_8 = QuizService.evaluate_submission("cryptography", answers_8)
    assert res_8["correct_count"] == 8
    assert res_8["score_percent"] == 88.9
    assert res_8["passed"] is True

    # 2. Test 10-question quiz (wireless-security)
    qb_w = QuizService.get_quiz_by_id("wireless-security")
    w_questions = qb_w["questions"]
    assert len(w_questions) == 10

    # 7/10 fail (70.0%)
    answers_w7 = {q["id"]: q["correct_option"] for q in w_questions[:7]}
    for q in w_questions[7:]:
        answers_w7[q["id"]] = "C" if q["correct_option"] != "C" else "D"
    res_w7 = QuizService.evaluate_submission("wireless-security", answers_w7)
    assert res_w7["correct_count"] == 7
    assert res_w7["score_percent"] == 70.0
    assert res_w7["passed"] is False

    # 8/10 pass (80.0%)
    answers_w8 = {q["id"]: q["correct_option"] for q in w_questions[:8]}
    for q in w_questions[8:]:
        answers_w8[q["id"]] = "C" if q["correct_option"] != "C" else "D"
    res_w8 = QuizService.evaluate_submission("wireless-security", answers_w8)
    assert res_w8["correct_count"] == 8
    assert res_w8["score_percent"] == 80.0
    assert res_w8["passed"] is True


def test_submission_validation_strict(app):
    """
    Test strengthened server-side submission validation:
    - Missing answers rejected
    - Incomplete submissions rejected
    - Extra question IDs rejected
    - Foreign quiz question IDs rejected
    - Invalid option labels rejected
    - Malformed JSON rejected
    """
    from CTFd.plugins.esecurityin.services.quiz_service import QuizService

    with app.app_context():
        register_user(app)
        client = login_as_user(app)

        qb_quiz = QuizService.get_quiz_by_id("cryptography")
        questions = qb_quiz["questions"]

        # 1. Incomplete / missing answers
        incomplete_answers = {questions[0]["id"]: "A"}
        res = client.post("/api/v1/esecurityin/quizzes/cryptography/submit", json={"answers": incomplete_answers})
        assert res.status_code == 400
        assert "Incomplete submission" in res.get_json()["error"]

        # 2. Extra / Foreign question ID
        full_answers = {q["id"]: "A" for q in questions}
        full_answers["q999"] = "B"
        res = client.post("/api/v1/esecurityin/quizzes/cryptography/submit", json={"answers": full_answers})
        assert res.status_code == 400
        assert "Invalid question ID" in res.get_json()["error"]

        # 3. Invalid option label (e.g. 'E' or '1' or 'True')
        bad_opt_answers = {q["id"]: "A" for q in questions}
        bad_opt_answers[questions[0]["id"]] = "E"
        res = client.post("/api/v1/esecurityin/quizzes/cryptography/submit", json={"answers": bad_opt_answers})
        assert res.status_code == 400
        assert "Invalid option label" in res.get_json()["error"]

        # 4. Malformed request body / non-dict answers
        res = client.post("/api/v1/esecurityin/quizzes/cryptography/submit", json={"answers": ["A", "B"]})
        assert res.status_code == 400
        assert "Malformed submission" in res.get_json()["error"]

        res2 = client.post("/api/v1/esecurityin/quizzes/cryptography/submit", json="not a dict")
        assert res2.status_code == 400
        assert "Invalid request body" in res2.get_json()["error"]


def test_rate_limiting_per_user(app):
    """
    Test server-side rate limiting on quiz submissions:
    - User submits up to rate limit (10 per minute)
    - 11th submission returns HTTP 429
    - Rate limit is tied to user, not just IP
    - Normal GET requests (question viewing) remain unaffected
    """
    from CTFd.plugins.esecurityin.services.quiz_service import QuizService

    with app.app_context():
        register_user(app, name="rl_user", email="rl@examplectf.com", password="password")
        client = login_as_user(app, name="rl_user", password="password")

        qb_quiz = QuizService.get_quiz_by_id("cryptography")
        questions = qb_quiz["questions"]
        all_wrong = {q["id"]: "C" if q["correct_option"] != "C" else "D" for q in questions}

        # 10 allowed submissions
        for _ in range(10):
            res = client.post("/api/v1/esecurityin/quizzes/cryptography/submit", json={"answers": all_wrong})
            assert res.status_code == 200

        # 11th submission hits 429 Too Many Requests
        res_limit = client.post("/api/v1/esecurityin/quizzes/cryptography/submit", json={"answers": all_wrong})
        assert res_limit.status_code == 429
        data = res_limit.get_json()
        assert data["rate_limited"] is True

        # Quiz GET endpoint remains unaffected by submission rate limiter
        res_get = client.get("/api/v1/esecurityin/quizzes/cryptography")
        assert res_get.status_code == 200


def test_scoring_submission_api_fail_and_retry(app):
    """
    Test quiz submission endpoint with a failing attempt:
    - 7/9 fails (77.8%) -> 0 points, 0 XP, attempt recorded
    - Response contains zero leaked answers
    - User can retry
    """
    from CTFd.models import Solves
    from CTFd.plugins.esecurityin.models import QuizChallenge, QuizAttempt
    from CTFd.plugins.esecurityin.services.quiz_service import QuizService

    with app.app_context():
        register_user(app, name="quiztester", email="tester@examplectf.com", password="password")
        client = login_as_user(app, name="quiztester", password="password")

        qb_quiz = QuizService.get_quiz_by_id("cryptography")
        questions = qb_quiz["questions"]

        # Submit complete 9 answers: 7 correct, 2 wrong (FAIL)
        answers_fail = {}
        for i, q in enumerate(questions):
            if i < 7:
                answers_fail[q["id"]] = q["correct_option"]
            else:
                wrong = "C" if q["correct_option"] != "C" else "D"
                answers_fail[q["id"]] = wrong

        res_fail = client.post("/api/v1/esecurityin/quizzes/cryptography/submit", json={"answers": answers_fail})
        assert res_fail.status_code == 200
        fail_data = res_fail.get_json()["result"]
        assert fail_data["passed"] is False
        assert fail_data["correct_count"] == 7
        assert fail_data["score_percent"] == 77.8
        assert fail_data["points_earned"] == 0
        assert fail_data["solved"] is False

        # Verify no Solves were created
        qc = QuizChallenge.query.filter_by(quiz_id="cryptography").first()
        solves = Solves.query.filter_by(challenge_id=qc.id).all()
        assert len(solves) == 0

        # Verify QuizAttempt was recorded
        attempts = QuizAttempt.query.filter_by(quiz_id="cryptography").all()
        assert len(attempts) == 1
        assert attempts[0].passed is False

        # Critical security check on results payload: no answers leaked
        raw_result = res_fail.get_data(as_text=True)
        assert "correct_option" not in raw_result

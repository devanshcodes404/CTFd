# CyberRealm MCQ Quiz Arena — System Documentation

## 1. Architecture Overview

The CyberRealm MCQ Quiz Arena is an integrated training module within CTFd powered by the `eSecurityIn` gamification plugin and custom `CyberRealm` theme.

```
                      +-----------------------------+
                      |   CyberRealm Theme UI       |
                      |  - /quizzes (Quiz Arena)    |
                      |  - /quizzes/<id> (Runner)   |
                      +--------------+--------------+
                                     |
                                     | (Strictly Sanitized API)
                                     v
                      +-----------------------------+
                      |    eSecurityIn API          |
                      |  /api/v1/esecurityin/quizzes|
                      +--------------+--------------+
                                     |
       +-----------------------------+-----------------------------+
       |                                                           |
       v                                                           v
+-----------------------------+                             +-----------------------------+
|    QuizService Engine       |                             |    CTFd Core & Gamification |
| - 120 Questions (13 Quizzes)|                             | - Challenges / Solves       |
| - 80% Threshold Evaluator   |                             | - UserXP / Level / Streaks  |
| - Server-Side Answer Key    |                             | - Rate Limiter (Redis/Cache)|
+-----------------------------+                             +-----------------------------+
```

---

## 2. The 13 Quizzes & 120 Questions

Extracted verbatim from `docs/source/Cybersecurity_120_MCQs_Question_Bank.pdf` into `CTFd/plugins/esecurityin/data/question_bank.json`.

| Quiz ID | Title | Question Count | Passing Score |
| :--- | :--- | :---: | :---: |
| `footprinting-osint` | Footprinting & OSINT | 9 | 8 / 9 (88.9%) |
| `enumeration` | Enumeration | 9 | 8 / 9 (88.9%) |
| `cryptography` | Cryptography | 9 | 8 / 9 (88.9%) |
| `network-security` | Network Security | 9 | 8 / 9 (88.9%) |
| `web-api-security` | Web & API Security | 9 | 8 / 9 (88.9%) |
| `penetration-testing` | Penetration Testing | 9 | 8 / 9 (88.9%) |
| `linux-endpoint-security` | Linux & Endpoint Security | 9 | 8 / 9 (88.9%) |
| `cloud-security` | Cloud Security | 9 | 8 / 9 (88.9%) |
| `soc-incident-response` | SOC & Incident Response | 9 | 8 / 9 (88.9%) |
| `malware-analysis` | Malware Analysis | 9 | 8 / 9 (88.9%) |
| `wireless-security` | Wireless Security | 10 | 8 / 10 (80.0%) |
| `grc-identity-security` | GRC & Identity Security | 10 | 8 / 10 (80.0%) |
| `secure-development-containers` | Secure Development & Containers | 10 | 8 / 10 (80.0%) |

---

## 3. Administrator Points Configuration & Synchronization

1. **Initial Provisioning:** When the plugin initializes, `QuizService.sync_quiz_challenges()` creates missing `QuizChallenge` records.
2. **Idempotence & Configuration Preservation:** Existing challenges are **never overwritten**. If an administrator updates a quiz's points (`challenge.value`), category, description, or visibility in the CTFd Admin Panel, those values are preserved across application restarts and subsequent synchronizations.
3. **Scoreboard & XP:** The score awarded to the user on completion is the challenge's configured point value (`challenge.value`). The XP pipeline uses this solve to advance user level, streaks, and missions.

---

## 4. Scoring & Attempt Lifecycle

- **Threshold:** $\ge 80\%$ required to pass.
  - 9-question quiz: 8 correct passes (88.9%), 7 correct fails (77.8%).
  - 10-question quiz: 8 correct passes (80.0%), 7 correct fails (70.0%).
- **Failed Attempts:**
  - Persisted in `esecurityin_quiz_attempts` with `passed = False`.
  - Award **zero CTFd points** and **zero CyberRealm XP**.
  - Users can retry the quiz immediately, subject to rate limits.
- **Successful Attempts:**
  - Persisted in `esecurityin_quiz_attempts` with `passed = True`.
  - Inserts a native `Solves` record into CTFd.
  - Fires the existing `eSecurityIn` solve listener inside the same transaction, awarding points and XP.
  - The challenge is marked as conquered; duplicate reward claims are rejected.

---

## 5. Security & Rate Limiting

- **Zero Client Answer Exposure:** Question retrieval endpoints (`GET /api/v1/esecurityin/quizzes/<id>`) filter out `correct_option` and all grading keys. Evaluation results return only aggregate counts (`total_questions`, `correct_count`, `score_percent`, `passed`).
- **Protected Storage:** `data/question_bank.json` is not served as a public or static asset (HTTP requests return 404).
- **Strict Server Validation:** The server rejects missing answers, extra questions, foreign questions, and invalid option labels ($A, B, C, D$ only).
- **Rate Limiting:** `POST /api/v1/esecurityin/quizzes/<id>/submit` is throttled to **10 submissions per 60 seconds per authenticated user** (`rl:quiz_submit:<user_id>`), backed by CTFd's shared cache backend to enforce limits across multi-worker environments. Excess requests receive HTTP 429.
- **Concurrency & Race Conditions:** Protected by database unique constraint `Solves(challenge_id, user_id)` with explicit transactional rollback.

---

## 6. Development & Build Instructions

To recompile frontend assets after editing theme files:
```bash
cd CTFd/themes/cyberrealm
npm run build
```
This generates the bundled JavaScript/CSS in `CTFd/themes/cyberrealm/static/assets/` and updates `CTFd/themes/cyberrealm/static/manifest.json`.

To run the backend test suite:
```powershell
.venv311\Scripts\pytest tests/plugins/esecurityin/test_quiz_backend.py
```


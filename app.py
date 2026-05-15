from __future__ import annotations

import json
import os
import secrets
import shutil
import sqlite3
import subprocess
import tempfile
import time
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database.db"
QUESTIONS_PATH = BASE_DIR / "questions.json"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(days=14),
)


TOPICS = [
    "Arrays",
    "Strings",
    "Hashing",
    "Sliding Window",
    "Two Pointers",
    "Linked List",
    "Stack",
    "Queue",
    "Trees",
    "Graphs",
    "Heap",
    "Binary Search",
    "Greedy",
    "Backtracking",
    "Dynamic Programming",
    "Bit Manipulation",
    "Tries",
    "Math",
]

SUPPLEMENTAL_QUESTIONS = [
    ("Longest Consecutive Sequence", "Hashing", "Medium"),
    ("Minimum Window Substring", "Sliding Window", "Hard"),
    ("LRU Cache", "Linked List", "Medium"),
    ("Implement Queue using Stacks", "Queue", "Easy"),
    ("Kth Largest Element in an Array", "Heap", "Medium"),
    ("Course Schedule", "Graphs", "Medium"),
    ("Word Search", "Backtracking", "Medium"),
    ("Coin Change", "Dynamic Programming", "Medium"),
    ("Counting Bits", "Bit Manipulation", "Easy"),
    ("Implement Trie Prefix Tree", "Tries", "Medium"),
    ("Happy Number", "Math", "Easy"),
    ("Merge Intervals", "Greedy", "Medium"),
    ("Binary Tree Level Order Traversal", "Trees", "Medium"),
]

FALLBACK_QUESTION_POOL = [
    ("Subarray Sum Equals K", "Hashing", "Medium"),
    ("Longest Repeating Character Replacement", "Sliding Window", "Medium"),
    ("Palindrome Linked List", "Linked List", "Easy"),
    ("Daily Temperatures", "Stack", "Medium"),
    ("Number of Islands", "Graphs", "Medium"),
    ("Meeting Rooms II", "Heap", "Medium"),
    ("Search a 2D Matrix", "Binary Search", "Medium"),
    ("Jump Game", "Greedy", "Medium"),
    ("Combination Sum", "Backtracking", "Medium"),
    ("House Robber", "Dynamic Programming", "Medium"),
    ("Single Number", "Bit Manipulation", "Easy"),
    ("Word Break", "Tries", "Medium"),
    ("Pow(x, n)", "Math", "Medium"),
    ("Rotate Image", "Arrays", "Medium"),
    ("Group Anagrams", "Strings", "Medium"),
    ("Top K Frequent Elements", "Heap", "Medium"),
    ("Clone Graph", "Graphs", "Medium"),
    ("Edit Distance", "Dynamic Programming", "Hard"),
    ("Median of Two Sorted Arrays", "Binary Search", "Hard"),
    ("N Queens", "Backtracking", "Hard"),
]

SAMPLE_TESTS = {
    "Two Sum": [
        {"input": "2 7 11 15\n9\n", "output": "0 1", "hidden": False},
        {"input": "3 2 4\n6\n", "output": "1 2", "hidden": True},
    ],
    "Maximum Subarray": [
        {"input": "-2 1 -3 4 -1 2 1 -5 4\n", "output": "6", "hidden": False},
        {"input": "5 4 -1 7 8\n", "output": "23", "hidden": True},
    ],
    "Contains Duplicate": [
        {"input": "1 2 3 1\n", "output": "true", "hidden": False},
        {"input": "1 2 3 4\n", "output": "false", "hidden": True},
    ],
}


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def add_column(conn: sqlite3.Connection, table: str, name: str, definition: str) -> None:
    if name not in column_names(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def init_db() -> None:
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS solved(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                problem TEXT,
                difficulty TEXT,
                solved_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, problem)
            );

            CREATE TABLE IF NOT EXISTS feedback(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                rating INTEGER,
                message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS questions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT UNIQUE,
                topic TEXT,
                difficulty TEXT,
                description TEXT,
                constraints TEXT,
                examples TEXT,
                test_cases TEXT,
                hints TEXT,
                solution TEXT,
                time_complexity TEXT,
                space_complexity TEXT,
                tags TEXT,
                companies TEXT,
                visual_type TEXT,
                is_blind75 INTEGER DEFAULT 0,
                is_neetcode150 INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS submissions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question_id INTEGER,
                language TEXT,
                code TEXT,
                verdict TEXT,
                runtime_ms INTEGER,
                memory_kb INTEGER,
                passed_count INTEGER,
                total_count INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS streaks(
                user_id INTEGER PRIMARY KEY,
                current_streak INTEGER DEFAULT 0,
                longest_streak INTEGER DEFAULT 0,
                last_solved_date TEXT
            );

            CREATE TABLE IF NOT EXISTS bookmarks(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, question_id)
            );

            CREATE TABLE IF NOT EXISTS achievements(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                badge TEXT,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, badge)
            );

            CREATE TABLE IF NOT EXISTS user_stats(
                user_id INTEGER PRIMARY KEY,
                xp INTEGER DEFAULT 0,
                total_submissions INTEGER DEFAULT 0,
                accepted_submissions INTEGER DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS recent_activity(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                detail TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        for table, columns in {
            "users": {"role": "TEXT DEFAULT 'user'", "created_at": "TEXT"},
            "solved": {"solved_at": "TEXT"},
            "feedback": {"created_at": "TEXT"},
            "questions": {
                "constraints": "TEXT",
                "examples": "TEXT",
                "test_cases": "TEXT",
                "hints": "TEXT",
                "solution": "TEXT",
                "time_complexity": "TEXT",
                "space_complexity": "TEXT",
                "tags": "TEXT",
                "companies": "TEXT",
                "visual_type": "TEXT",
                "is_blind75": "INTEGER DEFAULT 0",
                "is_neetcode150": "INTEGER DEFAULT 1",
            },
        }.items():
            for name, definition in columns.items():
                add_column(conn, table, name, definition)


def split_description(description: str) -> tuple[str, str, str]:
    examples = []
    constraints = []
    statement = []
    section = "statement"
    for line in description.splitlines():
        normalized = line.strip().lower()
        if normalized.startswith("example"):
            section = "examples"
        elif normalized.startswith("constraints"):
            section = "constraints"
        if section == "examples":
            examples.append(line)
        elif section == "constraints":
            constraints.append(line)
        else:
            statement.append(line)
    return "\n".join(statement).strip(), "\n".join(examples).strip(), "\n".join(constraints).strip()


def visual_type_for(topic: str) -> str:
    mapping = {
        "Linked List": "linked-list",
        "Trees": "tree",
        "Graphs": "graph",
        "Dynamic Programming": "dp",
        "Sliding Window": "window",
        "Stack": "stack",
        "Queue": "queue",
        "Binary Search": "binary-search",
        "Two Pointers": "two-pointers",
    }
    return mapping.get(topic, "array")


def default_solution(title: str, topic: str) -> str:
    return (
        f"Study the core {topic.lower()} pattern, define the invariant, and solve "
        f"{title} with a single clean pass or the standard optimized pattern for this topic. "
        "Prefer clarity first, then tighten edge cases and complexity."
    )


def enrich_question(raw: dict) -> dict:
    title = raw["title"].strip()
    topic = raw.get("topic", "Arrays").strip()
    difficulty = raw.get("difficulty", "Medium").strip()
    description = raw.get("description", "").strip()
    statement, examples, constraints = split_description(description)
    test_cases = raw.get("test_cases") or SAMPLE_TESTS.get(title) or [
        {"input": "Use the sample input from the statement.", "output": "Expected sample output.", "hidden": False}
    ]
    return {
        "title": title,
        "topic": topic,
        "difficulty": difficulty,
        "description": statement or description,
        "constraints": raw.get("constraints") or constraints,
        "examples": raw.get("examples") or examples,
        "test_cases": json.dumps(test_cases),
        "hints": json.dumps(
            raw.get("hints")
            or [
                f"Identify the main {topic.lower()} pattern before coding.",
                "Write down the state or pointers that must be updated every step.",
                "Optimize by removing repeated work and handling edge cases explicitly.",
            ]
        ),
        "solution": raw.get("solution") or default_solution(title, topic),
        "time_complexity": raw.get("time_complexity") or "See optimized approach",
        "space_complexity": raw.get("space_complexity") or "See optimized approach",
        "tags": json.dumps(raw.get("tags") or [topic, difficulty, "Interview"]),
        "companies": json.dumps(raw.get("companies") or ["Amazon", "Google", "Microsoft"]),
        "visual_type": raw.get("visual_type") or visual_type_for(topic),
        "is_blind75": 1 if raw.get("is_blind75", title in {"Two Sum", "Maximum Subarray", "Valid Anagram"}) else 0,
        "is_neetcode150": 1,
    }


def supplemental_description(title: str, topic: str) -> str:
    return (
        f"Solve {title}, a classic {topic} interview problem.\n\n"
        "Example:\nInput: see generated sample for this pattern\nOutput: expected result\n\n"
        "Constraints:\n1 <= n <= 10^5\nUse an optimized approach suitable for interviews."
    )


def load_questions() -> list[dict]:
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8")) if QUESTIONS_PATH.exists() else []
    titles = {q["title"] for q in questions}
    for title, topic, difficulty in [*SUPPLEMENTAL_QUESTIONS, *FALLBACK_QUESTION_POOL]:
        if title not in titles:
            questions.append(
                {
                    "title": title,
                    "topic": topic,
                    "difficulty": difficulty,
                    "description": supplemental_description(title, topic),
                }
            )
            titles.add(title)
        if len(titles) >= 100:
            break
    unique = []
    seen = set()
    for q in questions:
        if q["title"] in seen:
            continue
        unique.append(q)
        seen.add(q["title"])
        if len(unique) == 100:
            break
    return [enrich_question(q) for q in unique]


def seed_questions() -> None:
    questions = load_questions()
    with get_db() as conn:
        for q in questions:
            existing = conn.execute("SELECT id FROM questions WHERE title=? LIMIT 1", (q["title"],)).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE questions
                    SET topic=:topic,
                        difficulty=:difficulty,
                        description=:description,
                        constraints=:constraints,
                        examples=:examples,
                        test_cases=:test_cases,
                        hints=:hints,
                        solution=:solution,
                        time_complexity=:time_complexity,
                        space_complexity=:space_complexity,
                        tags=:tags,
                        companies=:companies,
                        visual_type=:visual_type,
                        is_blind75=:is_blind75,
                        is_neetcode150=:is_neetcode150
                    WHERE title=:title
                    """,
                    q,
                )
            else:
                conn.execute(
                    """
                    INSERT INTO questions(
                        title, topic, difficulty, description, constraints, examples, test_cases,
                        hints, solution, time_complexity, space_complexity, tags, companies,
                        visual_type, is_blind75, is_neetcode150
                    )
                    VALUES(
                        :title, :topic, :difficulty, :description, :constraints, :examples, :test_cases,
                        :hints, :solution, :time_complexity, :space_complexity, :tags, :companies,
                        :visual_type, :is_blind75, :is_neetcode150
                    )
                    """,
                    q,
                )


def current_user_id() -> int | None:
    return session.get("user_id")


def login_required():
    if "user_id" not in session:
        return redirect("/login")
    return None


def parse_json_field(value, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def question_to_dict(row: sqlite3.Row, solved_titles: set[str] | None = None, bookmarked_ids: set[int] | None = None) -> dict:
    solved_titles = solved_titles or set()
    bookmarked_ids = bookmarked_ids or set()
    return {
        "id": row["id"],
        "title": row["title"],
        "topic": row["topic"],
        "difficulty": row["difficulty"],
        "description": row["description"],
        "constraints": row["constraints"],
        "examples": row["examples"],
        "test_cases": parse_json_field(row["test_cases"], []),
        "hints": parse_json_field(row["hints"], []),
        "solution": row["solution"],
        "time_complexity": row["time_complexity"],
        "space_complexity": row["space_complexity"],
        "tags": parse_json_field(row["tags"], []),
        "companies": parse_json_field(row["companies"], []),
        "visual_type": row["visual_type"],
        "is_blind75": bool(row["is_blind75"]),
        "is_neetcode150": bool(row["is_neetcode150"]),
        "solved": row["title"] in solved_titles,
        "bookmarked": row["id"] in bookmarked_ids,
    }


def ensure_user_stats(conn: sqlite3.Connection, user_id: int) -> None:
    conn.execute("INSERT OR IGNORE INTO user_stats(user_id) VALUES(?)", (user_id,))
    conn.execute("INSERT OR IGNORE INTO streaks(user_id) VALUES(?)", (user_id,))


def record_activity(conn: sqlite3.Connection, user_id: int, action: str, detail: str) -> None:
    conn.execute(
        "INSERT INTO recent_activity(user_id, action, detail) VALUES(?,?,?)",
        (user_id, action, detail),
    )


def update_streak(conn: sqlite3.Connection, user_id: int) -> None:
    today = date.today().isoformat()
    streak = conn.execute("SELECT * FROM streaks WHERE user_id=?", (user_id,)).fetchone()
    if not streak:
        conn.execute(
            "INSERT INTO streaks(user_id, current_streak, longest_streak, last_solved_date) VALUES(?,?,?,?)",
            (user_id, 1, 1, today),
        )
        return
    if streak["last_solved_date"] == today:
        return
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    current = streak["current_streak"] + 1 if streak["last_solved_date"] == yesterday else 1
    longest = max(streak["longest_streak"], current)
    conn.execute(
        "UPDATE streaks SET current_streak=?, longest_streak=?, last_solved_date=? WHERE user_id=?",
        (current, longest, today, user_id),
    )


def award_badges(conn: sqlite3.Connection, user_id: int, solved_count: int) -> None:
    badges = [
        (1, "First Solve", "Solved your first problem."),
        (10, "Momentum", "Solved 10 interview problems."),
        (25, "Pattern Builder", "Solved 25 interview problems."),
        (50, "Interview Ready", "Solved 50 interview problems."),
        (100, "DSA Mastery", "Solved the full 100 problem roadmap."),
    ]
    for threshold, badge, description in badges:
        if solved_count >= threshold:
            conn.execute(
                "INSERT OR IGNORE INTO achievements(user_id, badge, description) VALUES(?,?,?)",
                (user_id, badge, description),
            )


def compile_and_run(language: str, code: str, stdin: str, timeout: int = 3) -> tuple[str, str, int]:
    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        if language == "python":
            source = tmp_path / "main.py"
            source.write_text(code, encoding="utf-8")
            command = ["python", str(source)]
        elif language == "cpp":
            if not shutil.which("g++"):
                return "", "C++ compiler not installed on server.", 1
            source = tmp_path / "main.cpp"
            binary = tmp_path / "main.exe"
            source.write_text(code, encoding="utf-8")
            build = subprocess.run(["g++", str(source), "-O2", "-std=c++17", "-o", str(binary)], capture_output=True, text=True, timeout=timeout)
            if build.returncode != 0:
                return "", build.stderr.strip(), build.returncode
            command = [str(binary)]
        elif language == "c":
            if not shutil.which("gcc"):
                return "", "C compiler not installed on server.", 1
            source = tmp_path / "main.c"
            binary = tmp_path / "main.exe"
            source.write_text(code, encoding="utf-8")
            build = subprocess.run(["gcc", str(source), "-O2", "-o", str(binary)], capture_output=True, text=True, timeout=timeout)
            if build.returncode != 0:
                return "", build.stderr.strip(), build.returncode
            command = [str(binary)]
        elif language == "java":
            if not shutil.which("javac") or not shutil.which("java"):
                return "", "Java runtime/compiler not installed on server.", 1
            source = tmp_path / "Main.java"
            source.write_text(code, encoding="utf-8")
            build = subprocess.run(["javac", str(source)], capture_output=True, text=True, timeout=timeout)
            if build.returncode != 0:
                return "", build.stderr.strip(), build.returncode
            command = ["java", "-cp", str(tmp_path), "Main"]
        else:
            return "", "Unsupported language.", 1

        try:
            process = subprocess.run(command, input=stdin, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return "", "Time Limit Exceeded", 124
    runtime = int((time.perf_counter() - started) * 1000)
    return process.stdout.strip(), process.stderr.strip() or str(runtime), process.returncode


def run_test_cases(question_row: sqlite3.Row, language: str, code: str, include_hidden: bool) -> dict:
    tests = parse_json_field(question_row["test_cases"], [])
    selected = tests if include_hidden else [test for test in tests if not test.get("hidden")]
    if not selected:
        selected = [{"input": "", "output": "", "hidden": False}]
    results = []
    verdict = "Accepted"
    total_runtime = 0
    for index, test in enumerate(selected, start=1):
        stdout, stderr_or_runtime, returncode = compile_and_run(language, code, test.get("input", ""))
        runtime_ms = int(stderr_or_runtime) if stderr_or_runtime.isdigit() else 0
        total_runtime += runtime_ms
        expected = str(test.get("output", "")).strip()
        passed = returncode == 0 and stdout.strip() == expected
        case_verdict = "Accepted" if passed else "Wrong Answer"
        if returncode == 124:
            case_verdict = "Time Limit Exceeded"
        elif returncode != 0:
            case_verdict = "Runtime Error"
        if case_verdict != "Accepted" and verdict == "Accepted":
            verdict = case_verdict
        results.append(
            {
                "case": index,
                "input": test.get("input", ""),
                "expected": expected,
                "output": stdout,
                "stderr": "" if stderr_or_runtime.isdigit() else stderr_or_runtime,
                "hidden": bool(test.get("hidden")),
                "passed": passed,
                "verdict": case_verdict,
                "runtime_ms": runtime_ms,
                "memory_kb": 18000 + len(code),
            }
        )
    return {
        "verdict": verdict,
        "results": results,
        "passed_count": sum(1 for result in results if result["passed"]),
        "total_count": len(results),
        "runtime_ms": total_runtime,
        "memory_kb": 18000 + len(code),
    }


@app.context_processor
def inject_globals():
    return {"topics": TOPICS}


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/learn")
def learn():
    return render_template("learn.html")


@app.route("/support")
def support():
    guard = login_required()
    if guard:
        return guard
    return render_template("support.html")


@app.route("/login")
def login():
    if "user_id" in session:
        return redirect("/dashboard")
    return render_template("login.html")


@app.route("/signup", methods=["POST"])
def signup():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if len(username) < 3 or len(password) < 6:
        return "Username must be 3+ characters and password must be 6+ characters.", 400
    with get_db() as conn:
        try:
            conn.execute(
                "INSERT INTO users(username, password) VALUES(?, ?)",
                (username, generate_password_hash(password)),
            )
        except sqlite3.IntegrityError:
            return "User already exists", 409
    return redirect("/login")


@app.route("/login-user", methods=["POST"])
def login_user():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user and (check_password_hash(user["password"], password) or user["password"] == password):
            if user["password"] == password:
                conn.execute("UPDATE users SET password=? WHERE id=?", (generate_password_hash(password), user["id"]))
            session.permanent = True
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"] or "user"
            ensure_user_stats(conn, user["id"])
            return redirect("/dashboard")
    return "Invalid login credentials", 401


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/dashboard")
def dashboard():
    guard = login_required()
    if guard:
        return guard
    return render_template("dashboard.html")


@app.route("/problems")
def problems():
    guard = login_required()
    if guard:
        return guard
    with get_db() as conn:
        solved = {row["problem"] for row in conn.execute("SELECT problem FROM solved WHERE user_id=?", (current_user_id(),))}
        bookmarks = {
            row["question_id"]
            for row in conn.execute("SELECT question_id FROM bookmarks WHERE user_id=?", (current_user_id(),))
        }
        questions = [
            question_to_dict(row, solved, bookmarks)
            for row in conn.execute("SELECT * FROM questions ORDER BY id")
        ]
    return render_template("problems.html", questions=questions)


@app.route("/question/<int:id>")
def question(id):
    guard = login_required()
    if guard:
        return guard
    with get_db() as conn:
        q = conn.execute("SELECT * FROM questions WHERE id=?", (id,)).fetchone()
        if not q:
            return "Problem not found", 404
        solved = {row["problem"] for row in conn.execute("SELECT problem FROM solved WHERE user_id=?", (current_user_id(),))}
        bookmarks = {
            row["question_id"]
            for row in conn.execute("SELECT question_id FROM bookmarks WHERE user_id=?", (current_user_id(),))
        }
        previous_q = conn.execute("SELECT id FROM questions WHERE id < ? ORDER BY id DESC LIMIT 1", (id,)).fetchone()
        next_q = conn.execute("SELECT id FROM questions WHERE id > ? ORDER BY id ASC LIMIT 1", (id,)).fetchone()
    return render_template(
        "question.html",
        q=question_to_dict(q, solved, bookmarks),
        previous_id=previous_q["id"] if previous_q else None,
        next_id=next_q["id"] if next_q else None,
    )


@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    guard = login_required()
    if guard:
        return guard
    if request.method == "POST":
        rating = int(request.form.get("rating") or 0)
        message = request.form.get("message", "").strip()
        with get_db() as conn:
            conn.execute(
                "INSERT INTO feedback(user_id, rating, message) VALUES(?,?,?)",
                (current_user_id(), rating, message),
            )
        return render_template("feedback.html", success=True)
    return render_template("feedback.html", success=False)


@app.route("/admin")
@app.route("/admin/feedback")
def admin_feedback():
    guard = login_required()
    if guard:
        return guard
    if session.get("role") != "admin":
        return "Admin access required", 403
    with get_db() as conn:
        feedbacks = conn.execute(
            """
            SELECT feedback.*, users.username
            FROM feedback
            LEFT JOIN users ON users.id = feedback.user_id
            ORDER BY feedback.created_at DESC
            """
        ).fetchall()
    return render_template("admin_feedback.html", feedbacks=feedbacks)


@app.route("/leaderboard")
def leaderboard():
    guard = login_required()
    if guard:
        return guard
    with get_db() as conn:
        leaders = conn.execute(
            """
            SELECT users.username, COUNT(solved.id) AS solved_count, COALESCE(user_stats.xp, 0) AS xp
            FROM users
            LEFT JOIN solved ON solved.user_id = users.id
            LEFT JOIN user_stats ON user_stats.user_id = users.id
            GROUP BY users.id
            ORDER BY solved_count DESC, xp DESC
            LIMIT 25
            """
        ).fetchall()
    return render_template("leaderboard.html", leaders=leaders)


@app.route("/arrays")
def arrays():
    return redirect("/problems?topic=Arrays")


@app.route("/progress")
def progress():
    guard = login_required()
    if guard:
        return guard
    with get_db() as conn:
        solved = conn.execute("SELECT COUNT(*) FROM solved WHERE user_id=?", (current_user_id(),)).fetchone()[0]
        total = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    return jsonify({"solved": solved, "total": total})


@app.route("/user-stats")
def user_stats():
    guard = login_required()
    if guard:
        return guard
    user_id = current_user_id()
    with get_db() as conn:
        ensure_user_stats(conn, user_id)
        stats = conn.execute("SELECT * FROM user_stats WHERE user_id=?", (user_id,)).fetchone()
        streak = conn.execute("SELECT * FROM streaks WHERE user_id=?", (user_id,)).fetchone()
        difficulty = {
            row["difficulty"].lower(): row["count"]
            for row in conn.execute(
                """
                SELECT difficulty, COUNT(*) AS count
                FROM solved
                WHERE user_id=?
                GROUP BY difficulty
                """,
                (user_id,),
            )
        }
        topics = [
            dict(row)
            for row in conn.execute(
                """
                SELECT q.topic, COUNT(s.id) AS solved, COUNT(q.id) AS total
                FROM questions q
                LEFT JOIN solved s ON s.problem = q.title AND s.user_id=?
                GROUP BY q.topic
                ORDER BY q.topic
                """,
                (user_id,),
            )
        ]
        recent = [
            dict(row)
            for row in conn.execute(
                "SELECT action, detail, created_at FROM recent_activity WHERE user_id=? ORDER BY created_at DESC LIMIT 8",
                (user_id,),
            )
        ]
        badges = [dict(row) for row in conn.execute("SELECT badge, description FROM achievements WHERE user_id=?", (user_id,))]
    accepted = stats["accepted_submissions"] or 0
    submissions = stats["total_submissions"] or 0
    return jsonify(
        {
            "easy": difficulty.get("easy", 0),
            "medium": difficulty.get("medium", 0),
            "hard": difficulty.get("hard", 0),
            "xp": stats["xp"],
            "accuracy": round((accepted / submissions) * 100, 1) if submissions else 0,
            "streak": streak["current_streak"] if streak else 0,
            "longest_streak": streak["longest_streak"] if streak else 0,
            "topics": topics,
            "recent": recent,
            "badges": badges,
        }
    )


@app.route("/api/problems")
def api_problems():
    guard = login_required()
    if guard:
        return guard
    query = request.args.get("q", "").strip().lower()
    topic = request.args.get("topic", "")
    difficulty = request.args.get("difficulty", "")
    company = request.args.get("company", "").lower()
    status = request.args.get("status", "")
    list_filter = request.args.get("list", "")
    bookmarked = request.args.get("bookmarked", "")
    with get_db() as conn:
        solved = {row["problem"] for row in conn.execute("SELECT problem FROM solved WHERE user_id=?", (current_user_id(),))}
        bookmarks = {
            row["question_id"]
            for row in conn.execute("SELECT question_id FROM bookmarks WHERE user_id=?", (current_user_id(),))
        }
        rows = [question_to_dict(row, solved, bookmarks) for row in conn.execute("SELECT * FROM questions ORDER BY id")]
    filtered = []
    for item in rows:
        if query and query not in f"{item['title']} {item['topic']} {' '.join(item['tags'])}".lower():
            continue
        if topic and item["topic"] != topic:
            continue
        if difficulty and item["difficulty"] != difficulty:
            continue
        if company and company not in " ".join(item["companies"]).lower():
            continue
        if status == "solved" and not item["solved"]:
            continue
        if status == "unsolved" and item["solved"]:
            continue
        if list_filter == "blind75" and not item["is_blind75"]:
            continue
        if list_filter == "neetcode150" and not item["is_neetcode150"]:
            continue
        if bookmarked == "1" and not item["bookmarked"]:
            continue
        filtered.append(item)
    return jsonify({"problems": filtered})


@app.route("/api/bookmark/<int:question_id>", methods=["POST"])
def toggle_bookmark(question_id):
    guard = login_required()
    if guard:
        return guard
    user_id = current_user_id()
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM bookmarks WHERE user_id=? AND question_id=?",
            (user_id, question_id),
        ).fetchone()
        if existing:
            conn.execute("DELETE FROM bookmarks WHERE id=?", (existing["id"],))
            bookmarked = False
        else:
            conn.execute("INSERT OR IGNORE INTO bookmarks(user_id, question_id) VALUES(?,?)", (user_id, question_id))
            bookmarked = True
    return jsonify({"bookmarked": bookmarked})


@app.route("/run-code", methods=["POST"])
def run_code():
    guard = login_required()
    if guard:
        return guard
    data = request.get_json() or {}
    question_id = data.get("question_id")
    title = data.get("question")
    language = data.get("language", "python")
    code = data.get("code", "")
    custom_input = data.get("custom_input")
    with get_db() as conn:
        row = None
        if question_id:
            row = conn.execute("SELECT * FROM questions WHERE id=?", (question_id,)).fetchone()
        if not row and title:
            row = conn.execute("SELECT * FROM questions WHERE title=?", (title,)).fetchone()
    if not row:
        return jsonify({"verdict": "Runtime Error", "results": [{"stderr": "Question not found", "passed": False}]})
    if custom_input is not None:
        stdout, stderr, returncode = compile_and_run(language, code, custom_input)
        verdict = "Accepted" if returncode == 0 else ("Time Limit Exceeded" if returncode == 124 else "Runtime Error")
        return jsonify(
            {
                "verdict": verdict,
                "results": [
                    {
                        "case": "custom",
                        "input": custom_input,
                        "expected": "",
                        "output": stdout,
                        "stderr": "" if stderr.isdigit() else stderr,
                        "passed": returncode == 0,
                        "verdict": verdict,
                        "runtime_ms": int(stderr) if stderr.isdigit() else 0,
                        "memory_kb": 18000 + len(code),
                    }
                ],
            }
        )
    return jsonify(run_test_cases(row, language, code, include_hidden=False))


@app.route("/submit-code", methods=["POST"])
def submit_code():
    guard = login_required()
    if guard:
        return guard
    data = request.get_json() or {}
    question_id = int(data.get("question_id"))
    language = data.get("language", "python")
    code = data.get("code", "")
    user_id = current_user_id()
    with get_db() as conn:
        row = conn.execute("SELECT * FROM questions WHERE id=?", (question_id,)).fetchone()
        if not row:
            return jsonify({"verdict": "Runtime Error", "results": []}), 404
        result = run_test_cases(row, language, code, include_hidden=True)
        ensure_user_stats(conn, user_id)
        conn.execute(
            """
            INSERT INTO submissions(user_id, question_id, language, code, verdict, runtime_ms, memory_kb, passed_count, total_count)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                user_id,
                question_id,
                language,
                code,
                result["verdict"],
                result["runtime_ms"],
                result["memory_kb"],
                result["passed_count"],
                result["total_count"],
            ),
        )
        accepted = result["verdict"] == "Accepted"
        conn.execute(
            """
            UPDATE user_stats
            SET total_submissions = total_submissions + 1,
                accepted_submissions = accepted_submissions + ?,
                xp = xp + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id=?
            """,
            (1 if accepted else 0, 15 if accepted else 2, user_id),
        )
        if accepted:
            conn.execute(
                "INSERT OR IGNORE INTO solved(user_id, problem, difficulty) VALUES(?,?,?)",
                (user_id, row["title"], row["difficulty"]),
            )
            update_streak(conn, user_id)
            solved_count = conn.execute("SELECT COUNT(*) FROM solved WHERE user_id=?", (user_id,)).fetchone()[0]
            award_badges(conn, user_id, solved_count)
            record_activity(conn, user_id, "Solved", row["title"])
        else:
            record_activity(conn, user_id, "Submitted", f"{row['title']} - {result['verdict']}")
    return jsonify(result)


@app.route("/api/dashboard")
def api_dashboard():
    guard = login_required()
    if guard:
        return guard
    user_id = current_user_id()
    with get_db() as conn:
        solved_titles = {row["problem"] for row in conn.execute("SELECT problem FROM solved WHERE user_id=?", (user_id,))}
        total = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        daily = conn.execute("SELECT * FROM questions ORDER BY (id + CAST(strftime('%j','now') AS INTEGER)) % 100 LIMIT 1").fetchone()
        weak = conn.execute(
            """
            SELECT q.topic, COUNT(s.id) AS solved, COUNT(q.id) AS total
            FROM questions q
            LEFT JOIN solved s ON s.problem = q.title AND s.user_id=?
            GROUP BY q.topic
            ORDER BY (CAST(COUNT(s.id) AS REAL) / COUNT(q.id)) ASC, COUNT(q.id) DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        recommended = [
            question_to_dict(row, solved_titles)
            for row in conn.execute(
                """
                SELECT *
                FROM questions
                WHERE title NOT IN (SELECT problem FROM solved WHERE user_id=?)
                ORDER BY CASE difficulty WHEN 'Easy' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, id
                LIMIT 5
                """,
                (user_id,),
            )
        ]
        heatmap = [
            dict(row)
            for row in conn.execute(
                """
                SELECT date(solved_at) AS day, COUNT(*) AS count
                FROM solved
                WHERE user_id=? AND solved_at >= date('now', '-120 day')
                GROUP BY date(solved_at)
                """,
                (user_id,),
            )
        ]
    return jsonify(
        {
            "solved": len(solved_titles),
            "total": total,
            "daily": question_to_dict(daily, solved_titles) if daily else None,
            "weak_area": dict(weak) if weak else None,
            "recommended": recommended,
            "heatmap": heatmap,
        }
    )


init_db()
seed_questions()


if __name__ == "__main__":
    app.run(debug=True)

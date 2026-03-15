from flask import Flask, render_template, request, jsonify, session, redirect
import subprocess
import tempfile
import os
import sqlite3

app = Flask(__name__)
app.secret_key = "secret123"


# ---------------- DATABASE ---------------- #

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS solved(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        problem TEXT,
        difficulty TEXT
    )
    """)

    conn.commit()
    conn.close()


init_db()


# ---------------- HOME ---------------- #

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/learn")
def learn():
    return render_template("learn.html")


# ---------------- LOGIN PAGE ---------------- #

@app.route("/login")
def login():

    if "user_id" in session:
        return redirect("/dashboard")

    return render_template("login.html")


# ---------------- SIGNUP ---------------- #

@app.route("/signup", methods=["POST"])
def signup():

    username = request.form["username"]
    password = request.form["password"]

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users(username,password) VALUES(?,?)",
            (username, password)
        )
        conn.commit()

    except:
        return "User already exists"

    conn.close()

    return redirect("/login")


# ---------------- LOGIN USER ---------------- #

@app.route("/login-user", methods=["POST"])
def login_user():

    username = request.form["username"]
    password = request.form["password"]

    conn = get_db()
    cursor = conn.cursor()

    user = cursor.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, password)
    ).fetchone()

    conn.close()

    if user:
        session["user_id"] = user["id"]
        session["username"] = username
        return redirect("/dashboard")

    return "Invalid login credentials"


# ---------------- LOGOUT ---------------- #

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------------- DASHBOARD ---------------- #

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    return render_template("dashboard.html")


# ---------------- PROBLEMS PAGE ---------------- #

@app.route("/problems")
def problems():

    if "user_id" not in session:
        return redirect("/login")

    return render_template("problems.html")


# ---------------- PROBLEM PAGE ---------------- #

@app.route("/two-sum")
def two_sum():

    if "user_id" not in session:
        return redirect("/login")

    return render_template("two_sum.html")


# ---------------- USER PROGRESS ---------------- #

@app.route("/progress")
def progress():

    if "user_id" not in session:
        return jsonify({"solved": 0, "total": 100})

    conn = get_db()
    cursor = conn.cursor()

    solved = cursor.execute(
        "SELECT COUNT(DISTINCT problem) FROM solved WHERE user_id=?",
        (session["user_id"],)
    ).fetchone()[0]

    conn.close()

    return jsonify({
        "solved": solved,
        "total": 100
    })


# ---------------- USER STATS ---------------- #

@app.route("/user-stats")
def user_stats():

    if "user_id" not in session:
        return jsonify({"easy": 0, "medium": 0, "hard": 0})

    conn = get_db()
    cursor = conn.cursor()

    easy = cursor.execute(
        "SELECT COUNT(*) FROM solved WHERE user_id=? AND difficulty='easy'",
        (session["user_id"],)
    ).fetchone()[0]

    medium = cursor.execute(
        "SELECT COUNT(*) FROM solved WHERE user_id=? AND difficulty='medium'",
        (session["user_id"],)
    ).fetchone()[0]

    hard = cursor.execute(
        "SELECT COUNT(*) FROM solved WHERE user_id=? AND difficulty='hard'",
        (session["user_id"],)
    ).fetchone()[0]

    conn.close()

    return jsonify({
        "easy": easy,
        "medium": medium,
        "hard": hard
    })


# ---------------- LEADERBOARD ---------------- #

@app.route("/leaderboard")
def leaderboard():

    conn = get_db()
    cursor = conn.cursor()

    users = cursor.execute("""
        SELECT users.username, COUNT(solved.problem) as solved_count
        FROM users
        LEFT JOIN solved
        ON users.id = solved.user_id
        GROUP BY users.id
        ORDER BY solved_count DESC
        LIMIT 10
    """).fetchall()

    conn.close()

    return render_template("leaderboard.html", users=users)


# ---------------- CODE RUNNER ---------------- #

@app.route("/run-code", methods=["POST"])
def run_code():

    if "user_id" not in session:
        return jsonify({"results": ["Login required"]})

    code = request.json.get("code")

    test_cases = [
        {"input": "2 7 11 15\n9", "output": "0 1"},
        {"input": "3 2 4\n6", "output": "1 2"},
        {"input": "3 3\n6", "output": "0 1"}
    ]

    results = []

    try:

        suffix = ".py"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            temp.write(code.encode())
            temp_path = temp.name

        for case in test_cases:

            result = subprocess.run(
                ["python", temp_path],
                input=case["input"],
                text=True,
                capture_output=True,
                timeout=5
            )

            user_output = result.stdout.strip()

            if user_output == case["output"]:
                results.append("Passed ✅")
            else:
                results.append(
                    f"Failed ❌ | Expected: {case['output']} | Got: {user_output}"
                )

        if all("Passed" in r for r in results):

            conn = get_db()
            cursor = conn.cursor()

            already = cursor.execute(
                "SELECT * FROM solved WHERE user_id=? AND problem=?",
                (session["user_id"], "two-sum")
            ).fetchone()

            if not already:
                cursor.execute(
                    "INSERT INTO solved(user_id,problem,difficulty) VALUES(?,?,?)",
                    (session["user_id"], "two-sum", "easy")
                )

                conn.commit()

            conn.close()

        os.remove(temp_path)

        return jsonify({"results": results})

    except Exception as e:
        return jsonify({"results": [str(e)]})


# ---------------- RUN SERVER ---------------- #

if __name__ == "__main__":
    app.run(debug=True)
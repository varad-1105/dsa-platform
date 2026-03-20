from flask import Flask, render_template, request, jsonify, session, redirect
import subprocess
import tempfile
import os
import sqlite3

app = Flask(__name__)
app.secret_key = "secret123"


# ---------------- DATABASE ---------------- #

def get_db():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "database.db")

    conn = sqlite3.connect(db_path)
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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS feedback(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        rating INTEGER,
        message TEXT
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


# ---------------- SUPPORT PAGE ---------------- #

@app.route("/support")
def support():
    return render_template("support.html")


# ---------------- LOGIN ---------------- #

@app.route("/login")
def login():
    if "user_id" in session:
        return redirect("/dashboard")
    return render_template("login.html")


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


# ---------------- PROBLEMS ---------------- #

@app.route("/problems")
def problems():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("problems.html")


@app.route("/two-sum")
def two_sum():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("two_sum.html")


# ---------------- FEEDBACK ---------------- #

@app.route("/feedback", methods=["GET", "POST"])
def feedback():

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        rating = request.form["rating"]
        message = request.form["message"]

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO feedback(user_id, rating, message) VALUES(?,?,?)",
            (session["user_id"], rating, message)
        )

        conn.commit()
        conn.close()

        return render_template("feedback.html", success=True)

    return render_template("feedback.html", success=False)


# ---------------- ADMIN FEEDBACK (ONLY YOU) ---------------- #

@app.route("/admin-feedback")
def admin_feedback():

    if "username" not in session or session["username"] != "Varad":
        return "Access Denied ❌"

    conn = get_db()
    cursor = conn.cursor()

    feedbacks = cursor.execute("""
        SELECT users.username, feedback.rating, feedback.message
        FROM feedback
        LEFT JOIN users
        ON feedback.user_id = users.id
        ORDER BY feedback.id DESC
    """).fetchall()

    conn.close()

    return render_template("admin_feedback.html", feedbacks=feedbacks)


# ---------------- PROGRESS ---------------- #

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
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as temp:
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

            if result.stdout.strip() == case["output"]:
                results.append("Passed ✅")
            else:
                results.append("Failed ❌")

        os.remove(temp_path)
        return jsonify({"results": results})

    except Exception as e:
        return jsonify({"results": [str(e)]})


# ---------------- RUN ---------------- #

if __name__ == "__main__":
    app.run(debug=True)
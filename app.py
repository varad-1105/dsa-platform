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

    # USERS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    # SOLVED
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS solved(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        problem TEXT,
        difficulty TEXT
    )
    """)

    # FEEDBACK
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS feedback(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        rating INTEGER,
        message TEXT
    )
    """)

    # QUESTIONS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        topic TEXT,
        difficulty TEXT,
        company TEXT
    )
    """)

    conn.commit()
    conn.close()


init_db()


# ---------------- INSERT QUESTIONS ---------------- #

def seed_questions():
    conn = get_db()
    cursor = conn.cursor()

    # 🔥 CLEAR OLD DATA (only for fix)
    cursor.execute("DELETE FROM questions")

    questions = [

    # ARRAYS
    ("Two Sum","Arrays","Easy","Google, Amazon"),
    ("Contains Duplicate","Arrays","Easy","Amazon"),
    ("Valid Anagram","Arrays","Easy","Google"),
    ("Group Anagrams","Arrays","Medium","Amazon"),
    ("Top K Frequent Elements","Arrays","Medium","Facebook"),
    ("Product of Array Except Self","Arrays","Medium","Amazon"),
    ("Longest Consecutive Sequence","Arrays","Hard","Google"),

    # TWO POINTERS
    ("Valid Parentheses","Two Pointers","Easy","Amazon"),
    ("Two Sum II","Two Pointers","Easy","Google"),
    ("3Sum","Two Pointers","Medium","Facebook"),
    ("Container With Most Water","Two Pointers","Medium","Amazon"),
    ("Trapping Rain Water","Two Pointers","Hard","Google"),

    # SLIDING WINDOW
    ("Best Time to Buy and Sell Stock","Sliding Window","Easy","Amazon"),
    ("Longest Substring Without Repeating Characters","Sliding Window","Medium","Google"),
    ("Permutation in String","Sliding Window","Medium","Facebook"),
    ("Minimum Window Substring","Sliding Window","Hard","Google"),
    ("Sliding Window Maximum","Sliding Window","Hard","Amazon"),

    # STACK
    ("Valid Parentheses","Stack","Easy","Amazon"),
    ("Min Stack","Stack","Medium","Google"),
    ("Evaluate Reverse Polish Notation","Stack","Medium","Amazon"),
    ("Generate Parentheses","Stack","Medium","Google"),
    ("Daily Temperatures","Stack","Medium","Amazon"),
    ("Car Fleet","Stack","Medium","Google"),
    ("Largest Rectangle in Histogram","Stack","Hard","Amazon"),

    # BINARY SEARCH
    ("Binary Search","Binary Search","Easy","Google"),
    ("Search a 2D Matrix","Binary Search","Medium","Amazon"),
    ("Koko Eating Bananas","Binary Search","Medium","Google"),
    ("Find Minimum in Rotated Sorted Array","Binary Search","Medium","Amazon"),
    ("Search in Rotated Sorted Array","Binary Search","Medium","Google"),
    ("Time Based Key Value Store","Binary Search","Medium","Amazon"),
    ("Median of Two Sorted Arrays","Binary Search","Hard","Google"),

    # LINKED LIST
    ("Reverse Linked List","Linked List","Easy","Amazon"),
    ("Merge Two Sorted Lists","Linked List","Easy","Google"),
    ("Linked List Cycle","Linked List","Easy","Facebook"),
    ("Reorder List","Linked List","Medium","Amazon"),
    ("Remove Nth Node From End","Linked List","Medium","Google"),
    ("Copy List With Random Pointer","Linked List","Medium","Amazon"),
    ("Add Two Numbers","Linked List","Medium","Google"),
    ("LRU Cache","Linked List","Hard","Amazon"),
    ("Merge K Sorted Lists","Linked List","Hard","Google"),
    ("Reverse Nodes in K Group","Linked List","Hard","Amazon"),

    # TREES
    ("Maximum Depth of Binary Tree","Trees","Easy","Google"),
    ("Diameter of Binary Tree","Trees","Easy","Amazon"),
    ("Balanced Binary Tree","Trees","Easy","Google"),
    ("Same Tree","Trees","Easy","Amazon"),
    ("Subtree of Another Tree","Trees","Easy","Facebook"),
    ("Lowest Common Ancestor","Trees","Medium","Google"),
    ("Binary Tree Level Order Traversal","Trees","Medium","Amazon"),
    ("Binary Tree Right Side View","Trees","Medium","Google"),
    ("Count Good Nodes","Trees","Medium","Amazon"),
    ("Validate BST","Trees","Medium","Google"),
    ("Kth Smallest Element","Trees","Medium","Amazon"),
    ("Construct Tree","Trees","Medium","Google"),
    ("Binary Tree Max Path Sum","Trees","Hard","Amazon"),
    ("Serialize Deserialize Tree","Trees","Hard","Google"),

    ]

    cursor.executemany(
        "INSERT INTO questions(title, topic, difficulty, company) VALUES (?,?,?,?)",
        questions
    )

    conn.commit()
    conn.close()


seed_questions()


# ---------------- HOME ---------------- #

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/learn")
def learn():
    return render_template("learn.html")


# ---------------- SUPPORT ---------------- #

@app.route("/support")
def support():
    if "user_id" not in session:
        return redirect("/login")
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

    conn = get_db()
    cursor = conn.cursor()

    questions = cursor.execute("SELECT * FROM questions").fetchall()

    conn.close()

    return render_template("problems.html", questions=questions)


# ---------------- PROGRESS (RESTORED) ---------------- #

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


# ---------------- RUN CODE (RESTORED) ---------------- #

@app.route("/run-code", methods=["POST"])
def run_code():

    if "user_id" not in session:
        return jsonify({"results": ["Login required"]})

    code = request.json.get("code")

    test_cases = [
        {"input": "2 7 11 15\n9", "output": "0 1"},
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

            results.append("Passed ✅" if result.stdout.strip() == case["output"] else "Failed ❌")

        os.remove(temp_path)
        return jsonify({"results": results})

    except Exception as e:
        return jsonify({"results": [str(e)]})


# ---------------- RUN ---------------- #

if __name__ == "__main__":
    app.run(debug=True)
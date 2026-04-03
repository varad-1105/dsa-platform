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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        topic TEXT,
        difficulty TEXT,
        description TEXT
    )
    """)

    conn.commit()
    conn.close()


# ---------------- SEED QUESTIONS ---------------- #

def seed_questions():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM questions")

    questions = [

    # ARRAYS
    ("Two Sum","Arrays","Easy",
     "Given an array nums and target, return indices of two numbers.\n\nExample:\nInput: [2,7,11,15], target=9\nOutput: [0,1]"),

    ("Contains Duplicate","Arrays","Easy",
     "Return true if any value appears twice.\n\nExample:\nInput: [1,2,3,1]\nOutput: true"),

    ("Valid Anagram","Arrays","Easy",
     "Check if two strings are anagrams.\n\nExample:\nInput: 'anagram','nagaram'\nOutput: true"),

    ("Group Anagrams","Arrays","Medium",
     "Group all anagrams together."),

    ("Top K Frequent Elements","Arrays","Medium",
     "Return k most frequent elements."),

    ("Product Except Self","Arrays","Medium",
     "Return product array except self."),

    ("Longest Consecutive Sequence","Arrays","Hard",
     "Find longest consecutive sequence."),

    # TWO POINTERS
    ("3Sum","Two Pointers","Medium",
     "Find triplets that sum to zero."),

    ("Container With Most Water","Two Pointers","Medium",
     "Find max water container."),

    ("Trapping Rain Water","Two Pointers","Hard",
     "Calculate trapped rain water."),

    # SLIDING WINDOW
    ("Best Time to Buy Sell Stock","Sliding Window","Easy",
     "Maximize stock profit."),

    ("Longest Substring Without Repeating","Sliding Window","Medium",
     "Longest substring without repeating characters."),

    ("Minimum Window Substring","Sliding Window","Hard",
     "Find smallest substring containing all chars."),

    # STACK
    ("Valid Parentheses","Stack","Easy",
     "Check valid parentheses."),

    ("Min Stack","Stack","Medium",
     "Stack with min."),

    ("Evaluate Reverse Polish Notation","Stack","Medium",
     "Evaluate postfix expression."),

    # BINARY SEARCH
    ("Binary Search","Binary Search","Easy",
     "Search element in sorted array."),

    ("Search 2D Matrix","Binary Search","Medium",
     "Search element in matrix."),

    # LINKED LIST
    ("Reverse Linked List","Linked List","Easy",
     "Reverse list."),

    ("Merge Two Sorted Lists","Linked List","Easy",
     "Merge lists."),

    # TREES
    ("Maximum Depth Binary Tree","Trees","Easy",
     "Find depth."),

    ("Balanced Binary Tree","Trees","Easy",
     "Check balance."),

    # GRAPH
    ("Number of Islands","Graphs","Medium",
     "Count islands in grid."),

    ("Clone Graph","Graphs","Medium",
     "Clone graph."),

    ("Course Schedule","Graphs","Medium",
     "Check if courses can be completed."),

    # DP
    ("Climbing Stairs","DP","Easy",
     "Count ways to climb stairs."),

    ("House Robber","DP","Medium",
     "Max money without robbing adjacent houses."),

    ("Coin Change","DP","Medium",
     "Find minimum coins required."),

    ("Longest Increasing Subsequence","DP","Medium",
     "Find LIS."),

    # BACKTRACKING
    ("Subsets","Backtracking","Medium",
     "Generate all subsets."),

    ("Permutations","Backtracking","Medium",
     "Generate permutations."),

    ("Combination Sum","Backtracking","Medium",
     "Find combinations summing to target."),

    ("N Queens","Backtracking","Hard",
     "Place queens on board."),

    ]

    cursor.executemany(
        "INSERT INTO questions(title, topic, difficulty, description) VALUES (?,?,?,?)",
        questions
    )

    conn.commit()
    conn.close()


# ---------------- INIT ---------------- #

init_db()
seed_questions()


# ---------------- ROUTES ---------------- #

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/learn")
def learn():
    return render_template("learn.html")


@app.route("/support")
def support():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("support.html")


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
    try:
        conn.execute("INSERT INTO users(username,password) VALUES(?,?)",(username,password))
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
    user = conn.execute("SELECT * FROM users WHERE username=? AND password=?",(username,password)).fetchone()
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


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("dashboard.html")


@app.route("/problems")
def problems():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    questions = conn.execute("SELECT * FROM questions").fetchall()
    conn.close()

    return render_template("problems.html", questions=questions)


@app.route("/question/<int:id>")
def question(id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    q = conn.execute("SELECT * FROM questions WHERE id=?", (id,)).fetchone()
    conn.close()

    return render_template("question.html", q=q)


@app.route("/feedback", methods=["GET","POST"])
def feedback():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        conn = get_db()
        conn.execute("INSERT INTO feedback(user_id,rating,message) VALUES(?,?,?)",
                     (session["user_id"],request.form["rating"],request.form["message"]))
        conn.commit()
        conn.close()
        return render_template("feedback.html",success=True)

    return render_template("feedback.html",success=False)


@app.route("/progress")
def progress():
    return jsonify({"solved":0,"total":100})


@app.route("/run-code",methods=["POST"])
def run_code():
    return jsonify({"results":["Working"]})


if __name__ == "__main__":
    app.run(debug=True)
"""
Flask Application for AI-Based Quiz Generator from PDF / Notes
BSc Computer Science Final Project
"""

import os
import json
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, g
)
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

from services.ai_service import extract_text_from_pdf, generate_quiz

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "college_quiz_generator_secret_key_2026")
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quiz_database.db")


# ---------------------------------------------------------
# DATABASE UTILITIES
# ---------------------------------------------------------

def get_db():
    """Connect to SQLite database and use Row factory."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error):
    """Close the database connection at the end of request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Initialize database tables."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Quizzes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # Questions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            question_type TEXT NOT NULL,
            options TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            explanation TEXT,
            FOREIGN KEY (quiz_id) REFERENCES quizzes (id) ON DELETE CASCADE
        )
    """)

    # Quiz Attempts table for tracking history & scores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            correct_answers INTEGER DEFAULT 0,
            wrong_answers INTEGER DEFAULT 0,
            unanswered INTEGER DEFAULT 0,
            percentage REAL NOT NULL,
            user_answers TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (quiz_id) REFERENCES quizzes (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # Check and safely add columns to quiz_attempts if migrating from earlier schema
    cursor.execute("PRAGMA table_info(quiz_attempts)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    if "correct_answers" not in existing_cols:
        cursor.execute("ALTER TABLE quiz_attempts ADD COLUMN correct_answers INTEGER DEFAULT 0")
    if "wrong_answers" not in existing_cols:
        cursor.execute("ALTER TABLE quiz_attempts ADD COLUMN wrong_answers INTEGER DEFAULT 0")
    if "unanswered" not in existing_cols:
        cursor.execute("ALTER TABLE quiz_attempts ADD COLUMN unanswered INTEGER DEFAULT 0")
    if "created_at" not in existing_cols:
        cursor.execute("ALTER TABLE quiz_attempts ADD COLUMN created_at TIMESTAMP")

    # Answers table for storing every individual submitted answer
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            selected_answer TEXT,
            is_correct BOOLEAN NOT NULL,
            FOREIGN KEY (attempt_id) REFERENCES quiz_attempts (id) ON DELETE CASCADE,
            FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


# ---------------------------------------------------------
# AUTHENTICATION DECORATOR
# ---------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ---------------------------------------------------------
# CONTEXT PROCESSORS
# ---------------------------------------------------------

@app.context_processor
def inject_user():
    """Inject logged-in user into all templates."""
    user = None
    if "user_id" in session:
        db = get_db()
        user = db.execute("SELECT id, name, email FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    return {"current_user": user}


# ---------------------------------------------------------
# GENERAL ROUTES
# ---------------------------------------------------------

@app.route("/")
def index():
    """Home landing page."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


# ---------------------------------------------------------
# AUTHENTICATION ROUTES
# ---------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    """User registration."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validation
        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html", name=name, email=email)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("register.html", name=name, email=email)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html", name=name, email=email)

        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            flash("An account with this email already exists. Please log in.", "warning")
            return redirect(url_for("login"))

        # Hash password securely
        hashed_password = generate_password_hash(password)

        try:
            db.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (name, email, hashed_password)
            )
            db.commit()
            flash("Registration successful! You can now log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            db.rollback()
            flash(f"Error during registration: {str(e)}", "danger")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """User login."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template("login.html", email=email)

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password. Please try again.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Log out user."""
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("login"))


# ---------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    """User dashboard with stats and quick links."""
    db = get_db()
    user_id = session["user_id"]

    # Statistics
    quiz_count = db.execute(
        "SELECT COUNT(*) as count FROM quizzes WHERE user_id = ?", (user_id,)
    ).fetchone()["count"]

    attempt_count = db.execute(
        "SELECT COUNT(*) as count FROM quiz_attempts WHERE user_id = ?", (user_id,)
    ).fetchone()["count"]

    avg_score = db.execute(
        "SELECT AVG(percentage) as avg_score FROM quiz_attempts WHERE user_id = ?", (user_id,)
    ).fetchone()["avg_score"] or 0.0

    # Recent Quizzes
    recent_quizzes = db.execute("""
        SELECT q.id, q.title, q.difficulty, q.created_at,
               COUNT(k.id) as question_count
        FROM quizzes q
        LEFT JOIN questions k ON q.id = k.quiz_id
        WHERE q.user_id = ?
        GROUP BY q.id
        ORDER BY q.created_at DESC
        LIMIT 5
    """, (user_id,)).fetchall()

    return render_template(
        "dashboard.html",
        quiz_count=quiz_count,
        attempt_count=attempt_count,
        avg_score=round(avg_score, 1),
        recent_quizzes=recent_quizzes
    )


# ---------------------------------------------------------
# UPLOAD PDF & PASTE NOTES / GENERATE QUIZ
# ---------------------------------------------------------

@app.route("/upload", methods=["GET"])
@login_required
def upload():
    """Upload PDF or paste notes interface."""
    return render_template("upload.html")


@app.route("/api/extract-pdf", methods=["POST"])
@login_required
def api_extract_pdf():
    """API endpoint to extract text from an uploaded PDF."""
    if "pdf_file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded."}), 400

    file = request.files["pdf_file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected."}), 400

    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"success": False, "error": "Only PDF files are supported."}), 400

    try:
        extracted_text = extract_text_from_pdf(file.stream)
        return jsonify({
            "success": True,
            "filename": file.filename,
            "text": extracted_text,
            "char_count": len(extracted_text),
            "word_count": len(extracted_text.split())
        })
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to extract PDF text: {str(e)}"}), 500


@app.route("/generate-quiz", methods=["POST"])
@login_required
def handle_generate_quiz():
    """Generate quiz using AI service and return for preview."""
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    title = data.get("title", "").strip() or "Untitled Quiz"
    difficulty = data.get("difficulty", "Medium")
    question_type = data.get("question_type", "MCQ")
    
    try:
        num_questions = int(data.get("num_questions", 5))
    except (ValueError, TypeError):
        num_questions = 5

    num_questions = max(1, min(20, num_questions))

    if not text or len(text) < 20:
        return jsonify({
            "success": False,
            "error": "Please provide sufficient study text or notes (at least 20 characters)."
        }), 400

    try:
        questions, mode_desc = generate_quiz(
            text=text,
            num_questions=num_questions,
            difficulty=difficulty,
            question_type=question_type
        )

        return jsonify({
            "success": True,
            "title": title,
            "difficulty": difficulty,
            "question_type": question_type,
            "mode": mode_desc,
            "questions": questions
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to generate quiz: {str(e)}"
        }), 500


@app.route("/quiz/save", methods=["POST"])
@login_required
def save_quiz():
    """Save generated and possibly edited quiz to the database."""
    data = request.get_json() or {}
    title = data.get("title", "").strip() or "Untitled Study Quiz"
    difficulty = data.get("difficulty", "Medium")
    questions = data.get("questions", [])

    if not questions or not isinstance(questions, list):
        return jsonify({"success": False, "error": "No questions provided to save."}), 400

    db = get_db()
    user_id = session["user_id"]

    try:
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO quizzes (user_id, title, difficulty) VALUES (?, ?, ?)",
            (user_id, title, difficulty)
        )
        quiz_id = cursor.lastrowid

        for q in questions:
            q_text = q.get("question", "").strip()
            q_type = q.get("question_type", "MCQ")
            options = q.get("options", [])
            correct_ans = q.get("correct_answer", "").strip()
            explanation = q.get("explanation", "").strip()

            if not q_text or not options:
                continue

            cursor.execute("""
                INSERT INTO questions (quiz_id, question, question_type, options, correct_answer, explanation)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                quiz_id,
                q_text,
                q_type,
                json.dumps(options),
                correct_ans,
                explanation
            ))

        db.commit()
        return jsonify({"success": True, "quiz_id": quiz_id, "message": "Quiz saved successfully!"})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": f"Failed to save quiz: {str(e)}"}), 500


# ---------------------------------------------------------
# ATTEMPT QUIZ
# ---------------------------------------------------------

@app.route("/quiz/<int:quiz_id>")
@login_required
def attempt_quiz(quiz_id):
    """Attempt quiz page."""
    db = get_db()
    user_id = session["user_id"]

    # Secure query: ensure quiz belongs to logged-in user
    quiz = db.execute(
        "SELECT * FROM quizzes WHERE id = ? AND user_id = ?",
        (quiz_id, user_id)
    ).fetchone()

    if not quiz:
        flash("Quiz not found or unauthorized access.", "danger")
        return redirect(url_for("dashboard"))

    raw_questions = db.execute(
        "SELECT id, question, question_type, options FROM questions WHERE quiz_id = ? ORDER BY id ASC",
        (quiz_id,)
    ).fetchall()

    if not raw_questions:
        flash("This quiz has no questions.", "warning")
        return redirect(url_for("history"))

    # CRITICAL SECURITY: Never pass correct_answer or explanation to the attempt page!
    questions = []
    for q in raw_questions:
        questions.append({
            "id": q["id"],
            "question": q["question"],
            "question_type": q["question_type"],
            "options": json.loads(q["options"])
        })

    return render_template("quiz.html", quiz=quiz, questions=questions)


@app.route("/quiz/<int:quiz_id>/submit", methods=["POST"])
@login_required
def submit_quiz(quiz_id):
    """Calculate score, record attempt and answers in DB, and return redirect."""
    db = get_db()
    user_id = session["user_id"]

    # Verify quiz exists and belongs to the current user
    quiz = db.execute(
        "SELECT * FROM quizzes WHERE id = ? AND user_id = ?",
        (quiz_id, user_id)
    ).fetchone()

    if not quiz:
        return jsonify({"success": False, "error": "Quiz not found or unauthorized."}), 404

    user_answers = request.get_json() or {}

    # Query correct answers directly from database
    questions = db.execute(
        "SELECT id, question, question_type, options, correct_answer, explanation FROM questions WHERE quiz_id = ? ORDER BY id ASC",
        (quiz_id,)
    ).fetchall()

    total_questions = len(questions)
    if total_questions == 0:
        return jsonify({"success": False, "error": "Quiz contains no questions."}), 400

    correct_answers = 0
    wrong_answers = 0
    unanswered_count = 0
    evaluated_answers = []

    for q in questions:
        qid_str = str(q["id"])
        selected_option = user_answers.get(qid_str, "").strip()
        correct_option = q["correct_answer"].strip()

        if not selected_option:
            unanswered_count += 1
            is_correct = False
        elif selected_option == correct_option:
            correct_answers += 1
            is_correct = True
        else:
            wrong_answers += 1
            is_correct = False

        evaluated_answers.append({
            "question_id": q["id"],
            "selected_answer": selected_option,
            "is_correct": 1 if is_correct else 0
        })

    score = correct_answers
    percentage = round((score / total_questions) * 100, 1)

    # Save attempt in quiz_attempts table
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO quiz_attempts (
            quiz_id, user_id, score, total_questions, correct_answers, 
            wrong_answers, unanswered, percentage, user_answers
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        quiz_id,
        user_id,
        score,
        total_questions,
        correct_answers,
        wrong_answers,
        unanswered_count,
        percentage,
        json.dumps(user_answers)
    ))
    attempt_id = cursor.lastrowid

    # Store individual answers in answers table
    for ans in evaluated_answers:
        cursor.execute("""
            INSERT INTO answers (attempt_id, question_id, selected_answer, is_correct)
            VALUES (?, ?, ?, ?)
        """, (
            attempt_id,
            ans["question_id"],
            ans["selected_answer"],
            ans["is_correct"]
        ))

    db.commit()

    return jsonify({
        "success": True,
        "attempt_id": attempt_id,
        "redirect_url": url_for("attempt_result", attempt_id=attempt_id)
    })


@app.route("/attempt/<int:attempt_id>/result")
@login_required
def attempt_result(attempt_id):
    """Display final quiz score, metrics, and detailed answers breakdown for an attempt."""
    db = get_db()
    user_id = session["user_id"]

    # Secure query: ensure attempt belongs to logged-in user
    attempt = db.execute("""
        SELECT qa.*, q.title as quiz_title, q.difficulty 
        FROM quiz_attempts qa
        JOIN quizzes q ON qa.quiz_id = q.id
        WHERE qa.id = ? AND qa.user_id = ?
    """, (attempt_id, user_id)).fetchone()

    if not attempt:
        flash("Attempt record not found or unauthorized.", "danger")
        return redirect(url_for("history"))

    # Fetch individual submitted answers joined with questions
    answers_data = db.execute("""
        SELECT a.selected_answer, a.is_correct,
               q.id as question_id, q.question, q.question_type, q.options, 
               q.correct_answer, q.explanation
        FROM answers a
        JOIN questions q ON a.question_id = q.id
        WHERE a.attempt_id = ?
        ORDER BY q.id ASC
    """, (attempt_id,)).fetchall()

    results_detail = []
    for item in answers_data:
        results_detail.append({
            "id": item["question_id"],
            "question": item["question"],
            "question_type": item["question_type"],
            "options": json.loads(item["options"]),
            "selected_answer": item["selected_answer"] or "",
            "correct_answer": item["correct_answer"],
            "is_correct": bool(item["is_correct"]),
            "explanation": item["explanation"]
        })

    result_data = {
        "attempt_id": attempt["id"],
        "quiz_id": attempt["quiz_id"],
        "quiz_title": attempt["quiz_title"],
        "difficulty": attempt["difficulty"],
        "total_questions": attempt["total_questions"],
        "correct_answers": attempt["correct_answers"],
        "wrong_answers": attempt["wrong_answers"],
        "unanswered": attempt["unanswered"],
        "score": attempt["score"],
        "percentage": attempt["percentage"],
        "results_detail": results_detail
    }

    return render_template("result.html", result=result_data)


@app.route("/quiz/<int:quiz_id>/result")
@login_required
def quiz_result(quiz_id):
    """Redirect to the latest attempt result for this quiz."""
    db = get_db()
    user_id = session["user_id"]

    latest = db.execute("""
        SELECT id FROM quiz_attempts
        WHERE quiz_id = ? AND user_id = ?
        ORDER BY id DESC LIMIT 1
    """, (quiz_id, user_id)).fetchone()

    if latest:
        return redirect(url_for("attempt_result", attempt_id=latest["id"]))

    flash("No attempts found for this quiz.", "warning")
    return redirect(url_for("attempt_quiz", quiz_id=quiz_id))


# ---------------------------------------------------------
# QUIZ HISTORY & MANAGEMENT
# ---------------------------------------------------------

@app.route("/history")
@login_required
def history():
    """Display all saved quizzes and past attempts."""
    db = get_db()
    user_id = session["user_id"]

    quizzes = db.execute("""
        SELECT 
            q.id, 
            q.title, 
            q.difficulty, 
            q.created_at,
            COUNT(DISTINCT k.id) AS question_count,
            COUNT(DISTINCT a.id) AS total_attempts,
            MAX(a.score) AS best_score,
            MAX(a.percentage) AS best_percentage
        FROM quizzes q
        LEFT JOIN questions k ON q.id = k.quiz_id
        LEFT JOIN quiz_attempts a ON q.id = a.quiz_id AND a.user_id = q.user_id
        WHERE q.user_id = ?
        GROUP BY q.id
        ORDER BY q.created_at DESC
    """, (user_id,)).fetchall()

    return render_template("history.html", quizzes=quizzes)


@app.route("/quiz/<int:quiz_id>/delete", methods=["POST"])
@login_required
def delete_quiz(quiz_id):
    """Delete a saved quiz and its questions/attempts."""
    db = get_db()
    user_id = session["user_id"]

    quiz = db.execute(
        "SELECT id FROM quizzes WHERE id = ? AND user_id = ?",
        (quiz_id, user_id)
    ).fetchone()

    if not quiz:
        flash("Quiz not found or unauthorized.", "danger")
        return redirect(url_for("history"))

    try:
        db.execute("DELETE FROM answers WHERE attempt_id IN (SELECT id FROM quiz_attempts WHERE quiz_id = ?)", (quiz_id,))
        db.execute("DELETE FROM questions WHERE quiz_id = ?", (quiz_id,))
        db.execute("DELETE FROM quiz_attempts WHERE quiz_id = ?", (quiz_id,))
        db.execute("DELETE FROM quizzes WHERE id = ? AND user_id = ?", (quiz_id, user_id))
        db.commit()
        flash("Quiz deleted successfully.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Failed to delete quiz: {str(e)}", "danger")

    return redirect(url_for("history"))


# ---------------------------------------------------------
# INITIALIZATION & RUNNER
# ---------------------------------------------------------

if __name__ == "__main__":
    init_db()
    print("AI Quiz Generator server starting on http://127.0.0.1:5000 ...")
    app.run(debug=True, host="127.0.0.1", port=5000)

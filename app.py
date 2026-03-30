"""Algebrify Flask app: routes for auth, practice, hints, and history.
"""

from flask import Flask, render_template, request, redirect, session, jsonify
import os
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from helper import generate_problem_by_type, check_answer, analyze_incorrect_answer, personalize_review
from cs50 import SQL

db = SQL("sqlite:///data/algebrify.db")

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# In-memory convenience users (hashed) for quick local testing
users = {
    'testuser': generate_password_hash('password'),
    'testuser2': generate_password_hash('password2'),
}

# Ensure those test users exist in the DB so login queries succeed
try:
    for uname, phash in users.items():
        rows = db.execute("SELECT * FROM users WHERE username = ?", uname)
        if len(rows) == 0:
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", uname, phash)
except Exception:
    # If DB not initialized yet or table missing, skip gracefully here.
    pass


# Home page
@app.route('/')
def index():
    return render_template('index.html')


# Login form + session
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            return "Username and password are required", 401

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(rows) != 1:
            return "Invalid username", 401

        if not check_password_hash(rows[0]["hash"], password):
            return "Invalid password", 401

        # Log in
        session["user_id"] = username
        return redirect('/practice')
    return render_template('login.html')


# Register a new user
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirmation = request.form.get('confirmation')

        if not username or not password or not confirmation:
            return "All fields are required", 400
        if password != confirmation:
            return "Passwords do not match", 400

        # check if user exists
        existing = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(existing) > 0:
            return "Username already exists", 400

        pw_hash = generate_password_hash(password)
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, pw_hash)

        # Log in
        session["user_id"] = username
        return redirect('/practice')
    return render_template('register.html')


@app.route('/logout')
def logout():
    """Log the user out and redirect to login."""
    session.clear()
    return redirect('/login')


# Practice: choose type, get hints, submit answers
@app.route('/practice', methods=['GET', 'POST'])
def practice():
    if "user_id" not in session:
        return redirect('/login')

    user_id = session["user_id"]
    types = db.execute("SELECT * FROM problem_types ORDER BY unit, type ASC")

    selected_type = None
    unit = None
    result = None
    guidance = None

    if types:
        selected_type = types[0]['type']
        unit = types[0]['unit']

    if request.method == 'POST':
        selected_type = request.form.get('problem_type') or selected_type
        unit = request.form.get('unit') or unit

        question_post = request.form.get('question')
        # NOTE: template uses name="user_answer_field" to avoid autofill — read that field here
        user_answer = (request.form.get('user_answer_field') or '').strip()
        correct_answer_raw = request.form.get('correct_answer')

        correct_answer_parsed = None
        if correct_answer_raw:
            try:
                if ',' in correct_answer_raw:
                    correct_answer_parsed = [float(x.strip()) for x in correct_answer_raw.split(',')]
                else:
                    correct_answer_parsed = float(correct_answer_raw)
            except Exception:
                correct_answer_parsed = correct_answer_raw

        # If an answer was submitted
        if user_answer and question_post and correct_answer_raw:
            # track attempts for current question in session
            current_q = session.get('current_question')
            if current_q and current_q == question_post:
                session['attempts'] = int(session.get('attempts', 0)) + 1
            else:
                session['attempts'] = 1
                session['current_question'] = question_post
            session.modified = True

            to_check = correct_answer_parsed if isinstance(correct_answer_parsed, list) else correct_answer_raw
            is_correct = check_answer(user_answer, to_check)

            used_hint_form = request.form.get('used_hint_level')
            if used_hint_form is not None:
                try:
                    used_hint_level = int(used_hint_form)
                except Exception:
                    used_hint_level = 0
            else:
                used_hint_level = int(session.pop('hint_shown_level', 0) or 0)

            # reveal after 5 attempts
            reveal_solution = False
            if session.get('attempts', 0) >= 5:
                reveal_solution = True
                used_hint_level = max(used_hint_level or 0, 3)

            used_hint = 1 if used_hint_level and int(used_hint_level) > 0 else 0

            if not is_correct and not reveal_solution:
                guidance = analyze_incorrect_answer(
                    user_answer,
                    correct_answer_parsed if correct_answer_parsed is not None else correct_answer_raw,
                    problem_type=selected_type,
                    question=question_post
                )

            try:
                db.execute(
                    "INSERT INTO history (user_id, unit, question, user_answer, correct_answer, result, used_hint, used_hint_level) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    user_id, unit, question_post, user_answer, correct_answer_raw, int(bool(is_correct)), used_hint, used_hint_level
                )
            except Exception:
                pass

            # If incorrect and not revealing, re-render same question with guidance
            if not is_correct and not reveal_solution:
                result = "❌ Incorrect. Try again!"
                return render_template(
                    'practice.html',
                    types=types,
                    question=question_post,
                    correct_answer=correct_answer_raw,
                    unit=unit,
                    problem_type=selected_type,
                    result=result,
                    guidance=guidance,
                    reveal=False,
                    hint=None,
                    attempts=session.get('attempts', 0)
                )

            # If reveal required, show correct answer AND review text (level 3)
            if reveal_solution:
                result = "❌ Incorrect. The correct answer is shown below (you reached 5 attempts)."
                # ensure attempts reset so we don't immediately reveal again
                session['attempts'] = 0
                session['hint_shown_level'] = max(session.get('hint_shown_level', 0) or 0, used_hint_level)
                session.modified = True

                # The review text should have been stored in session[current_hints]['3'] when problem was generated;
                # but if the session doesn't have it, generate it on the fly using the same generator pattern:
                review_text = ""
                hints = session.get('current_hints', {})
                review_text = hints.get('3') if hints.get('3') else ""

                return render_template(
                    'practice.html',
                    types=types,
                    question=question_post,
                    correct_answer=correct_answer_raw,
                    unit=unit,
                    problem_type=selected_type,
                    result=result,
                    guidance="You've reached 5 attempts — the correct answer and a short review are shown to help.",
                    reveal=True,
                    review=review_text,
                    hint=None,
                    attempts=session.get('attempts', 0)
                )

            # If correct: generate a new problem
            if is_correct:
                result = "✅ Correct!"
                session['attempts'] = 0
                session['hint_shown_level'] = 0

                question, solution, hint1, hint2, hint3 = generate_problem_by_type(selected_type)
                session['current_hints'] = {'1': hint1 or "", '2': hint2 or "", '3': hint3 or ""}
                session['current_question'] = question or ""
                session['current_solution'] = solution  # store raw solution for personalization / hint route
                session['hint_shown_level'] = 0
                session.modified = True

                if isinstance(solution, list):
                    solution_str = ', '.join(str(x) for x in solution)
                else:
                    solution_str = str(solution)

                return render_template(
                    'practice.html',
                    types=types,
                    question=question,
                    correct_answer=solution_str,
                    unit=unit,
                    problem_type=selected_type,
                    result=result,
                    guidance=None,
                    hint=None,
                    attempts=session.get('attempts', 0)
                )

        # POST with no answer (Start Practice): generate problem
        question, solution, hint1, hint2, hint3 = generate_problem_by_type(selected_type)
        session['current_hints'] = {'1': hint1 or "", '2': hint2 or "", '3': hint3 or ""}
        session['current_question'] = question or ""
        session['current_solution'] = solution  # store raw solution for personalization / hint route
        session['hint_shown_level'] = 0
        session['attempts'] = 0
        session.modified = True

        if isinstance(solution, list):
            solution_str = ', '.join(str(x) for x in solution)
        else:
            solution_str = str(solution)

        return render_template(
            'practice.html',
            types=types,
            question=question,
            correct_answer=solution_str,
            unit=unit,
            problem_type=selected_type,
            result=result,
            guidance=None,
            hint=None,
            attempts=session.get('attempts', 0)
        )

    # GET
    return render_template(
        'practice.html',
        question=None,
        correct_answer=None,
        types=types,
        hint=None,
        guidance=None,
        problem_type=selected_type,
        unit=unit,
        attempts=session.get('attempts', 0)
    )

# Lazy-load a hint for the current problem
@app.route('/hint', methods=['GET'])
def hint():
    """
    Return hint JSON for requested level.
    level=1 or 2 are available anytime (if present).
    level=3 (worked review) is only available if session['attempts'] >= 2
      (student tried at least twice) OR if reveal state is active.
    The route also updates session['hint_shown_level'] to the highest level served.
    """
    level = request.args.get('level', '1')
    try:
        level_i = int(level)
    except Exception:
        return jsonify({"ok": False, "error": "invalid level"}), 400

    hints = session.get('current_hints') or {}
    attempts = int(session.get('attempts', 0) or 0)
    reveal_allowed = False

    # If session indicates reveal (attempts >=5) allow level 3 as reveal.
    if attempts >= 5:
        reveal_allowed = True

    # require at least 2 attempts to request a level 3 hint manually
    if level_i == 3 and not reveal_allowed and attempts < 2:
        return jsonify({"ok": False, "error": "level 3 hint is available after at least 2 attempts"},), 403

    hint_text = hints.get(str(level_i), "")
    # For level 3, personalize it using the user's attempt info if available
    if level_i == 3:
        user_answer = request.args.get('user_answer') or request.values.get('user_answer') or session.get('last_user_answer')
        correct_answer = session.get('current_solution') or session.get('current_correct_answer') or session.get('current_correct')
        problem_type = session.get('current_problem_type')
        question = session.get('current_question')
        # If the session doesn't store the raw correct_answer, the generators in practice and /api/problem
        # should store it at session['current_solution'] (string or list). If not, this will be empty.
        personalized = personalize_review(hint_text or "", user_answer, correct_answer, problem_type=problem_type, question=question)
        hint_text = personalized

    # Update highest hint shown level in session
    try:
        current_shown = int(session.get('hint_shown_level', 0) or 0)
    except Exception:
        current_shown = 0
    if level_i > current_shown:
        session['hint_shown_level'] = level_i
        session.modified = True

    # Mark that the student used hint level 3 for history when they request it
    # (Your practice route will also save used_hint_level from the form on submit; this is just a best-effort flag)
    if level_i == 3:
        session['used_hint_level_on_request'] = 3
        session.modified = True

    return jsonify({"ok": True, "level": level_i, "hint": hint_text, "has_next": (level_i < 3 and bool(hints.get('2'))), "attempts": attempts})

# API: list problem types (JSON)
@app.route('/api/problem_types', methods=['GET'])
def api_problem_types():
    """Return available problem types as JSON for client-side UI."""
    try:
        rows = db.execute("SELECT unit, type, description FROM problem_types ORDER BY unit, type ASC")
        return jsonify({"ok": True, "types": rows})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# API: generate a single problem (JSON). Accepts form/query param 'problem_type'.
@app.route('/api/problem', methods=['GET', 'POST'])
def api_problem():
    """
    Return a generated problem as JSON.
    Accepts 'problem_type' via GET query or POST form/body.
    Stores hints in session for subsequent /hint requests.
    """
    problem_type = request.values.get('problem_type') or request.args.get('problem_type')
    if not problem_type:
        return jsonify({"ok": False, "error": "missing problem_type"}), 400

    # Optional: require login
    # if "user_id" not in session:
    #     return jsonify({"ok": False, "error": "authentication required"}), 401

    try:
        generated = generate_problem_by_type(problem_type)
        # Normalize unpacking: support generators that return 3,4 or 5 items
        if len(generated) == 3:
            question, solution, hint1 = generated
            hint2, hint3 = "", ""
        elif len(generated) == 4:
            question, solution, hint1, hint2 = generated
            hint3 = ""
        else:
            question, solution, hint1, hint2, hint3 = generated

        # Save hints and question into session so /hint can serve them lazily
        session['current_hints'] = {'1': hint1 or "", '2': hint2 or "", '3': hint3 or ""}
        session['current_question'] = question or ""
        session['current_solution'] = solution
        session['hint_shown_level'] = 0
        session['attempts'] = 0
        session.modified = True

        # NOTE: returning the solution is convenient for development and tests.
        # Remove 'solution' from the response before deploying to students.
        return jsonify({
            "ok": True,
            "problem_type": problem_type,
            "question": question,
            "solution": solution,
            "hints_available": {"1": bool(hint1), "2": bool(hint2), "3": bool(hint3)}
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# Attempt history (per-user if logged in)
@app.route('/history')
def history():
    """
    History view with filtering and sorting.
    Supported query params:
      - unit: filter by unit string (exact match)
      - result: "1" for correct, "0" for incorrect
      - used_hint_level: integer 0..3
      - start_date, end_date: 'YYYY-MM-DD' filter by timestamp date (inclusive)
      - sort_by: one of id, timestamp, unit, result, used_hint_level
      - sort_dir: asc or desc
    If user is logged in, limits results to that user by default; admins could remove that.
    """
    # Available filter/sort options
    units = [row['unit'] for row in db.execute("SELECT DISTINCT unit FROM problem_types ORDER BY unit")]
    sortables = {'id', 'timestamp', 'unit', 'result', 'used_hint_level'}

    # Read query params
    q_unit = request.args.get('unit', type=str)
    q_result = request.args.get('result', type=str)   # expect "1" or "0"
    q_hint_level = request.args.get('used_hint_level', type=str)  # expect "0","1","2","3"
    q_start = request.args.get('start_date', type=str)  # YYYY-MM-DD
    q_end = request.args.get('end_date', type=str)
    sort_by = request.args.get('sort_by', 'id')
    sort_dir = request.args.get('sort_dir', 'desc').lower()
    page = max(1, request.args.get('page', 1, type=int))
    page_size = 50  # change if you want pagination size

    # Sanitize sort_by and sort_dir
    if sort_by not in sortables:
        sort_by = 'id'
    if sort_dir not in ('asc', 'desc'):
        sort_dir = 'desc'

    # Build where clauses and params
    where_clauses = []
    params = []

    if "user_id" in session:
        where_clauses.append("user_id = ?")
        params.append(session["user_id"])

    if q_unit:
        where_clauses.append("unit = ?")
        params.append(q_unit)

    if q_result in ("0", "1"):
        where_clauses.append("result = ?")
        params.append(int(q_result))

    if q_hint_level is not None and q_hint_level != "":
        # allow searching for multiple values (comma separated) e.g., ?used_hint_level=0,1
        if ',' in q_hint_level:
            vals = [int(x) for x in q_hint_level.split(',') if x.strip().isdigit()]
            if vals:
                placeholders = ','.join('?' for _ in vals)
                where_clauses.append(f"used_hint_level IN ({placeholders})")
                params.extend(vals)
        else:
            try:
                lvl = int(q_hint_level)
                where_clauses.append("used_hint_level = ?")
                params.append(lvl)
            except Exception:
                pass

    # Date filtering: timestamp is assumed to be stored in a format SQLite can compare with YYYY-MM-DD
    # If your timestamp includes time, this still works using >= and <= with the date strings
    if q_start:
        where_clauses.append("DATE(timestamp) >= DATE(?)")
        params.append(q_start)
    if q_end:
        where_clauses.append("DATE(timestamp) <= DATE(?)")
        params.append(q_end)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # Count total for pagination
    count_sql = f"SELECT COUNT(*) AS total FROM history {where_sql}"
    try:
        total_row = db.execute(count_sql, *params)
        total = total_row[0]['total'] if total_row else 0
    except Exception:
        total = 0

    # Pagination calculation
    offset = (page - 1) * page_size

    # Final select with ordering and pagination
    sql = (
        "SELECT id, user_id, unit, question, user_answer, correct_answer, result, "
        "COALESCE(used_hint, 0) AS used_hint, COALESCE(used_hint_level, 0) AS used_hint_level, timestamp "
        f"FROM history {where_sql} "
        f"ORDER BY {sort_by} {sort_dir} "
        f"LIMIT ? OFFSET ?"
    )

    # append pagination params
    final_params = params + [page_size, offset]

    try:
        rows = db.execute(sql, *final_params)
    except Exception:
        rows = []

    # build url params to preserve filters in template links
    def build_query(**overrides):
        args = {
            'unit': q_unit or '',
            'result': q_result or '',
            'used_hint_level': q_hint_level or '',
            'start_date': q_start or '',
            'end_date': q_end or '',
            'sort_by': sort_by,
            'sort_dir': sort_dir,
            'page': page
        }
        args.update(overrides)
        # remove empty values
        return "&".join(f"{k}={v}" for k, v in args.items() if v not in (None, '', []))

    # compute pagination meta
    total_pages = max(1, (total + page_size - 1) // page_size)

    return render_template(
        'history.html',
        rows=rows,
        units=units,
        filters={
            'unit': q_unit,
            'result': q_result,
            'used_hint_level': q_hint_level,
            'start_date': q_start,
            'end_date': q_end
        },
        sort_by=sort_by,
        sort_dir=sort_dir,
        build_query=build_query,
        page=page,
        total=total,
        total_pages=total_pages
    )

# Optional selector page example
@app.route('/select')
def select():
    if "user_id" not in session:
        return redirect('/login')

    # Show all available types (no hard-coded unit filter)
    types = db.execute(
        "SELECT type, description FROM problem_types ORDER BY unit, type ASC"
    )

    return render_template('select.html', types=types)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

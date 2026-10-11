"""ACEest Fitness & Gym - Flask service.

Web/API port of the legacy Tkinter desktop app (see ``legacy/``). Business
logic lives in small pure functions so it can be unit-tested without HTTP.
"""
import os
import random
import sqlite3
from datetime import date, datetime

from flask import Flask, g, jsonify, request

PROGRAMS = {
    "Fat Loss (FL)": {
        "factor": 22,
        "workout": ["Mon: Back Squat 5x5 + Core", "Tue: EMOM 20min Assault Bike",
                    "Wed: Bench Press + 21-15-9", "Thu: Deadlift + Box Jumps",
                    "Fri: Zone 2 Cardio 30min"],
        "diet": ["Breakfast: Egg Whites + Oats", "Lunch: Grilled Chicken + Brown Rice",
                 "Dinner: Fish Curry + Millet Roti", "Target: ~2000 kcal"],
    },
    "Muscle Gain (MG)": {
        "factor": 35,
        "workout": ["Mon: Squat 5x5", "Tue: Bench 5x5", "Wed: Deadlift 4x6",
                    "Thu: Front Squat 4x8", "Fri: Incline Press 4x10",
                    "Sat: Barbell Rows 4x10"],
        "diet": ["Breakfast: Eggs + Peanut Butter Oats", "Lunch: Chicken Biryani",
                 "Dinner: Mutton Curry + Rice", "Target: ~3200 kcal"],
    },
    "Beginner (BG)": {
        "factor": 26,
        "workout": ["Full Body Circuit: Air Squats, Ring Rows, Push-ups",
                    "Focus: Technique & Consistency"],
        "diet": ["Balanced Tamil Meals", "Idli / Dosa / Rice + Dal",
                 "Protein Target: 120g/day"],
    },
}

WORKOUT_TYPES = {"Strength", "Hypertrophy", "Conditioning", "Mixed", "Mobility"}

EXERCISE_POOL = {
    "Strength": ["Squat", "Deadlift", "Bench Press", "Overhead Press", "Pull-Up", "Barbell Row"],
    "Hypertrophy": ["Leg Press", "Incline Dumbbell Press", "Lat Pulldown",
                    "Lateral Raise", "Bicep Curl", "Tricep Extension"],
    "Conditioning": ["Running", "Cycling", "Rowing", "Burpees", "Jump Rope", "Kettlebell Swings"],
    "Full Body": ["Push-Up", "Pull-Up", "Lunge", "Plank", "Dumbbell Row", "Dumbbell Press"],
}

EXPERIENCE = {  # level: (sets range, reps range, days per week)
    "beginner": ((2, 3), (8, 12), 3),
    "intermediate": ((3, 4), (8, 15), 4),
    "advanced": ((4, 5), (6, 15), 5),
}
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    age INTEGER, height REAL, weight REAL,
    program TEXT, calories INTEGER,
    target_weight REAL, target_adherence INTEGER,
    membership_expiry TEXT
);
CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL, week TEXT, adherence INTEGER
);
CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL, date TEXT, workout_type TEXT,
    duration_min INTEGER, notes TEXT
);
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL, date TEXT, weight REAL, waist REAL, bodyfat REAL
);
"""


# ---------- pure business logic ----------
def calculate_calories(weight, program):
    """Estimated daily kcal = weight(kg) x program factor."""
    if program not in PROGRAMS:
        raise ValueError(f"Unknown program: {program}")
    if weight is None or weight <= 0:
        raise ValueError("Weight must be positive")
    return int(weight * PROGRAMS[program]["factor"])


def calculate_bmi(height_cm, weight_kg):
    """Return (bmi, category, risk note)."""
    if not height_cm or not weight_kg or height_cm <= 0 or weight_kg <= 0:
        raise ValueError("Height and weight must be positive")
    bmi = round(weight_kg / ((height_cm / 100.0) ** 2), 1)
    if bmi < 18.5:
        return bmi, "Underweight", "Potential nutrient deficiency, low energy."
    if bmi < 25:
        return bmi, "Normal", "Low risk if active and strong."
    if bmi < 30:
        return bmi, "Overweight", "Moderate risk; focus on adherence and progressive activity."
    return bmi, "Obese", "Higher risk; prioritize fat loss, consistency, and supervision."


def membership_status(expiry, today=None):
    """Return 'Active', 'Expired' or 'Not Set' for an ISO date string."""
    if not expiry:
        return "Not Set"
    today = today or date.today()
    return "Active" if date.fromisoformat(expiry) >= today else "Expired"


def generate_program(program_name, level, rng=random):
    """AI-style weekly plan: list of {day, exercise, sets, reps}."""
    level = (level or "").lower()
    if level not in EXPERIENCE:
        raise ValueError("Experience must be beginner, intermediate or advanced")
    focus = "Full Body"
    if "Fat Loss" in (program_name or ""):
        focus = "Conditioning"
    elif "Muscle Gain" in (program_name or ""):
        focus = "Hypertrophy"
    sets_r, reps_r, days = EXPERIENCE[level]
    plan = []
    for day in WEEKDAYS[:days]:
        for ex in rng.sample(EXERCISE_POOL[focus], k=3 if days < 4 else 4):
            plan.append({"day": day, "exercise": ex,
                         "sets": rng.randint(*sets_r), "reps": rng.randint(*reps_r)})
    return plan


def valid_iso_date(value):
    try:
        date.fromisoformat(value)
        return True
    except (TypeError, ValueError):
        return False


def json_object():
    """Return the request JSON body if it is an object, else None."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate_client_fields(data):
    """Return an error message for invalid client fields, else None."""
    age = data.get("age")
    if age is not None and (not isinstance(age, int) or isinstance(age, bool) or age <= 0):
        return "age must be a positive integer"
    for field in ("height", "weight", "target_weight"):
        v = data.get(field)
        if v is not None and (not _is_number(v) or v <= 0):
            return f"{field} must be a positive number"
    ta = data.get("target_adherence")
    if ta is not None and (not isinstance(ta, int) or isinstance(ta, bool) or not 0 <= ta <= 100):
        return "target_adherence must be an integer between 0 and 100"
    expiry = data.get("membership_expiry")
    if expiry and not valid_iso_date(expiry):
        return "membership_expiry must be YYYY-MM-DD"
    return None


# ---------- app factory ----------
def create_app(test_config=None):
    app = Flask(__name__)
    app.config["DATABASE"] = os.environ.get("ACEEST_DB", "aceest_fitness.db")
    if test_config:
        app.config.update(test_config)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    schema_ready = {"done": False}

    @app.before_request
    def ensure_schema():
        if not schema_ready["done"]:
            db = get_db()
            db.executescript(SCHEMA)
            db.commit()
            schema_ready["done"] = True

    def err(msg, code=400):
        return jsonify({"error": msg}), code

    def find_client(name):
        return get_db().execute("SELECT * FROM clients WHERE name=?", (name,)).fetchone()

    # ----- system / reference data -----
    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "service": "aceest-fitness"})

    @app.get("/")
    def index():
        return jsonify({"name": "ACEest Fitness & Gym API", "programs": "/programs",
                        "clients": "/clients", "health": "/health"})

    @app.get("/programs")
    def list_programs():
        return jsonify({name: {"factor": p["factor"]} for name, p in PROGRAMS.items()})

    @app.get("/programs/<name>")
    def get_program(name):
        if name not in PROGRAMS:
            return err("Program not found", 404)
        return jsonify({"name": name, **PROGRAMS[name]})

    # ----- clients -----
    @app.post("/clients")
    def create_client():
        data = json_object()
        if data is None:
            return err("JSON object body is required")
        name = (data.get("name") or "").strip() if isinstance(data.get("name"), str) else ""
        program = data.get("program")
        if not name:
            return err("Name is required")
        if program not in PROGRAMS:
            return err("Valid program is required")
        problem = validate_client_fields(data)
        if problem:
            return err(problem)
        expiry = data.get("membership_expiry")
        if find_client(name):
            return err("Client already exists", 409)
        weight = data.get("weight")
        calories = calculate_calories(weight, program) if weight else None
        db = get_db()
        db.execute(
            "INSERT INTO clients (name, age, height, weight, program, calories,"
            " target_weight, target_adherence, membership_expiry) VALUES (?,?,?,?,?,?,?,?,?)",
            (name, data.get("age"), data.get("height"), weight, program, calories,
             data.get("target_weight"), data.get("target_adherence"), expiry))
        db.commit()
        return jsonify(dict(find_client(name))), 201

    @app.get("/clients")
    def list_clients():
        rows = get_db().execute("SELECT * FROM clients ORDER BY name").fetchall()
        return jsonify([dict(r) for r in rows])

    @app.get("/clients/<name>")
    def get_client(name):
        row = find_client(name)
        return (jsonify(dict(row)), 200) if row else err("Client not found", 404)

    @app.put("/clients/<name>")
    def update_client(name):
        row = find_client(name)
        if not row:
            return err("Client not found", 404)
        data = json_object()
        if data is None:
            return err("JSON object body is required")
        changes = {k: v for k, v in data.items() if k != "name"}
        problem = validate_client_fields(changes)
        if problem:
            return err(problem)
        merged = {**dict(row), **changes}
        if merged["program"] not in PROGRAMS:
            return err("Valid program is required")
        calories = calculate_calories(merged["weight"], merged["program"]) if merged["weight"] else None
        db = get_db()
        db.execute(
            "UPDATE clients SET age=?, height=?, weight=?, program=?, calories=?,"
            " target_weight=?, target_adherence=?, membership_expiry=? WHERE name=?",
            (merged["age"], merged["height"], merged["weight"], merged["program"], calories,
             merged["target_weight"], merged["target_adherence"], merged["membership_expiry"], name))
        db.commit()
        return jsonify(dict(find_client(name)))

    @app.delete("/clients/<name>")
    def delete_client(name):
        if not find_client(name):
            return err("Client not found", 404)
        db = get_db()
        for table in ("progress", "workouts", "metrics"):
            db.execute(f"DELETE FROM {table} WHERE client_name=?", (name,))  # nosec - fixed names
        db.execute("DELETE FROM clients WHERE name=?", (name,))
        db.commit()
        return "", 204

    # ----- progress -----
    @app.post("/clients/<name>/progress")
    def add_progress(name):
        if not find_client(name):
            return err("Client not found", 404)
        body = json_object()
        if body is None:
            return err("JSON object body is required")
        adherence = body.get("adherence")
        if not isinstance(adherence, int) or isinstance(adherence, bool) or not 0 <= adherence <= 100:
            return err("adherence must be an integer between 0 and 100")
        week = datetime.now().strftime("Week %U - %Y")
        db = get_db()
        db.execute("INSERT INTO progress (client_name, week, adherence) VALUES (?,?,?)",
                   (name, week, adherence))
        db.commit()
        return jsonify({"client": name, "week": week, "adherence": adherence}), 201

    @app.get("/clients/<name>/progress")
    def get_progress(name):
        if not find_client(name):
            return err("Client not found", 404)
        rows = get_db().execute(
            "SELECT week, adherence FROM progress WHERE client_name=? ORDER BY id", (name,)
        ).fetchall()
        return jsonify([dict(r) for r in rows])

    # ----- workouts -----
    @app.post("/clients/<name>/workouts")
    def add_workout(name):
        if not find_client(name):
            return err("Client not found", 404)
        d = json_object()
        if d is None:
            return err("JSON object body is required")
        w_date = d.get("date") or date.today().isoformat()
        if not valid_iso_date(w_date):
            return err("date must be YYYY-MM-DD")
        if d.get("workout_type") not in WORKOUT_TYPES:
            return err(f"workout_type must be one of {sorted(WORKOUT_TYPES)}")
        dur = d.get("duration_min", 60)
        if not isinstance(dur, int) or isinstance(dur, bool) or dur <= 0:
            return err("duration_min must be a positive integer")
        db = get_db()
        db.execute("INSERT INTO workouts (client_name, date, workout_type, duration_min, notes)"
                   " VALUES (?,?,?,?,?)", (name, w_date, d["workout_type"], dur, d.get("notes", "")))
        db.commit()
        return jsonify({"client": name, "date": w_date, "workout_type": d["workout_type"],
                        "duration_min": dur}), 201

    @app.get("/clients/<name>/workouts")
    def list_workouts(name):
        if not find_client(name):
            return err("Client not found", 404)
        rows = get_db().execute(
            "SELECT date, workout_type, duration_min, notes FROM workouts"
            " WHERE client_name=? ORDER BY date DESC, id DESC", (name,)).fetchall()
        return jsonify([dict(r) for r in rows])

    # ----- body metrics -----
    @app.post("/clients/<name>/metrics")
    def add_metrics(name):
        if not find_client(name):
            return err("Client not found", 404)
        d = json_object()
        if d is None:
            return err("JSON object body is required")
        m_date = d.get("date") or date.today().isoformat()
        if not valid_iso_date(m_date):
            return err("date must be YYYY-MM-DD")
        if not isinstance(d.get("weight"), (int, float)) or d["weight"] <= 0:
            return err("weight must be a positive number")
        db = get_db()
        db.execute("INSERT INTO metrics (client_name, date, weight, waist, bodyfat) VALUES (?,?,?,?,?)",
                   (name, m_date, d["weight"], d.get("waist"), d.get("bodyfat")))
        db.commit()
        return jsonify({"client": name, "date": m_date, "weight": d["weight"]}), 201

    @app.get("/clients/<name>/metrics")
    def list_metrics(name):
        if not find_client(name):
            return err("Client not found", 404)
        rows = get_db().execute(
            "SELECT date, weight, waist, bodyfat FROM metrics WHERE client_name=? ORDER BY date",
            (name,)).fetchall()
        return jsonify([dict(r) for r in rows])

    # ----- analytics -----
    @app.get("/clients/<name>/bmi")
    def client_bmi(name):
        row = find_client(name)
        if not row:
            return err("Client not found", 404)
        try:
            bmi, category, risk = calculate_bmi(row["height"], row["weight"])
        except ValueError as exc:
            return err(str(exc))
        return jsonify({"client": name, "bmi": bmi, "category": category, "risk": risk})

    @app.get("/clients/<name>/membership")
    def client_membership(name):
        row = find_client(name)
        if not row:
            return err("Client not found", 404)
        return jsonify({"client": name, "expiry": row["membership_expiry"],
                        "status": membership_status(row["membership_expiry"])})

    @app.get("/clients/<name>/summary")
    def client_summary(name):
        row = find_client(name)
        if not row:
            return err("Client not found", 404)
        db = get_db()
        weeks, avg = db.execute(
            "SELECT COUNT(*), AVG(adherence) FROM progress WHERE client_name=?", (name,)).fetchone()
        last = db.execute(
            "SELECT date, weight, waist, bodyfat FROM metrics WHERE client_name=?"
            " ORDER BY date DESC LIMIT 1", (name,)).fetchone()
        return jsonify({"profile": dict(row), "weeks_logged": weeks,
                        "average_adherence": round(avg, 1) if avg is not None else 0,
                        "last_metrics": dict(last) if last else None,
                        "membership_status": membership_status(row["membership_expiry"])})

    @app.post("/clients/<name>/generate-program")
    def client_generate_program(name):
        row = find_client(name)
        if not row:
            return err("Client not found", 404)
        body = json_object()
        if body is None:
            return err("JSON object body is required")
        level = body.get("experience")
        try:
            plan = generate_program(row["program"], level)
        except ValueError as exc:
            return err(str(exc))
        return jsonify({"client": name, "program": row["program"], "plan": plan})

    return app


app = create_app()

if __name__ == "__main__":
    # Bind to localhost by default; containers set HOST=0.0.0.0 explicitly.
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 5000)))

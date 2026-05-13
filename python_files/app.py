from flask import Flask, render_template, request, redirect, session, jsonify
from datetime import datetime, timedelta
from pathlib import Path
import os
import uuid
import secrets
import pickle
import re
import requests
import sqlite3
from admin_config import ADMIN_USERNAME, ADMIN_PASSWORD


APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent if APP_DIR.name == "python_files" else APP_DIR
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
STATIC_DIR = PROJECT_ROOT / "static"

DB_PATH = DATA_DIR / "database.db"
MODEL_PATH = MODELS_DIR / "model.pkl"
VECTORIZER_PATH = MODELS_DIR / "vectorizer.pkl"


app = Flask(
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
    static_url_path="/static"
)
app.secret_key = str(uuid.uuid4())  # New key on every run clears old login sessions
app.permanent_session_lifetime = timedelta(minutes=30)

# Load ML model
model = pickle.load(open(MODEL_PATH, 'rb'))
vectorizer = pickle.load(open(VECTORIZER_PATH, 'rb'))

API_KEY = os.getenv("NEWS_API_KEY", "")
accuracy = 0.98

DELETE_WORDS = [
    "violet", "orbit", "signal", "pixel", "silver", "river",
    "bright", "nova", "stone", "echo", "cloud", "spark"
]


def db_connect():
    return sqlite3.connect(DB_PATH)


def get_analyzer_history(username, limit=8):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, news, result, confidence FROM history WHERE username=? ORDER BY id DESC LIMIT ?",
        (username, limit)
    )
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "news": row[1],
            "result": row[2],
            "confidence": round(float(row[3]) * 100, 2)
        }
        for row in rows
    ]


def make_delete_phrase():
    words = secrets.SystemRandom().sample(DELETE_WORDS, 2)
    return " ".join(words)


def fetch_live_articles(keywords):
    if not API_KEY:
        return []

    try:
        response = requests.get(
            "https://newsapi.org/v2/everything",
            params={"q": keywords, "apiKey": API_KEY},
            timeout=5
        )
        data = response.json()
    except (requests.RequestException, ValueError):
        return []

    if data.get("status") != "ok":
        return []

    articles = []
    for article in data.get("articles", [])[:3]:
        articles.append({
            "title": article.get("title", "Untitled"),
            "source": article.get("source", {}).get("name", "Unknown source"),
            "url": article.get("url", "#")
        })

    return articles


def ensure_archive_tables():
    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS deleted_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        old_user_id INTEGER,
        username TEXT,
        password TEXT,
        deleted_by TEXT,
        deleted_at TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS deleted_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        deleted_user_id INTEGER,
        news TEXT,
        result TEXT,
        confidence REAL
    )
    ''')

    conn.commit()
    conn.close()


def archive_and_delete_user(deleted_by, user_id=None, username=None):
    ensure_archive_tables()
    conn = db_connect()
    cursor = conn.cursor()

    if user_id is not None:
        cursor.execute("SELECT id, username, password FROM users WHERE id=?", (user_id,))
    else:
        cursor.execute("SELECT id, username, password FROM users WHERE username=?", (username,))

    user = cursor.fetchone()
    if not user:
        conn.close()
        return False

    cursor.execute(
        "INSERT INTO deleted_users (old_user_id, username, password, deleted_by, deleted_at) VALUES (?, ?, ?, ?, ?)",
        (user[0], user[1], user[2], deleted_by, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    deleted_user_id = cursor.lastrowid

    cursor.execute("SELECT news, result, confidence FROM history WHERE username=?", (user[1],))
    for history_item in cursor.fetchall():
        cursor.execute(
            "INSERT INTO deleted_history (deleted_user_id, news, result, confidence) VALUES (?, ?, ?, ?)",
            (deleted_user_id, history_item[0], history_item[1], history_item[2])
        )

    cursor.execute("DELETE FROM history WHERE username=?", (user[1],))
    cursor.execute("DELETE FROM users WHERE id=?", (user[0],))
    conn.commit()
    conn.close()
    return True


# -------- PREPROCESS --------
def preprocess(text):
    text = re.sub(r'[^a-zA-Z]', ' ', str(text))
    text = text.lower()
    text = ' '.join(text.split())
    return text


# -------- HOME (PROTECTED) --------
@app.route('/')
def home():
    if 'user' not in session:
        return redirect('/login')
    return render_template(
        'index.html',
        username=session['user'],
        history_items=get_analyzer_history(session['user'])
    )


# -------- LOGIN --------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = db_connect()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user'] = username
            return redirect('/')
        else:
            return render_template('login.html', error="Invalid username or password")

    return render_template('login.html')


# -------- ADMIN LOGIN --------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session.clear()
            session['admin'] = username
            return redirect('/admin/dashboard')

        return render_template('admin_login.html', error="Invalid admin username or password")

    return render_template('admin_login.html')


@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect('/admin/login')

    ensure_archive_tables()
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password FROM users ORDER BY id DESC")
    users = cursor.fetchall()
    conn.close()

    return render_template('admin_dashboard.html', users=users, admin=session['admin'])


@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    if 'admin' not in session:
        return redirect('/admin/login')

    archive_and_delete_user(deleted_by=f"admin:{session['admin']}", user_id=user_id)
    return redirect('/admin/dashboard')


@app.route('/admin/past-users')
def admin_past_users():
    if 'admin' not in session:
        return redirect('/admin/login')

    ensure_archive_tables()
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, old_user_id, username, password, deleted_by, deleted_at FROM deleted_users ORDER BY id DESC"
    )
    users = cursor.fetchall()

    past_users = []
    for user in users:
        cursor.execute(
            "SELECT news, result, confidence FROM deleted_history WHERE deleted_user_id=? ORDER BY id DESC",
            (user[0],)
        )
        past_users.append({
            "user": user,
            "history": cursor.fetchall()
        })

    conn.close()
    return render_template('admin_past_users.html', past_users=past_users, admin=session['admin'])


@app.route('/admin/delete-past-user/<int:deleted_user_id>', methods=['POST'])
def admin_delete_past_user(deleted_user_id):
    if 'admin' not in session:
        return redirect('/admin/login')

    ensure_archive_tables()
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM deleted_history WHERE deleted_user_id=?", (deleted_user_id,))
    cursor.execute("DELETE FROM deleted_users WHERE id=?", (deleted_user_id,))
    conn.commit()
    conn.close()

    return redirect('/admin/past-users')


@app.route('/admin/clear-past-users', methods=['POST'])
def admin_clear_past_users():
    if 'admin' not in session:
        return redirect('/admin/login')

    ensure_archive_tables()
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM deleted_history")
    cursor.execute("DELETE FROM deleted_users")
    conn.commit()
    conn.close()

    return redirect('/admin/past-users')


@app.route('/admin/login-as/<username>', methods=['POST'])
def admin_login_as_user(username):
    if 'admin' not in session:
        return redirect('/admin/login')

    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE username=?", (username,))
    user = cursor.fetchone()
    conn.close()

    if user:
        session['user'] = user[0]
        session['admin_impersonating'] = True
        return redirect('/')

    return redirect('/admin/dashboard')


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect('/admin/login')


# -------- REGISTER --------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = db_connect()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE username=?", (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            return render_template('register.html', error="Username already exists")

        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()

        session['user'] = username
        return redirect('/')

    return render_template('register.html')


# -------- LOGOUT --------
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')


# -------- ACCOUNT DELETE --------
@app.route('/account/delete-challenge')
def delete_challenge():
    if 'user' not in session:
        return jsonify({"error": "login_required"}), 401

    phrase = make_delete_phrase()
    session['delete_account_phrase'] = phrase
    return jsonify({"phrase": phrase})


@app.route('/account/delete', methods=['POST'])
def delete_account():
    if 'user' not in session:
        return redirect('/login')

    entered_phrase = request.form.get('delete_phrase', '').strip().lower()
    expected_phrase = session.get('delete_account_phrase', '').strip().lower()

    if not expected_phrase or entered_phrase != expected_phrase:
        return render_template(
            'index.html',
            username=session['user'],
            history_items=get_analyzer_history(session['user']),
            account_delete_error="Verification text did not match."
        )

    archive_and_delete_user(deleted_by="user", username=session['user'])
    session.clear()
    return redirect('/login')


# -------- PREDICT (PROTECTED) --------
@app.route('/predict', methods=['POST'])
def predict():
    if 'user' not in session:
        return redirect('/login')

    news = request.form['news']

    if len(news) < 50:
        return render_template('index.html',
            prediction_text="Please enter a longer news article (at least 2-3 lines) for better analysis",
            username=session['user'],
            history_items=get_analyzer_history(session['user'])
        )

    # ML Prediction
    clean_news = preprocess(news)
    vect = vectorizer.transform([clean_news])

    prediction = model.predict(vect)[0]
    probs = model.predict_proba(vect)[0]
    confidence = probs[prediction]

    # -------- NEWS API (ONLINE OPTIONAL) --------
    keywords = " ".join(clean_news.split()[:8])  # better search
    articles = fetch_live_articles(keywords)

    # -------- DECISION LOGIC --------
    if prediction == 0:
        result = "Real News"
    else:
        if articles:
            result = "Possibly Real (Found in trusted sources)"
        elif confidence < 0.75:
            result = "Suspicious News (Verify)"
        else:
            result = "Fake News"

    # -------- SAVE HISTORY --------
    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO history (username, news, result, confidence) VALUES (?, ?, ?, ?)",
        (session['user'], news, result, float(confidence))
    )

    conn.commit()
    conn.close()

    # -------- GOOGLE FALLBACK --------
    search_url = f"https://www.google.com/search?q={news[:80]}"

    return render_template(
        'index.html',
        prediction_text=result,
        confidence=round(confidence * 100, 2),
        articles=articles,
        search_url=search_url,
        username=session['user'],
        history_items=get_analyzer_history(session['user'])
    )


# -------- DELETE HISTORY --------
@app.route('/history/clear', methods=['POST'])
def clear_history():
    if 'user' not in session:
        return redirect('/login')

    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM history WHERE username=?", (session['user'],))
    conn.commit()
    conn.close()

    return redirect('/')


@app.route('/history/delete/<int:history_id>', methods=['POST'])
def delete_history_item(history_id):
    if 'user' not in session:
        return redirect('/login')

    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM history WHERE id=? AND username=?",
        (history_id, session['user'])
    )
    conn.commit()
    conn.close()

    return redirect('/')


# -------- HISTORY PAGE --------
@app.route('/history')
def history():
    if 'user' not in session:
        return redirect('/login')

    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT news, result, confidence FROM history WHERE username=?",
        (session['user'],)
    )

    data = cursor.fetchall()
    conn.close()

    return render_template('history.html', data=data)


# -------- RUN --------
if __name__ == "__main__":
    app.run(debug=True)

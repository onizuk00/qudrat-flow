import sqlite3
from contextlib import contextmanager
import json
from datetime import datetime

DATABASE_PATH = "qudrat.db"

def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def db_connection():
    conn = get_db()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with db_connection() as conn:
        # Users table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                is_admin BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tests table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                google_form_url TEXT UNIQUE NOT NULL,
                reading_passage TEXT,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Questions table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                options_json TEXT NOT NULL,
                correct_answer_index INTEGER NOT NULL,
                order_index INTEGER NOT NULL,
                FOREIGN KEY (test_id) REFERENCES tests (id) ON DELETE CASCADE
            )
        ''')
        
        # Test sessions table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS test_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                time_limit_seconds INTEGER NOT NULL,
                time_spent_seconds INTEGER,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                score INTEGER,
                total_questions INTEGER,
                correct_count INTEGER,
                completed BOOLEAN DEFAULT 0,
                FOREIGN KEY (test_id) REFERENCES tests (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Answers table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                selected_answer_index INTEGER NOT NULL,
                is_correct BOOLEAN NOT NULL,
                FOREIGN KEY (session_id) REFERENCES test_sessions (id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE
            )
        ''')
        
        # Create indexes
        conn.execute('CREATE INDEX IF NOT EXISTS idx_tests_user_id ON tests(user_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON test_sessions(user_id)')
        print("✅ Database initialized successfully")

def create_user(username, email, hashed_password):
    with db_connection() as conn:
        cursor = conn.execute(
            'INSERT INTO users (username, email, hashed_password) VALUES (?, ?, ?)',
            (username, email, hashed_password)
        )
        return cursor.lastrowid

def get_user_by_username(username):
    with db_connection() as conn:
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        return dict(user) if user else None

def get_user_by_email(email):
    with db_connection() as conn:
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        return dict(user) if user else None

def get_user_by_id(user_id):
    with db_connection() as conn:
        user = conn.execute('SELECT id, username, email, is_admin FROM users WHERE id = ?', (user_id,)).fetchone()
        return dict(user) if user else None

def get_all_tests_for_user(user_id):
    with db_connection() as conn:
        tests = conn.execute('SELECT * FROM tests WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()
        return [dict(row) for row in tests]

def save_test(title, url, reading_passage, questions_data, user_id):
    with db_connection() as conn:
        cursor = conn.execute(
            'INSERT INTO tests (title, google_form_url, reading_passage, user_id) VALUES (?, ?, ?, ?)',
            (title, url, reading_passage, user_id)
        )
        test_id = cursor.lastrowid
        for idx, q in enumerate(questions_data):
            conn.execute(
                'INSERT INTO questions (test_id, question_text, options_json, correct_answer_index, order_index) VALUES (?, ?, ?, ?, ?)',
                (test_id, q['text'], json.dumps(q['options']), q['correct_answer_index'], idx)
            )
        return test_id

def get_test_by_id(test_id):
    with db_connection() as conn:
        test = conn.execute('SELECT * FROM tests WHERE id = ?', (test_id,)).fetchone()
        if not test:
            return None
        questions = conn.execute('SELECT id, question_text, options_json, order_index FROM questions WHERE test_id = ? ORDER BY order_index', (test_id,)).fetchall()
        return {
            'id': test['id'],
            'title': test['title'],
            'reading_passage': test['reading_passage'],
            'questions': [{
                'id': q['id'],
                'text': q['question_text'],
                'options': json.loads(q['options_json']),
                'order_index': q['order_index']
            } for q in questions]
        }

def get_test_answers_key(test_id):
    with db_connection() as conn:
        questions = conn.execute('SELECT id, correct_answer_index FROM questions WHERE test_id = ?', (test_id,)).fetchall()
        return {q['id']: q['correct_answer_index'] for q in questions}

def save_session_results(test_id, time_spent_seconds, answers, time_limit_seconds, user_id):
    with db_connection() as conn:
        total_q = conn.execute('SELECT COUNT(*) as count FROM questions WHERE test_id = ?', (test_id,)).fetchone()['count']
        answer_key = get_test_answers_key(test_id)
        correct_count = 0
        answer_records = []
        for qid, selected_idx in answers.items():
            is_correct = (answer_key.get(int(qid)) == selected_idx)
            if is_correct:
                correct_count += 1
            answer_records.append((int(qid), selected_idx, is_correct))
        score = int((correct_count / total_q) * 100) if total_q > 0 else 0
        cursor = conn.execute('''
            INSERT INTO test_sessions (test_id, user_id, time_limit_seconds, time_spent_seconds, end_time, score, total_questions, correct_count, completed)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, 1)
        ''', (test_id, user_id, time_limit_seconds, time_spent_seconds, score, total_q, correct_count))
        session_id = cursor.lastrowid
        for qid, selected_idx, is_correct in answer_records:
            conn.execute('INSERT INTO answers (session_id, question_id, selected_answer_index, is_correct) VALUES (?, ?, ?, ?)', (session_id, qid, selected_idx, is_correct))
        return {'session_id': session_id, 'score': score, 'correct_count': correct_count, 'total_questions': total_q, 'percentage': score}

def get_test_history_for_user(user_id):
    with db_connection() as conn:
        sessions = conn.execute('''
            SELECT s.*, t.title as test_title FROM test_sessions s JOIN tests t ON s.test_id = t.id WHERE s.user_id = ? AND s.completed = 1 ORDER BY s.start_time DESC
        ''', (user_id,)).fetchall()
        return [dict(row) for row in sessions]

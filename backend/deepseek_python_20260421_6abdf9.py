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
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                google_form_url TEXT UNIQUE NOT NULL,
                reading_passage TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
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
        conn.execute('''
            CREATE TABLE IF NOT EXISTS test_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id INTEGER NOT NULL,
                time_limit_seconds INTEGER NOT NULL,
                time_spent_seconds INTEGER,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                score INTEGER,
                total_questions INTEGER,
                correct_count INTEGER,
                completed BOOLEAN DEFAULT 0,
                FOREIGN KEY (test_id) REFERENCES tests (id) ON DELETE CASCADE
            )
        ''')
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
        conn.execute('CREATE INDEX IF NOT EXISTS idx_questions_test_id ON questions(test_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_test_id ON test_sessions(test_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_answers_session_id ON answers(session_id)')

def save_test(title, url, reading_passage, questions_data):
    with db_connection() as conn:
        cursor = conn.execute(
            'INSERT INTO tests (title, google_form_url, reading_passage) VALUES (?, ?, ?)',
            (title, url, reading_passage)
        )
        test_id = cursor.lastrowid
        for idx, q in enumerate(questions_data):
            conn.execute(
                'INSERT INTO questions (test_id, question_text, options_json, correct_answer_index, order_index) VALUES (?, ?, ?, ?, ?)',
                (test_id, q['text'], json.dumps(q['options']), q['correct_answer_index'], idx)
            )
        return test_id

def get_all_tests():
    with db_connection() as conn:
        tests = conn.execute('''
            SELECT t.*, 
                   (SELECT MAX(start_time) FROM test_sessions WHERE test_id = t.id) as last_taken,
                   (SELECT score FROM test_sessions WHERE test_id = t.id AND completed = 1 ORDER BY start_time DESC LIMIT 1) as last_score,
                   (SELECT correct_count FROM test_sessions WHERE test_id = t.id AND completed = 1 ORDER BY start_time DESC LIMIT 1) as last_correct,
                   (SELECT total_questions FROM test_sessions WHERE test_id = t.id AND completed = 1 ORDER BY start_time DESC LIMIT 1) as last_total
            FROM tests t
            ORDER BY t.created_at DESC
        ''').fetchall()
        return [dict(row) for row in tests]

def get_test_by_id(test_id):
    with db_connection() as conn:
        test = conn.execute('SELECT * FROM tests WHERE id = ?', (test_id,)).fetchone()
        if not test:
            return None
        questions = conn.execute('''
            SELECT id, question_text, options_json, order_index 
            FROM questions 
            WHERE test_id = ? 
            ORDER BY order_index
        ''', (test_id,)).fetchall()
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
        questions = conn.execute('''
            SELECT id, correct_answer_index FROM questions WHERE test_id = ?
        ''', (test_id,)).fetchall()
        return {q['id']: q['correct_answer_index'] for q in questions}

def save_session_results(test_id, time_spent_seconds, answers, time_limit_seconds):
    with db_connection() as conn:
        total_q = conn.execute('SELECT COUNT(*) as count FROM questions WHERE test_id = ?', (test_id,)).fetchone()['count']
        answer_key = get_test_answers_key(test_id)
        correct_count = 0
        answer_records = []
        for question_id, selected_idx in answers.items():
            is_correct = (answer_key.get(int(question_id)) == selected_idx)
            if is_correct:
                correct_count += 1
            answer_records.append((int(question_id), selected_idx, is_correct))
        score = int((correct_count / total_q) * 100) if total_q > 0 else 0
        cursor = conn.execute('''
            INSERT INTO test_sessions 
            (test_id, time_limit_seconds, time_spent_seconds, end_time, score, total_questions, correct_count, completed)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, 1)
        ''', (test_id, time_limit_seconds, time_spent_seconds, score, total_q, correct_count))
        session_id = cursor.lastrowid
        for question_id, selected_idx, is_correct in answer_records:
            conn.execute('''
                INSERT INTO answers (session_id, question_id, selected_answer_index, is_correct)
                VALUES (?, ?, ?, ?)
            ''', (session_id, question_id, selected_idx, is_correct))
        return {
            'session_id': session_id,
            'score': score,
            'correct_count': correct_count,
            'total_questions': total_q,
            'percentage': score
        }

def get_test_history():
    with db_connection() as conn:
        sessions = conn.execute('''
            SELECT s.*, t.title as test_title
            FROM test_sessions s
            JOIN tests t ON s.test_id = t.id
            WHERE s.completed = 1
            ORDER BY s.start_time DESC
        ''').fetchall()
        return [dict(row) for row in sessions]

def get_mistakes_by_test(test_id=None):
    with db_connection() as conn:
        query = '''
            SELECT 
                a.id, a.session_id, a.question_id, a.selected_answer_index,
                q.question_text, q.options_json, q.correct_answer_index,
                t.title as test_title, t.id as test_id,
                s.start_time
            FROM answers a
            JOIN questions q ON a.question_id = q.id
            JOIN test_sessions s ON a.session_id = s.id
            JOIN tests t ON q.test_id = t.id
            WHERE a.is_correct = 0
        '''
        params = []
        if test_id:
            query += " AND t.id = ?"
            params.append(test_id)
        query += " ORDER BY s.start_time DESC"
        mistakes = conn.execute(query, params).fetchall()
        return [dict(row) for row in mistakes]

def get_distinct_wrong_question_ids(test_id):
    with db_connection() as conn:
        rows = conn.execute('''
            SELECT DISTINCT q.id
            FROM answers a
            JOIN questions q ON a.question_id = q.id
            JOIN test_sessions s ON a.session_id = s.id
            WHERE q.test_id = ? AND a.is_correct = 0
        ''', (test_id,)).fetchall()
        return [row['id'] for row in rows]

def get_questions_by_ids(question_ids):
    if not question_ids:
        return []
    with db_connection() as conn:
        placeholders = ','.join('?' for _ in question_ids)
        questions = conn.execute(f'''
            SELECT id, question_text, options_json, correct_answer_index, order_index
            FROM questions
            WHERE id IN ({placeholders})
        ''', question_ids).fetchall()
        return [{
            'id': q['id'],
            'text': q['question_text'],
            'options': json.loads(q['options_json']),
            'correct_answer_index': q['correct_answer_index']
        } for q in questions]
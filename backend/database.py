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
        # Users table (NEW)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                is_admin BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tests table (with user_id)
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
        
        # Test sessions table (with user_id)
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
        
        # Admin logs table (NEW)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                target_type TEXT,
                target_id INTEGER,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (admin_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Create indexes
        conn.execute('CREATE INDEX IF NOT EXISTS idx_questions_test_id ON questions(test_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_test_id ON test_sessions(test_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON test_sessions(user_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_answers_session_id ON answers(session_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_tests_user_id ON tests(user_id)')

# ========== USER FUNCTIONS ==========

def create_user(username: str, email: str, hashed_password: str):
    with db_connection() as conn:
        cursor = conn.execute(
            'INSERT INTO users (username, email, hashed_password) VALUES (?, ?, ?)',
            (username, email, hashed_password)
        )
        return cursor.lastrowid

def get_user_by_username(username: str):
    with db_connection() as conn:
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        return dict(user) if user else None

def get_user_by_email(email: str):
    with db_connection() as conn:
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        return dict(user) if user else None

def get_user_by_id(user_id: int):
    with db_connection() as conn:
        user = conn.execute('SELECT id, username, email, is_admin, created_at FROM users WHERE id = ?', (user_id,)).fetchone()
        return dict(user) if user else None

def get_all_users_for_admin():
    with db_connection() as conn:
        users = conn.execute('SELECT id, username, email, is_admin, created_at FROM users ORDER BY created_at DESC').fetchall()
        return [dict(row) for row in users]

# ========== ADMIN FUNCTIONS ==========

def promote_to_admin(user_id: int, admin_id: int):
    with db_connection() as conn:
        conn.execute('UPDATE users SET is_admin = 1 WHERE id = ?', (user_id,))
        conn.execute(
            'INSERT INTO admin_logs (admin_id, action, target_type, target_id, details) VALUES (?, ?, ?, ?, ?)',
            (admin_id, 'PROMOTE_TO_ADMIN', 'user', user_id, f'User {user_id} promoted to admin')
        )

def demote_from_admin(user_id: int, admin_id: int):
    with db_connection() as conn:
        conn.execute('UPDATE users SET is_admin = 0 WHERE id = ?', (user_id,))
        conn.execute(
            'INSERT INTO admin_logs (admin_id, action, target_type, target_id, details) VALUES (?, ?, ?, ?, ?)',
            (admin_id, 'DEMOTE_FROM_ADMIN', 'user', user_id, f'User {user_id} demoted from admin')
        )

def delete_user_by_admin(user_id: int, admin_id: int):
    with db_connection() as conn:
        # Delete user's answers, sessions, tests, then user
        conn.execute('DELETE FROM answers WHERE session_id IN (SELECT id FROM test_sessions WHERE user_id = ?)', (user_id,))
        conn.execute('DELETE FROM test_sessions WHERE user_id = ?', (user_id,))
        conn.execute('DELETE FROM questions WHERE test_id IN (SELECT id FROM tests WHERE user_id = ?)', (user_id,))
        conn.execute('DELETE FROM tests WHERE user_id = ?', (user_id,))
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.execute(
            'INSERT INTO admin_logs (admin_id, action, target_type, target_id, details) VALUES (?, ?, ?, ?, ?)',
            (admin_id, 'DELETE_USER', 'user', user_id, f'User {user_id} deleted')
        )

def delete_test_by_admin(test_id: int, admin_id: int):
    with db_connection() as conn:
        conn.execute('DELETE FROM answers WHERE session_id IN (SELECT id FROM test_sessions WHERE test_id = ?)', (test_id,))
        conn.execute('DELETE FROM test_sessions WHERE test_id = ?', (test_id,))
        conn.execute('DELETE FROM questions WHERE test_id = ?', (test_id,))
        conn.execute('DELETE FROM tests WHERE id = ?', (test_id,))
        conn.execute(
            'INSERT INTO admin_logs (admin_id, action, target_type, target_id, details) VALUES (?, ?, ?, ?, ?)',
            (admin_id, 'DELETE_TEST', 'test', test_id, f'Test {test_id} deleted')
        )

def get_all_tests_for_admin():
    with db_connection() as conn:
        tests = conn.execute('''
            SELECT t.*, u.username as owner_name 
            FROM tests t
            LEFT JOIN users u ON t.user_id = u.id
            ORDER BY t.created_at DESC
        ''').fetchall()
        return [dict(row) for row in tests]

def get_all_sessions_for_admin():
    with db_connection() as conn:
        sessions = conn.execute('''
            SELECT s.*, t.title as test_title, u.username as user_name
            FROM test_sessions s
            JOIN tests t ON s.test_id = t.id
            JOIN users u ON s.user_id = u.id
            ORDER BY s.start_time DESC
            LIMIT 100
        ''').fetchall()
        return [dict(row) for row in sessions]

def get_admin_logs(admin_id: int = None, limit: int = 50):
    with db_connection() as conn:
        if admin_id:
            logs = conn.execute('''
                SELECT l.*, u.username as admin_name
                FROM admin_logs l
                JOIN users u ON l.admin_id = u.id
                WHERE l.admin_id = ?
                ORDER BY l.created_at DESC
                LIMIT ?
            ''', (admin_id, limit)).fetchall()
        else:
            logs = conn.execute('''
                SELECT l.*, u.username as admin_name
                FROM admin_logs l
                JOIN users u ON l.admin_id = u.id
                ORDER BY l.created_at DESC
                LIMIT ?
            ''', (limit,)).fetchall()
        return [dict(row) for row in logs]

def get_admin_stats():
    with db_connection() as conn:
        total_users = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
        total_admins = conn.execute('SELECT COUNT(*) as count FROM users WHERE is_admin = 1').fetchone()['count']
        total_tests = conn.execute('SELECT COUNT(*) as count FROM tests').fetchone()['count']
        total_sessions = conn.execute('SELECT COUNT(*) as count FROM test_sessions WHERE completed = 1').fetchone()['count']
        avg_score = conn.execute('SELECT AVG(score) as avg FROM test_sessions WHERE completed = 1').fetchone()['avg'] or 0
        return {
            "total_users": total_users,
            "total_admins": total_admins,
            "total_tests": total_tests,
            "total_sessions": total_sessions,
            "avg_score": round(avg_score, 2)
        }

# ========== TEST FUNCTIONS (with user_id) ==========

def save_test(title, url, reading_passage, questions_data, user_id):
    """Save extracted test to database for a specific user"""
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

def get_all_tests_for_user(user_id):
    """Get all tests belonging to a user with latest session info"""
    with db_connection() as conn:
        tests = conn.execute('''
            SELECT t.*, 
                   (SELECT MAX(start_time) FROM test_sessions WHERE test_id = t.id AND user_id = ?) as last_taken,
                   (SELECT score FROM test_sessions WHERE test_id = t.id AND user_id = ? AND completed = 1 ORDER BY start_time DESC LIMIT 1) as last_score,
                   (SELECT correct_count FROM test_sessions WHERE test_id = t.id AND user_id = ? AND completed = 1 ORDER BY start_time DESC LIMIT 1) as last_correct,
                   (SELECT total_questions FROM test_sessions WHERE test_id = t.id AND user_id = ? AND completed = 1 ORDER BY start_time DESC LIMIT 1) as last_total
            FROM tests t
            WHERE t.user_id = ?
            ORDER BY t.created_at DESC
        ''', (user_id, user_id, user_id, user_id, user_id)).fetchall()
        return [dict(row) for row in tests]

def get_test_by_id(test_id):
    """Get test details including all questions (without exposing answers) - no user check needed for viewing"""
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
    """Get correct answers for scoring"""
    with db_connection() as conn:
        questions = conn.execute('''
            SELECT id, correct_answer_index FROM questions WHERE test_id = ?
        ''', (test_id,)).fetchall()
        return {q['id']: q['correct_answer_index'] for q in questions}

def save_session_results(test_id, time_spent_seconds, answers, time_limit_seconds, user_id):
    """Save test session results and return score data for a specific user"""
    with db_connection() as conn:
        # Get total questions count
        total_q = conn.execute('SELECT COUNT(*) as count FROM questions WHERE test_id = ?', (test_id,)).fetchone()['count']
        
        # Get answer key
        answer_key = get_test_answers_key(test_id)
        
        # Calculate score
        correct_count = 0
        answer_records = []
        for question_id, selected_idx in answers.items():
            is_correct = (answer_key.get(int(question_id)) == selected_idx)
            if is_correct:
                correct_count += 1
            answer_records.append((int(question_id), selected_idx, is_correct))
        
        score = int((correct_count / total_q) * 100) if total_q > 0 else 0
        
        # Insert session with user_id
        cursor = conn.execute('''
            INSERT INTO test_sessions 
            (test_id, user_id, time_limit_seconds, time_spent_seconds, end_time, score, total_questions, correct_count, completed)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, 1)
        ''', (test_id, user_id, time_limit_seconds, time_spent_seconds, score, total_q, correct_count))
        session_id = cursor.lastrowid
        
        # Insert answers
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

def get_test_history_for_user(user_id):
    """Get all test sessions history for a specific user"""
    with db_connection() as conn:
        sessions = conn.execute('''
            SELECT s.*, t.title as test_title
            FROM test_sessions s
            JOIN tests t ON s.test_id = t.id
            WHERE s.completed = 1 AND s.user_id = ?
            ORDER BY s.start_time DESC
        ''', (user_id,)).fetchall()
        return [dict(row) for row in sessions]

def get_mistakes_by_test_for_user(test_id, user_id):
    """Get all mistakes for a specific test and user"""
    with db_connection() as conn:
        mistakes = conn.execute('''
            SELECT 
                a.id, a.session_id, a.question_id, a.selected_answer_index,
                q.question_text, q.options_json, q.correct_answer_index,
                t.title as test_title, t.id as test_id,
                s.start_time
            FROM answers a
            JOIN questions q ON a.question_id = q.id
            JOIN test_sessions s ON a.session_id = s.id
            JOIN tests t ON q.test_id = t.id
            WHERE a.is_correct = 0 AND t.id = ? AND s.user_id = ?
            ORDER BY s.start_time DESC
        ''', (test_id, user_id)).fetchall()
        return [dict(row) for row in mistakes]

def get_distinct_wrong_question_ids_for_user(test_id, user_id):
    """Get unique question IDs that were answered incorrectly by a user across all sessions of a test"""
    with db_connection() as conn:
        rows = conn.execute('''
            SELECT DISTINCT q.id
            FROM answers a
            JOIN questions q ON a.question_id = q.id
            JOIN test_sessions s ON a.session_id = s.id
            WHERE q.test_id = ? AND a.is_correct = 0 AND s.user_id = ?
        ''', (test_id, user_id)).fetchall()
        return [row['id'] for row in rows]

# For backward compatibility (admin use, or no-user fallback)
def get_all_tests():
    with db_connection() as conn:
        tests = conn.execute('SELECT * FROM tests ORDER BY created_at DESC').fetchall()
        return [dict(row) for row in tests]

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

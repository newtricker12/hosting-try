import sqlite3
import os
import hashlib
from datetime import datetime

DB_PATH = "users.db"

# ==================== DATABASE CONNECTION ====================
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # User config table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_config (
            user_id INTEGER PRIMARY KEY,
            chat_id TEXT DEFAULT '',
            name_prefix TEXT DEFAULT '',
            delay INTEGER DEFAULT 5,
            cookies TEXT DEFAULT '',
            messages TEXT DEFAULT '',
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # Automation state table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS automation_state (
            user_id INTEGER PRIMARY KEY,
            is_running BOOLEAN DEFAULT 0,
            last_started TIMESTAMP,
            messages_sent INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # Admin chat IDs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_chat_ids (
            user_id INTEGER PRIMARY KEY,
            admin_thread_id TEXT,
            chat_type TEXT DEFAULT 'REGULAR',
            cookies TEXT DEFAULT '',
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

# ==================== USER FUNCTIONS ====================
def create_user(username, password):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return False, "Username already exists"
        
        password_hash = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash)
        )
        user_id = cursor.lastrowid
        
        cursor.execute(
            "INSERT INTO user_config (user_id) VALUES (?)",
            (user_id,)
        )
        
        cursor.execute(
            "INSERT INTO automation_state (user_id) VALUES (?)",
            (user_id,)
        )
        
        conn.commit()
        return True, "User created successfully"
        
    except sqlite3.Error as e:
        return False, f"Database error: {str(e)}"
    finally:
        if conn:
            conn.close()

def verify_user(username, password):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        password_hash = hash_password(password)
        cursor.execute(
            "SELECT id FROM users WHERE username = ? AND password_hash = ?",
            (username, password_hash)
        )
        
        result = cursor.fetchone()
        return result['id'] if result else None
        
    except sqlite3.Error:
        return None
    finally:
        if conn:
            conn.close()

def get_username(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        return result['username'] if result else None
        
    except sqlite3.Error:
        return None
    finally:
        if conn:
            conn.close()

# ==================== CONFIG FUNCTIONS ====================
def get_user_config(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT chat_id, name_prefix, delay, cookies, messages 
            FROM user_config 
            WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        
        if result:
            return {
                'chat_id': result['chat_id'] or '',
                'name_prefix': result['name_prefix'] or '',
                'delay': result['delay'] or 5,
                'cookies': result['cookies'] or '',
                'messages': result['messages'] or 'Hello!'
            }
        else:
            cursor.execute(
                "INSERT INTO user_config (user_id) VALUES (?)",
                (user_id,)
            )
            conn.commit()
            return {
                'chat_id': '',
                'name_prefix': '',
                'delay': 5,
                'cookies': '',
                'messages': 'Hello!'
            }
            
    except sqlite3.Error:
        return {
            'chat_id': '',
            'name_prefix': '',
            'delay': 5,
            'cookies': '',
            'messages': 'Hello!'
        }
    finally:
        if conn:
            conn.close()

def update_user_config(user_id, chat_id, name_prefix, delay, cookies, messages):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM user_config WHERE user_id = ?", (user_id,))
        if cursor.fetchone():
            cursor.execute('''
                UPDATE user_config 
                SET chat_id = ?, name_prefix = ?, delay = ?, cookies = ?, messages = ?
                WHERE user_id = ?
            ''', (chat_id, name_prefix, delay, cookies, messages, user_id))
        else:
            cursor.execute('''
                INSERT INTO user_config (user_id, chat_id, name_prefix, delay, cookies, messages)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, chat_id, name_prefix, delay, cookies, messages))
        
        conn.commit()
        return True
        
    except sqlite3.Error:
        return False
    finally:
        if conn:
            conn.close()

# ==================== AUTOMATION FUNCTIONS ====================
def set_automation_running(user_id, is_running):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if is_running:
            cursor.execute('''
                UPDATE automation_state 
                SET is_running = 1, last_started = ?, messages_sent = 0
                WHERE user_id = ?
            ''', (current_time, user_id))
        else:
            cursor.execute('''
                UPDATE automation_state 
                SET is_running = 0
                WHERE user_id = ?
            ''', (user_id,))
        
        conn.commit()
        return True
        
    except sqlite3.Error:
        return False
    finally:
        if conn:
            conn.close()

def get_automation_state(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT is_running, last_started, messages_sent 
            FROM automation_state 
            WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        if result:
            return {
                'is_running': bool(result['is_running']),
                'last_started': result['last_started'],
                'messages_sent': result['messages_sent'] or 0
            }
        else:
            return {
                'is_running': False,
                'last_started': None,
                'messages_sent': 0
            }
            
    except sqlite3.Error:
        return {
            'is_running': False,
            'last_started': None,
            'messages_sent': 0
        }
    finally:
        if conn:
            conn.close()

# ==================== ADMIN CHAT ID FUNCTIONS ====================
def get_admin_e2ee_thread_id(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT admin_thread_id FROM admin_chat_ids WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        return result['admin_thread_id'] if result else None
        
    except sqlite3.Error:
        return None
    finally:
        if conn:
            conn.close()

def set_admin_e2ee_thread_id(user_id, thread_id, cookies, chat_type='REGULAR'):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("SELECT 1 FROM admin_chat_ids WHERE user_id = ?", (user_id,))
        if cursor.fetchone():
            cursor.execute('''
                UPDATE admin_chat_ids 
                SET admin_thread_id = ?, cookies = ?, chat_type = ?, last_updated = ?
                WHERE user_id = ?
            ''', (thread_id, cookies, chat_type, current_time, user_id))
        else:
            cursor.execute('''
                INSERT INTO admin_chat_ids (user_id, admin_thread_id, cookies, chat_type, last_updated)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, thread_id, cookies, chat_type, current_time))
        
        conn.commit()
        return True
        
    except sqlite3.Error as e:
        return False
    finally:
        if conn:
            conn.close()

# ==================== INITIALIZE DATABASE ====================
if not os.path.exists(DB_PATH):
    init_db()
    print(f"Database created: {DB_PATH}")
else:
    print(f"Database already exists: {DB_PATH}")
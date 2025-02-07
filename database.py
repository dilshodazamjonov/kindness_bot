import sqlite3
from kindness_acts import kindness_acts
from datetime import datetime, timedelta
import pytz




def get_local_timestamp():
    utc_now = datetime.now(pytz.utc)
    uzbekistan_tz = pytz.timezone('Asia/Tashkent')
    local_time = utc_now.astimezone(uzbekistan_tz)
    return local_time.strftime('%Y-%m-%d %H:%M:%S')

def create_table_users():
    database = sqlite3.connect('kindness_bot.db')
    cursor = database.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            full_name TEXT,
            username TEXT,
            kindness_count INTEGER DEFAULT 0,
            highest_streak INTEGER DEFAULT 0,
            current_streak INTEGER DEFAULT 0,
            joined_at TIMESTAMP
        )
    ''')
    database.commit()
    database.close()
create_table_users()


def update_user_streak_automatically():
    database = sqlite3.connect('kindness_bot.db')
    cursor = database.cursor()
    cursor.execute('''
        SELECT u.user_id, k.started_at, k.completed
        FROM users u
        LEFT JOIN user_kindness k ON u.user_id = k.user_id
        WHERE k.completed = TRUE
    ''')
    user_data = cursor.fetchall()

    for user in user_data:
        user_id, started_at, completed = user

        if started_at:
            current_date = datetime.now()
            last_completed_date = datetime.strptime(started_at, "%Y-%m-%d %H:%M:%S")
            if (current_date - last_completed_date).days == 1:  # Consecutive days
                kindness_completed = True
            else:
                kindness_completed = False
            update_user_streak(user_id, kindness_completed)

    database.close()


def update_user_streak(user_id, kindness_completed):
    database = sqlite3.connect('kindness_bot.db')
    cursor = database.cursor()

    cursor.execute("SELECT current_streak, highest_streak FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()

    if user_data:
        current_streak, highest_streak = user_data
        if kindness_completed:
            current_streak += 1
            if current_streak > highest_streak:
                highest_streak = current_streak
        else:
            current_streak = 0
        cursor.execute('''
            UPDATE users
            SET current_streak = ?, highest_streak = ?
            WHERE user_id = ?
        ''', (current_streak, highest_streak, user_id))

        database.commit()
    else:
        print(f"User with ID {user_id} not found.")

    database.close()


def select_user_from_db(chat_id):
    database = sqlite3.connect('kindness_bot.db')
    cursor = database.cursor()
    cursor.execute('''
        SELECT * FROM users WHERE user_id = ?
    ''', (chat_id,))
    user = cursor.fetchone()
    database.close()
    return user

def add_new_user(username, chat_id, full_name):
    database = sqlite3.connect('kindness_bot.db')
    cursor = database.cursor()
    local_timestamp = get_local_timestamp()
    cursor.execute('''
        INSERT INTO users (user_id, username, full_name, joined_at) VALUES(?, ?, ?, ?)
    ''', (chat_id, username, full_name, local_timestamp))
    database.commit()
    database.close()


def create_table_kindness():
    database = sqlite3.connect('kindness_bot.db')
    cursor = database.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kindnesses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kindness_text TEXT UNIQUE NOT NULL
        )
    ''')

    database.commit()
    database.close()

create_table_kindness()

def insert_kindness(kindness_text):
    database = sqlite3.connect('kindness_bot.db')
    cursor = database.cursor()

    try:
        cursor.execute('''
            INSERT INTO kindnesses (kindness_text) 
            VALUES (?)
        ''', (kindness_text,))
        database.commit()
        print(f"✅ Added: {kindness_text}")
    except sqlite3.IntegrityError:
        print(f"⚠️ Skipped (duplicate): {kindness_text}")

    database.close()


def fetch_kindness_text_by_id(kindness_id):
    database = sqlite3.connect('kindness_bot.db')
    cursor = database.cursor()

    cursor.execute('''
        SELECT kindness_text FROM kindnesses WHERE id = ?
    ''', (kindness_id,))

    result = cursor.fetchone()
    database.close()

    return result[0] if result else None


def fetch_random_kindness():
    database = sqlite3.connect('kindness_bot.db')
    cursor = database.cursor()

    cursor.execute("SELECT * FROM kindnesses ORDER BY RANDOM() LIMIT 1")
    row = cursor.fetchone()
    database.close()

    return row if row else None

# for act in kindness_acts:
#     insert_kindness(act)


def create_user_kindness_table():
    database = sqlite3.connect('kindness_bot.db')
    cursor = database.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_kindness (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        kindness_id INTEGER REFERENCES kindnesses(id),
        completed BOOLEAN DEFAULT FALSE,
        started_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')
    database.commit()
    database.close()

create_user_kindness_table()


def insert_into_user_kindness_table(user_id, kindness_text):
    database = sqlite3.connect('kindness_bot.db')
    cursor = database.cursor()
    local_time = get_local_timestamp()
    cursor.execute('''
        INSERT INTO user_kindness (user_id, kindness_id, started_at)
        VALUES (?, ?, ?)
    ''', (user_id, kindness_text, local_time))

    database.commit()
    database.close()


def select_uncompleted_kindnesses(user_id):
    database = sqlite3.connect('kindness_bot.db')
    cursor = database.cursor()
    cursor.execute('''
        SELECT * FROM user_kindness WHERE user_id = ? AND completed = 0
    ''', (user_id,))
    res = cursor.fetchall()
    database.close()
    return res

def mark_kindness_as_complete(user_id, kindness_id):
    database = sqlite3.connect('kindness_bot.db')
    cursor = database.cursor()
    query = """
        UPDATE user_kindness
        SET completed = TRUE
        WHERE user_id = ? AND kindness_id = ?;
        """
    cursor.execute(query, (user_id, kindness_id))
    database.commit()
    database.close()

def update_user_kindness_in_db(user_id):
    database = sqlite3.connect('kindness_bot.db')
    cursor = database.cursor()
    cursor.execute("SELECT kindness_count, current_streak, highest_streak FROM users WHERE id = ?", (user_id,))
    data = cursor.fetchone()
    if data is None:
        print(f"User with user_id {user_id} not found.")
        database.close()
        return
    kindness_count, current_streak, highest_streak = data
    kindness_count += 1
    if current_streak == 0:
        current_streak = 1
    else:
        current_streak += 1

    if highest_streak is None or current_streak > highest_streak:
        highest_streak = current_streak

    cursor.execute("""
        UPDATE users
        SET kindness_count = ?, current_streak = ?, highest_streak = ?
        WHERE id = ?;
    """, (kindness_count, current_streak, highest_streak, user_id))
    database.commit()
    database.close()


def delete_kindness(user_id, kindness_id):
    database = sqlite3.connect('kindness_bot.db')
    cursor = database.cursor()
    query = """
        DELETE FROM user_kindness
        WHERE user_id = ? AND kindness_id = ?;
    """
    cursor.execute(query, (user_id, kindness_id))

    database.commit()
    database.close()


def create_table_kindness_user():
    database = sqlite3.connect('kindness_bot.db')
    cursor = database.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kindness_user (
            id INTEGER PRIMARY KEY,
            user_id INTEGER REFERENCES users(user_id) DEFAULT NULL,
            kindness_text TEXT UNIQUE NOT NULL
        )
    ''')

    database.commit()
    database.close()

create_table_kindness_user()

def save_user_kindness(user_id, text):
    database = sqlite3.connect('kindness_bot.db')
    cursor = database.cursor()
    cursor.execute('''
        INSERT INTO kindness_user(kindness_text, user_id) VALUES(?, ?)
    ''',(text, user_id))

    database.commit()
    database.close()

def select_user_kindness(user_id):
    database = sqlite3.connect('kindness_bot.db')
    cursor = database.cursor()
    cursor.execute('''
        SELECT id, kindness_text FROM kindness_user WHERE user_id = ?
    ''', (user_id,))
    data = cursor.fetchall()
    database.close()
    return data

def remove_user_kindness(user_id, kindness_id):
    database = sqlite3.connect('kindness_bot.db')
    cursor = database.cursor()
    cursor.execute('''
        DELETE FROM kindness_user WHERE user_id = ? AND id = ? 
    ''', (user_id, kindness_id))
    database.commit()
    database.close()
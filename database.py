import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT")
        )
        return conn
    except psycopg2.Error as er:
        print("Ошибка соединения с базой данных:", er)
        return None


def init_database():

    conn = get_db_connection()
    if conn is None:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users(
            id SERIAL PRIMARY KEY,
            user_name VARCHAR(120) UNIQUE NOT NULL,
            created_at TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP)
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS common_words(
            id SERIAL PRIMARY KEY,
            russian_word VARCHAR(50) NOT NULL,
            english_word VARCHAR(50) NOT NULL,
            UNIQUE (russian_word, english_word),
            created_at TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP)
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS user_words(
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            russian_word VARCHAR(50) NOT NULL,
            english_word VARCHAR(50) NOT NULL,
            UNIQUE (user_id, russian_word, english_word),
            created_at TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP)
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS learning_stats(
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            word_id INTEGER NOT NULL,
            word_type VARCHAR(50) NOT NULL CHECK (word_type IN ('common', 'personal')),
            UNIQUE (user_id, word_id, word_type),
            correct_answers INTEGER NOT NULL DEFAULT 0,
            total_attempts INTEGER NOT NULL DEFAULT 0,
            last_reviewed TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP)
            """)

            words = [
                ('красный', 'red'),
                ('синий', 'blue'),
                ('я', 'I'),
                ('ты', 'you'),
                ('кошка', 'cat'),
                ('собака', 'dog'),
                ('один', 'one'),
                ('два', 'two'),
                ('хороший', 'good'),
                ('спасибо', 'thank you')
            ]

            cur.executemany("""
                INSERT INTO common_words (russian_word, english_word)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
            """, words)
        conn.commit()
    finally:
        conn.close()


def login_user(user_name):

    conn = get_db_connection()

    if conn is None:
        return None

    try:
        with conn.cursor() as cur:
            query = "SELECT id FROM users WHERE user_name = %s"
            cur.execute(query, (user_name,))
            result = cur.fetchone()

            if result is not None:
                return result[0]

            cur.execute("""
                INSERT INTO users (user_name) VALUES (%s)
                RETURNING id""",
                            (user_name,))
            user_id = cur.fetchone()[0]
            conn.commit()
            return user_id
    finally:
        conn.close()


def get_user_words(user_id):

    conn = get_db_connection()

    if conn is None:
        return None

    try:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT id, russian_word, english_word, 'common' FROM common_words
            UNION ALL
            SELECT id, russian_word, english_word, 'personal' FROM user_words
            WHERE user_id = %s;""", (user_id,))
            words = cur.fetchall()
            return words
    finally:
        conn.close()


def add_personal_word(user_id, russian_word, english_word):

    conn = get_db_connection()

    if conn is None:
        return None

    try:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO user_words (user_id, russian_word, english_word)
            VALUES (%s, %s, %s) ON CONFLICT DO NOTHING
            RETURNING id;""", (user_id, russian_word, english_word))
            result = cur.fetchone()

            if result is None:
                return False

        conn.commit()
        return True
    finally:
        conn.close()


def delete_personal_word(user_id, word_id):

    conn = get_db_connection()

    if conn is None:
        return None

    try:
        with conn.cursor() as cur:
            cur.execute("""
            DELETE FROM user_words WHERE user_id = %s AND id = %s
            RETURNING id;""", (user_id, word_id))
            result = cur.fetchone()

            if result is None:
                return False

        conn.commit()
        return True
    finally:
        conn.close()


def update_stats(user_id, word_id, word_type, is_correct):

    conn = get_db_connection()

    if conn is None:
        return None

    correct_increment = 1 if is_correct else 0

    try:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO learning_stats (
            user_id,
            word_id,
            word_type,
            correct_answers,
            total_attempts
            )
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id, word_id, word_type)
            DO UPDATE SET 
            correct_answers = learning_stats.correct_answers + EXCLUDED.correct_answers,
            total_attempts = learning_stats.total_attempts + EXCLUDED.total_attempts,
            last_reviewed = CURRENT_TIMESTAMP;""",
                        (user_id, word_id, word_type, correct_increment, 1))
        conn.commit()
    finally:
        conn.close()


def get_statistics(user_id):
    conn = get_db_connection()

    if conn is None:
        return None

    try:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT
            COALESCE(SUM(correct_answers), 0),
            COALESCE(SUM(total_attempts), 0)
            FROM learning_stats WHERE user_id = %s;""", (user_id,))
            result = cur.fetchone()
            correct_answers = result[0]
            total_attempts = result[1]

            if total_attempts == 0:
                accuracy = 0
            else:
                accuracy = round((correct_answers / total_attempts) * 100, 2)

        return {
            "correct_answers": correct_answers,
            "total_attempts": total_attempts,
            "accuracy": accuracy
        }
    finally:
        conn.close()
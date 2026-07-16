"""
EnglishCard - Приложение для изучения английского языка
Базовый файл-заготовка для курсовой работы
Студенту необходимо доработать этот файл в соответствии с заданием
"""

import streamlit as st
import psycopg2
import pandas as pd
import random

# ============================================================
# НАСТРОЙКА СТРАНИЦЫ
# ============================================================
st.set_page_config(
    page_title="EnglishCard - Изучение английского",
    page_icon="📚",
    layout="wide"
)


# ============================================================
# РАБОТА С БАЗОЙ ДАННЫХ (НЕОБХОДИМО РЕАЛИЗОВАТЬ)
# ============================================================

def get_db_connection():

    try:
        conn = psycopg2.connect(host='localhost', database='english_card', user='postgres', password='ВАШ ПАРОЛЬ')
        return conn
    except psycopg2.Error as er:
        st.error('Ошибка соединения с базой данных!')
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



# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def generate_options(correct_word, all_words):
    available_words = all_words.copy()
    available_words.remove(correct_word)
    wrong_words = [word[2] for word in available_words]

    if len(wrong_words) < 3:
        st.warning("Для викторины необходимо минимум 4 слова.")
        return None

    answer_options = random.sample(wrong_words, 3)
    answer_options.append(correct_word[2])
    random.shuffle(answer_options)
    return answer_options




# ============================================================
# ИНТЕРФЕЙС ПРИЛОЖЕНИЯ (НЕОБХОДИМО ДОРАБОТАТЬ)
# ============================================================

def render_sidebar():

    with st.sidebar:
        if st.session_state.user_id is None:
            st.header("Авторизация")
            user_name = st.text_input("Введите Ваше имя")
            if st.button("Войти"):
                if not user_name.strip():
                    st.warning("Введите имя.")
                else:
                    user_id = login_user(user_name)
                    st.session_state.user_id = user_id
                    st.session_state.username = user_name
                    st.rerun()
        else:
            st.write(f"👋 Привет, {st.session_state.username}!")
            if st.button("Выйти"):
                st.session_state.user_id = None
                st.session_state.username = None
                st.rerun()




def render_study_tab(words):

    if not words:
        st.warning("В словаре отсутствуют слова для изучения.")
        return

    if "current_word" not in st.session_state:
        st.session_state.current_word = random.choice(words)

    if "answer_options" not in st.session_state:
        st.session_state.answer_options = generate_options(
            st.session_state.current_word,
            words
        )

    if "answer_checked" not in st.session_state:
        st.session_state.answer_checked = False

    if "last_answer_correct" not in st.session_state:
        st.session_state.last_answer_correct = False

    current_word = st.session_state.current_word
    answer_options = st.session_state.answer_options

    st.subheader("Переведите слово:")
    st.write(f"**{current_word[1]}**")

    if answer_options is None:
        return

    # Пока пользователь не ответил
    if not st.session_state.answer_checked:

        for option in answer_options:

            if st.button(option):
                is_correct = option == current_word[2]
                update_stats(
                    st.session_state.user_id,
                    current_word[0],
                    current_word[3],
                    is_correct
                )

                st.session_state.last_answer_correct = is_correct
                st.session_state.answer_checked = True
                st.rerun()
    else:
        if st.session_state.last_answer_correct:
            st.success("✅ Правильно!")
        else:
            st.error(f"❌ Неправильно! Правильный ответ: {current_word[2]}")

        if st.button("Следующее слово"):
            st.session_state.current_word = random.choice(words)
            st.session_state.answer_options = generate_options(
                st.session_state.current_word,
                words
            )
            st.session_state.answer_checked = False
            st.session_state.last_answer_correct = False
            st.rerun()


def render_add_word_tab():
    russian_word = st.text_input("Введите слово на русском языке")
    english_word = st.text_input("Введите слово на английском языке")
    if st.button("Добавить"):
        if not russian_word.strip() or not english_word.strip():
            st.warning("Заполните все поля.")
        else:
            result = add_personal_word(st.session_state.user_id, russian_word, english_word)
            if result:
                st.success("Слово успешно добавлено.")
            else:
                st.warning("Такое слово уже существует.")


def render_delete_word_tab(words):

    personal_words = [word for word in words if word[3] == "personal"]

    if not personal_words:
        st.info("У вас нет личных слов.")
        return

    selected_word = st.selectbox(
        "Выберите слово для удаления",
        personal_words,
        format_func=lambda word: f"{word[1]} — {word[2]}"
    )

    if st.button("Удалить"):

        result = delete_personal_word(
            st.session_state.user_id,
            selected_word[0]
        )

        if result:
            st.success("Слово успешно удалено.")
            st.rerun()
        else:
            st.error("Не удалось удалить слово.")


def render_statistics_tab(user_id):

    statistics = get_statistics(user_id)

    if statistics is None:
        st.error("Не удалось получить статистику.")
        return

    st.metric(
        "Правильных ответов",
        statistics["correct_answers"]
    )

    st.metric(
        "Всего попыток",
        statistics["total_attempts"]
    )

    st.metric(
        "Точность",
        f"{statistics['accuracy']:.1f}%"
    )


def render_schema():

    st.subheader("Схема базы данных")

    st.image("schema.png")


# ============================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================

def main():

    st.title("📚 EnglishCard - Изучай английский с удовольствием!")

    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    if "username" not in st.session_state:
        st.session_state.username = None

    init_database()

    render_sidebar()

    if st.session_state.user_id:
        words = get_user_words(st.session_state.user_id)

        tab1, tab2, tab3, tab4 = st.tabs(
            [
                "📖 Изучение",
                "➕ Добавить слово",
                "🗑️ Удалить слово",
                "📊 Статистика"
            ]
        )

        with tab1:
            render_study_tab(words)

        with tab2:
            render_add_word_tab()

        with tab3:
            render_delete_word_tab(words)

        with tab4:
            render_statistics_tab(st.session_state.user_id)
    else:
        st.info("Введите имя пользователя для начала работы.")


if __name__ == "__main__":
    main()
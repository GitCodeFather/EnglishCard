import os
import random
import streamlit as st
from database import (
    login_user,
    add_personal_word,
    delete_personal_word,
    update_stats,
    get_statistics
)

from utils import generate_options


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

    if "message" not in st.session_state:
        st.session_state.message = ""

    current_word = st.session_state.current_word
    answer_options = st.session_state.answer_options

    st.subheader("Переведите слово:")
    st.write(f"**{current_word[1]}**")

    if answer_options is None:
        return

    if st.session_state.message:
        st.info(st.session_state.message)

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
                if is_correct:
                    st.session_state.message = "✅ Правильно!"
                    st.session_state.answer_checked = True
                else:
                    st.session_state.message = "❌ Неправильно! Попробуйте еще раз."
                st.rerun()
    else:
        if st.button("Следующее слово"):
            st.session_state.current_word = random.choice(words)
            st.session_state.answer_options = generate_options(
                st.session_state.current_word,
                words
            )
            st.session_state.answer_checked = False
            st.session_state.message = ""
            st.rerun()


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
    st.subheader("🗄️ Схема базы данных")
    schema_path = os.path.join(
        os.path.dirname(__file__),
        "schema.png"
    )
    st.image(schema_path)
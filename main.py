"""
EnglishCard - Приложение для изучения английского языка

Главный файл запуска приложения.
Отвечает за инициализацию,
авторизацию и отображение вкладок.
"""

import streamlit as st
from database import (
    init_database,
    get_user_words
)
from ui import (
    render_sidebar,
    render_study_tab,
    render_add_word_tab,
    render_delete_word_tab,
    render_statistics_tab,
    render_schema
)

st.set_page_config(
    page_title="EnglishCard - Изучение английского",
    page_icon="📚",
    layout="wide"
)


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

        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            [
                "📖 Изучение",
                "➕ Добавить слово",
                "🗑️ Удалить слово",
                "📊 Статистика",
                "🗄️ Схема БД"
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

        with tab5:
            render_schema()
    else:
        st.info("Введите имя пользователя для начала работы.")


if __name__ == "__main__":
    main()

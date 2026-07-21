import random
import streamlit as st


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
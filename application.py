import streamlit as st
import pandas as pd
import io
import requests

from sqlalchemy import create_engine, text

# =========================
# CONFIG
# =========================
OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]

# =========================
# DB
# =========================
engine = create_engine("sqlite:///bank_surveys.db")

# =========================
# SQL EXECUTOR
# =========================
def run_sql(query: str) -> str:
    try:
        with engine.connect() as con:
            result = con.execute(text(query))
            columns = result.keys()

            output = " | ".join(columns) + "\n"
            output += "-" * 50 + "\n"

            for row in result:
                output += " | ".join(str(val) for val in row) + "\n"

        return output
    except Exception as e:
        return f"SQL Error: {str(e)}"

def clean_sql(sql: str) -> str:
    sql = sql.strip()

    # убираем ```sql ``` или ```
    if sql.startswith("```"):
        sql = sql.replace("```sql", "")
        sql = sql.replace("```", "")

    return sql.strip()

# =========================
# LLM → SQL
# =========================
def generate_sql(question):
    prompt = f"""
Ты аналитик данных.

Преобразуй вопрос пользователя в SQL-запрос.

Таблица: survey_responses
Колонки:
- response_id
- survey_id
- customer_id
- product_name
- score
- comment
- response_date
- channel

Правила:
- Используй только эту таблицу
- Синтаксис SQLite
- Верни ТОЛЬКО SQL
- Без markdown
- Без ```sql

Вопрос: {question}
"""

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "openrouter/auto",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
    )

    result = response.json()
    return result["choices"][0]["message"]["content"].strip()

# =========================
# SQL → INSIGHTS
# =========================
def explain_results(question, sql_result):
    prompt = f"""
Ты бизнес-аналитик.

Вопрос пользователя:
{question}

Результат SQL:
{sql_result}

Объясни выводы простым языком НА РУССКОМ.
Напиши кратко и по делу.
"""

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "openrouter/auto",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
    )

    result = response.json()
    return result["choices"][0]["message"]["content"]

# =========================
# UI
# =========================
st.set_page_config(page_title="AI Analyst", layout="wide")

st.title("Привет! Я твой аналитический помощник")
st.caption("Жду твои вопросы по клиентским оценкам")

# sidebar
st.sidebar.title("Примеры")

examples = [
    "Средняя оценка по продуктам",
    "Сколько оценок в мае",
    "Оценки по каналам",
    "Оценки по возрастным группам",
    "Какая доля оценок 10"
]

for ex in examples:
    if st.sidebar.button(ex):
        st.session_state["query"] = ex

query = st.chat_input("Введите вопрос...")

if "query" in st.session_state:
    query = st.session_state.pop("query")

# =========================
# RESPONSE
# =========================
if query:
    with st.chat_message("user"):
        st.write(query)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            try:
                sql = generate_sql(query)
                sql = clean_sql(sql)
                st.code(sql, language="sql")

                result = run_sql(sql)
                st.write(result)

                # график
                try:
                    df = pd.read_csv(io.StringIO(result), sep="|")
                    df.columns = [c.strip() for c in df.columns]

                    if len(df.columns) == 2:
                        st.bar_chart(df.set_index(df.columns[0]))
                except:
                    pass

                st.markdown("### 💡 Insights")
                insights = explain_results(query, result)
                st.write(insights)

            except Exception as e:
                st.error("Ошибка при обработке запроса")
                st.text(str(e))

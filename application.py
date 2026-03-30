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

# =========================
# LLM → SQL
# =========================
def generate_sql(question):
    prompt = f"""
You are a data analyst.

Convert the question into SQL query.

Table: survey_responses
Columns:
- response_id
- survey_id
- customer_id
- product_name
- score
- comment
- response_date
- channel

Rules:
- Use only this table
- Return ONLY SQL
- SQLite syntax

Question: {question}
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
You are a business analyst.

User question:
{question}

SQL result:
{sql_result}

Explain insights in simple terms.
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

st.title("📊 AI Data Analyst")
st.caption("Ask questions → get insights from your data")

# sidebar
st.sidebar.title("💡 Examples")

examples = [
    "Средняя оценка по продуктам",
    "Какие продукты хуже всего",
    "Оценки по каналам",
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

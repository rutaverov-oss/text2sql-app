# 2 версия

!pip install streamlit

import streamlit as st
import pandas as pd
import io

from smolagents import CodeAgent, HfApiModel, tool
from sqlalchemy import create_engine, text

# =========================
# DB
# =========================
engine = create_engine("sqlite:///bank_surveys.db")

# =========================
# TOOL
# =========================
@tool
def sql_engine(query: str) -> str:
    """
    Execute SQL query on the survey_responses table.

    Table schema:
    survey_responses (
        response_id INTEGER PRIMARY KEY,
        survey_id INTEGER,
        customer_id INTEGER,
        product_name TEXT,
        score INTEGER,
        comment TEXT,
        response_date TEXT,
        channel TEXT
    )

    Args:
        query: SQL query in SQLite syntax.

    Returns:
        String with query result (table format).
    """
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
        return f"Error: {str(e)}"

# =========================
# AGENT
# =========================
@st.cache_resource
def load_agent():
    model = HfApiModel("Qwen/Qwen2.5-7B-Instruct")
    return CodeAgent(tools=[sql_engine], model=model)

agent = load_agent()

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

if query:
    with st.chat_message("user"):
        st.write(query)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            try:
                response = agent.run(query)
                st.write(response)

                # график
                try:
                    df = pd.read_csv(io.StringIO(response), sep="|")
                    df.columns = [c.strip() for c in df.columns]

                    if len(df.columns) == 2:
                        st.bar_chart(df.set_index(df.columns[0]))
                except:
                    pass

            except Exception as e:
                st.error(f"Ошибка: {str(e)}")
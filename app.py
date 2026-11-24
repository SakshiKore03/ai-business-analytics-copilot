# AI Business Analytics Copilot
# Flow: your question -> AI writes SQL -> database runs it -> table + chart -> AI explains in simple words

import time
import sqlite3

import streamlit as st
import pandas as pd
from google import genai
from google.genai import errors, types

st.set_page_config(page_title="AI Business Analytics Copilot", layout="wide")
st.title("📊 AI Business Analytics Copilot")
st.caption("Upload your sales data and ask questions in plain English.")

# ---------- 1. Connect to the AI ----------
# Give up on a slow request after 30 seconds, and do not let the library retry silently
try:
    http_opts = types.HttpOptions(timeout=30_000, retry_options=types.HttpRetryOptions(attempts=1))
except Exception:
    http_opts = types.HttpOptions(timeout=30_000)
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"], http_options=http_opts)
MODELS = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-4-hydrogen"]

# "low" thinking = faster answers (this task does not need deep reasoning)
FAST_CONFIG = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_level="low")
)


def call_model(model, prompt):
    try:
        return client.models.generate_content(model=model, contents=prompt, config=FAST_CONFIG)
    except errors.ClientError as e:
        if e.code == 400:   # this model does not accept the thinking setting -> call it normally
            return client.models.generate_content(model=model, contents=prompt)
        raise


@st.cache_data(show_spinner=False)   # same prompt asked again = instant answer
def ask_ai(prompt):
    problems = []                             # remember why each model failed
    deadline = time.time() + 90               # never wait more than ~90 seconds in total
    for model in MODELS:                      # try each model in turn
        for attempt in range(2):              # up to 2 tries per model
            if time.time() > deadline:
                break
            try:
                response = call_model(model, prompt)
                text = (response.text or "").strip()
                if text:
                    return text
                problems.append(f"{model}: empty answer")
                break                         # empty answer -> try the next model
            except errors.ServerError:        # 503: Google is busy -> short wait, retry
                problems.append(f"{model}: busy (503)")
                time.sleep(2)
            except errors.ClientError as e:
                if e.code == 429:             # quota used up -> next model
                    problems.append(f"{model}: quota used up (429)")
                    break
                elif e.code == 404:           # model not available -> next model
                    problems.append(f"{model}: not available (404)")
                    break
                else:
                    raise
            except Exception as e:            # timeout or network problem -> next model
                problems.append(f"{model}: {type(e).__name__}")
                break
    raise RuntimeError("All models failed -> " + " | ".join(problems))


# ---------- 2. Load the data (cached so the app stays fast) ----------
@st.cache_data
def load_data(file):
    df = pd.read_csv(file)
    # SQL does not like spaces in column names, so replace them with _
    df.columns = df.columns.str.strip().str.replace(r"[ \-]", "_", regex=True)
    return df


@st.cache_resource
def make_database(file_name, _df):
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    _df.to_sql("data", conn, index=False)
    return conn


# ---------- 3. Sidebar ----------
file = st.sidebar.file_uploader("Upload your sales CSV", type="csv")
st.sidebar.markdown("**Try asking:**")
st.sidebar.markdown(
    "- Which 5 countries have the highest total revenue?\n"
    "- How many unique customers are there?\n"
    "- Which 10 products sold the most units?\n"
    "- What is the total revenue for each month?"
)

# ---------- 4. Main app ----------
if file is None:
    st.info("👈 Upload a CSV file from the sidebar to begin (for example retail_clean.csv).")
else:
    with st.spinner("Loading data (only slow the first time)..."):
        df = load_data(file)
        conn = make_database(file.name, df)

    st.subheader("Your data")
    st.write(f"{len(df):,} rows and {df.shape[1]} columns")
    st.dataframe(df.head(10))

    question = st.text_input("Ask a question about your business")

    if question:
        start = time.time()

        # Step A: AI writes the SQL query
        sql_prompt = f"""You are a data analyst. SQLite table name: data
Columns and types:
{df.dtypes.to_string()}

Sample rows:
{df.head(3).to_string()}

Notes: date columns are stored as text like 2011-03-15 10:30:00.
Write ONE SQLite SELECT query to answer this question: {question}
Return ONLY the SQL query. No explanation, no markdown."""

        try:
            with st.spinner("AI is writing the SQL query..."):
                sql = ask_ai(sql_prompt)
        except Exception as e:
            st.error(f"The AI could not answer right now. {e}")
            st.stop()
        sql = sql.replace("```sql", "").replace("```", "").strip()

        st.subheader("Generated SQL")
        st.code(sql, language="sql")

        # Step B: safety check - only allow one read-only SELECT query
        if not sql.lower().startswith("select") or ";" in sql.rstrip(";"):
            st.error("Only a single read-only SELECT query is allowed.")
        else:
            try:
                # Step C: run the query
                result = pd.read_sql(sql, conn)
                st.subheader("Result")
                st.dataframe(result)

                # Step D: draw a bar chart when the result has 2 columns (label + number)
                if result.shape[1] == 2 and pd.api.types.is_numeric_dtype(result.iloc[:, 1]):
                    st.bar_chart(result.set_index(result.columns[0]))

                # Step E: AI explains the result in simple words
                st.subheader("💡 AI insight")
                insight_prompt = f"""Question: {question}
Result:
{result.head(20).to_string()}

The currency is British pounds (£), not dollars.
Explain this in 3 short bullet points for a shop owner with no technical
background, then suggest one action they can take."""
                with st.spinner("AI is writing the insight..."):
                    st.write(ask_ai(insight_prompt))

                st.caption(f"⏱ Answered in {time.time() - start:.1f} seconds")
            except Exception as e:
                st.error(f"Something went wrong: {e}. Try rephrasing your question.")
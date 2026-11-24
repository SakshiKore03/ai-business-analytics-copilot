# AI Business Analytics Copilot

Small business owners often cannot afford a data analyst. This app lets them upload sales data, ask questions in plain English, and get tables, charts and simple business insights.

## How it works
1. Upload a sales CSV file
2. Ask a question in plain English
3. An LLM converts the question into a SQL query
4. Only single read-only SELECT queries are allowed to run
5. The app shows a table and chart, and the LLM explains the result in simple words

## Tech stack
Python, Streamlit, SQLite, Pandas, Gemini API

## Tested on
Online Retail dataset (UCI), 397,884 transactions

## Example questions
- Which 5 countries have the highest total revenue?
- Which 10 products sold the most units?

## Handling API problems
The app retries when the AI service is busy, falls back to other models, stops waiting after a time limit, and caches repeated questions.

## Limitations
- Uses the free Gemini tier, so answers can be slow or fail when the service is busy or the quota is used up
- Answers depend on the LLM writing correct SQL, so complex questions can fail

## How to run
1. Install the libraries with `pip install -r requirements.txt`
2. Create `.streamlit/secrets.toml` and add `GEMINI_API_KEY = "your-key"`
3. Run `streamlit run app.py`

## Future improvements
Customer segmentation tab, sales forecasting tab, deployment
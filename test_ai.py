import tomllib
from google import genai

key = tomllib.load(open(".streamlit/secrets.toml", "rb"))["GEMINI_API_KEY"]
client = genai.Client(api_key=key)

for model in ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-4-hydrogen"]:
    try:
        r = client.models.generate_content(model=model, contents="Say hi")
        print(model, "OK ->", r.text.strip())
    except Exception as e:
        print(model, "FAILED ->", str(e)[:150])
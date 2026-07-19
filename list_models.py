
import os
from google import genai
from dotenv import load_dotenv

load_dotenv("backend/.env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

print("Listing Available Models:")
for m in client.models.list():
    if "flash" in m.name or "pro" in m.name:
        print(f"- {m.name}")

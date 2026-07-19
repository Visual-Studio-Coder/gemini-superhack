import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv("backend/.env")

KEY = os.getenv("GEMINI_API_KEY")
if not KEY:
    print("❌ No API Key found in backend/.env")
    exit(1)

print(f"✅ API Key found: {KEY[:5]}...")

genai.configure(api_key=KEY)

try:
    print("🚀 Connecting to Gemini 3 Pro Preview...")
    model = genai.GenerativeModel('gemini-3-pro-preview')
    
    print("📝 Sending prompt: 'Generate 5 funny bingo events for a Hackathon'")
    response = model.generate_content("Generate 5 funny bingo events for a Hackathon. Return valid JSON list of strings.")
    
    print("\n✨ GEMINI RESPONSE:")
    print(response.text)
    print("\n✅ It works! The API is active and responding.")
except Exception as e:
    print(f"\n❌ Error contacting Gemini: {e}")

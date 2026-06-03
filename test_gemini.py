import os
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv

env_path = Path("Tiki_Project/api/.env")
load_dotenv(dotenv_path=env_path)

key = os.getenv("GEMINI_API_KEY")
if not key:
    print("No GEMINI_API_KEY found in .env")
else:
    print(f"Testing Gemini key: {key[:8]}...{key[-8:]}")
    genai.configure(api_key=key)

    try:
        model = genai.GenerativeModel("gemini-flash-latest")
        response = model.generate_content("Xin chào, bạn có hoạt động không?")
        print("Success calling API!")
        with open("gemini_response.txt", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("Wrote response to gemini_response.txt successfully!")
    except Exception as e:
        print("Failed!")
        print("Error:", e)

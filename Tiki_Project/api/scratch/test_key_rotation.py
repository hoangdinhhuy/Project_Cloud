import os
import sys
import google.generativeai as genai
from dotenv import load_dotenv

def main():
    load_dotenv()
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        print("No key found")
        return

    keys = [k.strip() for k in key.split(",") if k.strip()]
    print(f"Loaded keys: {len(keys)}")
    
    # Configure with a fake key first
    print("Configuring with fake key first...")
    genai.configure(api_key="AIzaSyFakeKeyInvalidTesting1234567890")
    model = genai.GenerativeModel("gemini-flash-latest")
    try:
        res = model.generate_content("Say hello in Vietnamese")
        print(f"Success with fake key (unexpected): {res.text}")
    except Exception as e:
        print(f"Expected error with fake key: {type(e).__name__} - {e}")

    # Now configure with the real key and recreate model
    print("Switching to real key and recreating model...")
    genai.configure(api_key=keys[0])
    model = genai.GenerativeModel("gemini-flash-latest")
    try:
        res = model.generate_content("Say hello in Vietnamese")
        print(f"Success with real key: {res.text}")
    except Exception as e:
        print(f"Error with real key: {type(e).__name__} - {e}")

if __name__ == "__main__":
    main()

import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai

def test_key():
    print("Loading .env file...")
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY is not set in .env!")
        return
        
    print(f"🔑 API Key found in .env: {api_key[:10]}...{api_key[-10:] if len(api_key) > 20 else ''}")
    print(f"Length of API Key: {len(api_key)}")
    
    print("Configuring google-generativeai...")
    genai.configure(api_key=api_key)
    
    print("Attempting to list models to verify connection and key validity...")
    try:
        models = genai.list_models()
        model_list = []
        for m in models:
            model_list.append(m.name)
        print(f"✅ Connection successful! Available models count: {len(model_list)}")
        print("First 3 models:")
        for m in model_list[:3]:
            print(f" - {m}")
            
        print("\nAttempting to generate a simple content stream using 'gemini-flash-latest'...")
        model = genai.GenerativeModel("gemini-flash-latest")
        response = model.generate_content("Xin chào, bạn có hoạt động bình thường không? Trả lời rất ngắn gọn.")
        print(f"✅ Text generation successful! Response:\n{response.text}")
        
    except Exception as e:
        print("\n❌ API Key OR Connection check FAILED!")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {e}")
        
if __name__ == "__main__":
    test_key()

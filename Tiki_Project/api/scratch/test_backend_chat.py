import requests
import json
import time

def test_chat():
    url = "http://localhost:8000/api/chat"
    payload = {
        "message": "Tôi muốn kinh doanh thiết bị điện tử với số vốn 150 triệu ở TP.HCM.",
        "session_id": "test_verification_session_123"
    }
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"Sending POST request to {url} (timeout=60s)...")
    start = time.time()
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        duration = time.time() - start
        print(f"Response received in {duration:.2f} seconds.")
        print(f"Response Status Code: {response.status_code}")
        
        if response.status_code == 200:
            res_json = response.json()
            print("[SUCCESS] Backend API Chat responded successfully!")
            print("Response text content preview:")
            print("-" * 50)
            print(res_json.get("response", ""))
            print("-" * 50)
            print("Profile Builder state captured:")
            print(res_json.get("profile"))
        else:
            print(f"[ERROR] Backend API returned error! Details: {response.text}")
            
    except Exception as e:
        duration = time.time() - start
        print(f"[FAIL] Connection or request failed after {duration:.2f} seconds: {e}")

if __name__ == "__main__":
    test_chat()

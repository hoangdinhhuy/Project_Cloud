import requests
import sys

def check_health():
    url = "http://localhost:8000/health"
    print(f"Checking backend health at {url}...")
    try:
        response = requests.get(url, timeout=5)
        print(f"Status Code: {response.status_code}")
        print("Response JSON:")
        print(response.json())
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    check_health()

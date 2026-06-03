import requests, json, sys
url = 'http://127.0.0.1:8000/api/chat'
payload = {'message': 'Phân tích kỹ sản phẩm Sách Cây Cam Ngọt Của Tôi cho tôi', 'session_id': 'test'}
try:
    print("Sending request to /api/chat (timeout=60)...")
    resp = requests.post(url, json=payload, timeout=60)
    print('Status:', resp.status_code)
    with open('chat_response.txt', 'w', encoding='utf-8') as f:
        f.write(resp.text)
    print("Wrote response to chat_response.txt successfully!")
except Exception as e:
    print('Error:', e, file=sys.stderr)
    sys.exit(1)

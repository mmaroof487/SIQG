import requests
import json

def test():
    token = None
    with open('.env', 'r') as f:
        for line in f:
            if line.startswith('VITE_TEMP_TOKEN='):
                token = line.split('=', 1)[1].strip().strip('"').strip("'")
                break
    
    url = 'http://localhost:8000/api/v1/connections'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    payload = {
        "display_name": "Test",
        "db_type": "postgres",
        "conn_str": "postgresql://argus:argus@postgres:5432/argus"
    }
    res = requests.post(url, headers=headers, json=payload)
    print("Status:", res.status_code)
    print("Response:", res.text)

if __name__ == '__main__':
    test()

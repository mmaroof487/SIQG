import os
import requests
import json

def test():
    token = None
    with open('.env', 'r') as f:
        for line in f:
            if line.startswith('VITE_TEMP_TOKEN='):
                token = line.split('=', 1)[1].strip().strip('"').strip("'")
                break
    
    if not token:
        print("No token found")
        return

    url = 'http://localhost:8000/api/v1/connections/e1c1d7bd-77ab-41dc-bc0d-dd4d06cec80b/test'
    headers = {'Authorization': f'Bearer {token}'}
    res = requests.post(url, headers=headers)
    print("Status:", res.status_code)
    print("Response:", res.text)

if __name__ == '__main__':
    test()


import urllib.request
import json
import sys

def test_login():
    url = "http://localhost:8000/auth/login"
    payload = {
        "email": "subramaniyam@manager.com",
        "password": "Admin@123"
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    try:
        print(f"Sending POST to {url}")
        with urllib.request.urlopen(req) as response:
            print(f"Status Code: {response.getcode()}")
            response_body = response.read()
            print("Login SUCCESS!")
            print(response_body.decode('utf-8'))
            
    except urllib.request.HTTPError as e:
        print(f"Login FAILED! Status: {e.code}")
        print(e.read().decode('utf-8'))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_login()

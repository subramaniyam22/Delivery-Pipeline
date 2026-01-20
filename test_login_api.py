
import requests
import sys

def test_login():
    url = "http://localhost:8000/auth/login"
    payload = {
        "email": "subramaniyam@manager.com",
        "password": "Admin@123"
    }
    
    try:
        print(f"Sending POST to {url}")
        res = requests.post(url, json=payload)
        print(f"Status Code: {res.status_code}")
        if res.status_code == 200:
            print("Login SUCCESS!")
            print(res.json())
        else:
            print("Login FAILED!")
            print(res.text)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_login()

import requests
import json

BASE_URL = "http://localhost:8000"

def get_users():
    # 1. Login as Admin
    login_data = {
        "email": "subramaniyam.webdesigner@gmail.com",
        "password": "admin123"
    }
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        response.raise_for_status()
        token = response.json().get("access_token")
        print(f"Got Admin Token.")
    except Exception as e:
        print(f"Login failed: {e}")
        try:
            print(response.text)
        except:
            pass
        return

    # 2. List Users
    headers = {
        "Authorization": f"Bearer {token}"
    }
    try:
        response = requests.get(f"{BASE_URL}/users", headers=headers)
        response.raise_for_status()
        users = response.json()
        print(f"Found {len(users)} users:")
        for u in users:
            print(f"- Name: {u.get('name')}, Email: {u.get('email')}, Role: {u.get('role')}")
            
    except Exception as e:
        print(f"List users failed: {e}")
        try:
            print(response.text)
        except:
            pass

if __name__ == "__main__":
    get_users()

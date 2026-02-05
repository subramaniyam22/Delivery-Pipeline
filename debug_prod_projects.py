import requests
import json

BASE_URL = "https://delivery-backend-vvbf.onrender.com"
# Admin credentials from main.py seeding
EMAIL = "subramaniyam.webdesigner@gmail.com"
PASSWORD = "admin123"

def debug_prod():
    print(f"Logging in as {EMAIL}...")
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD})
        print(f"Login Status: {resp.status_code}")
        if resp.status_code != 200:
            print("Login Failed:", resp.text)
            return

        token = resp.json()["access_token"]
        print("Token received. Fetching /projects...")
        
        headers = {"Authorization": f"Bearer {token}"}
        proj_resp = requests.get(f"{BASE_URL}/projects", headers=headers)
        
        print(f"Projects Status: {proj_resp.status_code}")
        print("Response Body:")
        print(proj_resp.text)
        
    except Exception as e:
        print(f"Script Error: {e}")

if __name__ == "__main__":
    debug_prod()

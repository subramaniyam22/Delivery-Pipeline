
import requests
import json

url = "http://localhost:8000/auth/login"
payload = {
    "email": "subramaniyam@consultant.com",
    "password": "password"
}
headers = {
    "Content-Type": "application/json"
}

try:
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print("Response Body:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")


from app.auth import create_access_token
try:
    token = create_access_token(data={"sub": "test@example.com"})
    print(f"Token created: {token}")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Error: {e}")

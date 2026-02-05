"""
Test authentication flow to identify timeout issue.
"""
import sys
import time
from app.db import SessionLocal
from app.models import User
from app.auth import create_access_token, decode_access_token

def test_auth_flow():
    print("Testing authentication flow...")
    db = SessionLocal()
    
    try:
        # Get a test user
        user = db.query(User).filter(User.is_active == True).first()
        if not user:
            print("✗ No active users found in database")
            return
        
        print(f"✓ Found user: {user.email}")
        
        # Create token
        start = time.time()
        token = create_access_token({"sub": user.email})
        elapsed = time.time() - start
        print(f"✓ Token created in {elapsed:.3f}s")
        
        # Decode token
        start = time.time()
        payload = decode_access_token(token)
        elapsed = time.time() - start
        print(f"✓ Token decoded in {elapsed:.3f}s")
        print(f"  Payload: {payload}")
        
        if payload is None:
            print("✗ Token decode failed!")
            return
        
        # Simulate deps.py flow
        start = time.time()
        email = payload.get("sub")
        user_check = db.query(User).filter(User.email == email).first()
        elapsed = time.time() - start
        print(f"✓ User lookup in {elapsed:.3f}s")
        
        if user_check:
            print(f"✓ Authentication flow works!")
            print(f"  User: {user_check.name} ({user_check.role.value})")
        else:
            print("✗ User not found after token decode")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_auth_flow()

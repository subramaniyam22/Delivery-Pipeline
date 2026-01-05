#!/usr/bin/env python3
"""
Seed script to create initial admin user
Run with: python scripts/seed_admin.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db import SessionLocal
from app.models import User, Role
from app.auth import hash_password

def seed_admin():
    """Create initial admin user"""
    db = SessionLocal()
    
    try:
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.email == "admin@delivery.com").first()
        if existing_admin:
            print("Admin user already exists!")
            return
        
        # Create admin user
        admin = User(
            name="Admin User",
            email="admin@delivery.com",
            password_hash=hash_password("admin123"),
            role=Role.ADMIN,
            is_active=True
        )
        db.add(admin)
        db.commit()
        
        print("✓ Admin user created successfully!")
        print("  Email: admin@delivery.com")
        print("  Password: admin123")
        print("  Role: ADMIN")
        print("\n⚠️  Please change the password after first login!")
        
    except Exception as e:
        print(f"Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()

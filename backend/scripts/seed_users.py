from app.db import SessionLocal
from app.models import User, Role, Region
from app.auth import hash_password


USERS = [
    # Admin
    {"email": "subramaniyam.webdesigner@gmail.com", "password": "Admin@123", "role": Role.ADMIN},
    # Consultant
    {"email": "subramaniyam@consultant.com", "password": "Admin@123", "role": Role.CONSULTANT},
    {"email": "jane@consultant.com", "password": "Admin@123", "role": Role.CONSULTANT},
    # PC
    {"email": "subramaniyam@pc.com", "password": "Admin@123", "role": Role.PC},
    {"email": "john@pc.com", "password": "Admin@123", "role": Role.PC},
    # Builder
    {"email": "subramaniyam@builder.com", "password": "Admin@123", "role": Role.BUILDER},
    {"email": "bob@builder.com", "password": "Admin@123", "role": Role.BUILDER},
    # Tester
    {"email": "subramaniyam@tester.com", "password": "Admin@123", "role": Role.TESTER},
    {"email": "alice@tester.com", "password": "Admin@123", "role": Role.TESTER},
    # Manager
    {"email": "subramaniyam@manager.com", "password": "Admin@123", "role": Role.MANAGER},
    {"email": "alice@manager.com", "password": "Admin@123", "role": Role.MANAGER},
    {"email": "subramaniyam@usmanager.com", "password": "Admin@123", "role": Role.MANAGER},
    # Sales
    {"email": "subramaniyam@sales.com", "password": "Admin@123", "role": Role.SALES},
    {"email": "alice@sales.com", "password": "Admin@123", "role": Role.SALES},
]


def _name_from_email(email: str) -> str:
    local = email.split("@", 1)[0]
    cleaned = local.replace(".", " ").replace("_", " ").replace("-", " ")
    parts = [p for p in cleaned.split() if p]
    return " ".join(part.capitalize() for part in parts) or email


def main() -> None:
    db = SessionLocal()
    created = 0
    updated = 0
    try:
        for item in USERS:
            email = item["email"]
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                existing.password_hash = hash_password(item["password"])
                existing.role = item["role"]
                existing.is_active = True
                existing.is_archived = False
                if not existing.name:
                    existing.name = _name_from_email(email)
                if not existing.region:
                    existing.region = Region.INDIA
                db.commit()
                updated += 1
                print(f"UPDATED: {email} ({item['role'].value})")
                continue

            user = User(
                name=_name_from_email(email),
                email=email,
                password_hash=hash_password(item["password"]),
                role=item["role"],
                region=Region.INDIA,
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            created += 1
            print(f"CREATED: {email} ({item['role'].value})")
    finally:
        db.close()

    print(f"\nDone. Created: {created}, Updated: {updated}")


if __name__ == "__main__":
    main()

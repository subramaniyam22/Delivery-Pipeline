
from app.db import engine, Base
from app.models import Notification
from sqlalchemy import inspect

def create_table():
    inspector = inspect(engine)
    if not inspector.has_table("notifications"):
        print("Creating notifications table...")
        Notification.__table__.create(engine)
        print("Done.")
    else:
        print("Table 'notifications' already exists.")

if __name__ == "__main__":
    create_table()

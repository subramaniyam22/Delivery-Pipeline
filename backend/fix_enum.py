from sqlalchemy import create_engine, text
from app.config import settings

# Parse URL or use direct string if imports fail
# Assuming settings.database_url_fixed is available.
# Try to import settings. If fails, I might need to construct URL.

try:
    from app.config import settings
    url = settings.database_url_fixed
except ImportError:
    # Fallback or error
    print("Could not import settings")
    exit(1)

engine = create_engine(url)

# ALTER TYPE cannot run in transaction block mostly.
# Use isolation_level="AUTOCOMMIT"
with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
    try:
        connection.execute(text("ALTER TYPE role ADD VALUE 'SALES'"))
        print("Successfully added 'SALES' to role enum.")
    except Exception as e:
        print(f"Error: {e}")

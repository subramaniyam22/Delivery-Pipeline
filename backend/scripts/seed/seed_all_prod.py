"""
Run all prod seeds: 3 core templates only. Idempotent.
Run from backend: python -m scripts.seed.seed_all_prod
"""
import os
import sys

_backend = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from scripts.seed.common import check_db_connection
from scripts.seed.seed_templates_prod import main as seed_templates_prod_main


def main():
    check_db_connection()
    print("Running prod seed...")
    seed_templates_prod_main()
    print("Done.")


if __name__ == "__main__":
    main()

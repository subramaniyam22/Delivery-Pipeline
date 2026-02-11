"""
Run all demo seeds: templates (12) + ensure demo dataset keys exist.
Run from backend: python -m scripts.seed.seed_all_demo
"""
import os
import sys

_backend = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

# Import after path fix
from scripts.seed.common import check_db_connection
from scripts.seed.seed_templates_demo import main as seed_templates_demo_main


def main():
    check_db_connection()
    print("Running demo seed (templates + demo dataset keys)...")
    seed_templates_demo_main()
    print("Demo dataset key: pmc_default_v1 (use GET /api/templates/demo-dataset?key=pmc_default_v1)")
    print("Done.")


if __name__ == "__main__":
    main()

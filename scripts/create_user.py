#!/usr/bin/env python3
"""Create or update a user account in the database.

Usage examples:
  python scripts/create_user.py --username hassan --password 'StrongPass' --admin
  python scripts/create_user.py --username ben --password 'AnotherStrongPass' --admin
  python scripts/create_user.py --username test --password 'TestPass' --display-name test
"""

from __future__ import annotations

import argparse

from llm_api.db import init_db
from llm_api.users import get_user_service


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or update a user account")
    parser.add_argument("--username", required=True, help="Username (or legacy email)")
    parser.add_argument("--password", required=True, help="Account password")
    parser.add_argument(
        "--display-name",
        default=None,
        help="Optional display name (defaults to username)",
    )
    parser.add_argument(
        "--admin",
        action="store_true",
        help="Create/update this account as an admin",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    init_db()
    user = get_user_service().ensure_user(
        email=args.username,
        password=args.password,
        display_name=args.display_name or args.username,
        is_admin=args.admin,
    )
    role = "admin" if user["is_admin"] else "user"
    print(f"Created/updated {role} account: {user['username']}")


if __name__ == "__main__":
    main()

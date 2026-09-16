"""Controlled account provisioning for the MVP.

Self-registration (POST /api/v1/auth/register) can only ever create the
read-only `user` role. This script is the ONLY supported path for creating an
`operator` account, and it is deliberately operator-run, not network-exposed:
there is no privileged account-creation API and none should be added.

Safety properties:
  * The password is read interactively with getpass — never passed as an
    argument, so it never reaches shell history, the process list, or a log.
  * Only `user` and `operator` may be created. `admin` is refused outright:
    it is an internal escalation rank, not a provisionable role.
  * Refuses to touch an email that already exists (no silent role changes and
    no accidental privilege escalation of an existing account).
  * Writes exactly one row and prints no password, hash, token, or key.

Usage (from the repository root, with backend/.env configured):

    backend\\.venv\\Scripts\\python scripts\\provision_account.py \\
        --email operator@example.com --name "Operator One" \\
        --id-number OP-001 --role operator

Then log in normally through the UI or POST /api/v1/auth/login.
"""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.auth.security import hash_password  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.database import init_supabase  # noqa: E402

# `admin` is intentionally excluded: it exists only as an internal rank.
PROVISIONABLE_ROLES = ("user", "operator")
MIN_PASSWORD_LENGTH = 8


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create one MVP account (user or operator). "
                    "The password is prompted for, never passed on the command line.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--id-number", required=True, dest="id_number")
    parser.add_argument("--role", required=True, choices=PROVISIONABLE_ROLES)
    args = parser.parse_args()

    email = args.email.strip().lower()
    name = args.name.strip()
    id_number = args.id_number.strip()

    if "@" not in email:
        print("ERROR: not a valid email address.", file=sys.stderr)
        return 2
    if not name or not id_number:
        print("ERROR: name and id-number are required.", file=sys.stderr)
        return 2

    settings = get_settings()
    if not settings.supabase_configured:
        print("ERROR: Supabase is not configured. Set SUPABASE_URL and "
              "SUPABASE_SERVICE_ROLE_KEY in backend/.env first.", file=sys.stderr)
        return 2

    client = init_supabase()
    if client is None:
        print("ERROR: could not create the Supabase client.", file=sys.stderr)
        return 2

    existing = client.table("users").select("id,role").eq("email", email).limit(1).execute().data
    if existing:
        print(f"ERROR: an account already exists for {email} "
              f"(role={existing[0]['role']}). Refusing to modify it.\n"
              f"       Change a role deliberately in SQL if that is really intended.",
              file=sys.stderr)
        return 3

    password = getpass.getpass(f"Password for {email} ({args.role}): ")
    if len(password) < MIN_PASSWORD_LENGTH:
        print(f"ERROR: password must be at least {MIN_PASSWORD_LENGTH} characters.",
              file=sys.stderr)
        return 2
    if password != getpass.getpass("Confirm password: "):
        print("ERROR: passwords do not match.", file=sys.stderr)
        return 2

    created = client.table("users").insert({
        "name": name,
        "id_number": id_number,
        "email": email,
        "password_hash": hash_password(password),
        "role": args.role,
        "status": "active",
    }).execute().data

    if not created:
        print("ERROR: the account was not created.", file=sys.stderr)
        return 1

    row = created[0]
    # Deliberately prints no hash and no password.
    print(f"Created {row['role']} account for {row['email']} "
          f"(id={row['id']}, status={row['status']}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

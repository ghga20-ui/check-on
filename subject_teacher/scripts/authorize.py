"""Run the initial OAuth consent flow and store the refresh token locally."""
from __future__ import annotations

from subject_teacher.auth.google_oauth import authorize_interactive


def main() -> None:
    credentials = authorize_interactive()
    print("OK - refresh_token saved.")
    print("  has_refresh_token:", bool(credentials.refresh_token))
    print("  scopes:", credentials.scopes)


if __name__ == "__main__":
    main()

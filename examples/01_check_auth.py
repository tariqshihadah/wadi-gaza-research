"""Milestone 1: prove that CDSE credentials work.

This does the smallest possible live check: build a config from your .env and
request an OAuth token. No imagery is downloaded. If this succeeds, the account
and credentials are good and we can move on to fetching a real image.

Run:
    python examples/01_check_auth.py
"""

import sys
from pathlib import Path

# Make the package importable when running this file directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sentinelhub import SentinelHubSession  # noqa: E402

from s2grab.auth import MissingCredentialsError, get_config  # noqa: E402


def main() -> int:
    try:
        config = get_config()
    except MissingCredentialsError as exc:
        print(f"FAIL: {exc}")
        return 1

    print(f"Credentials loaded. client_id ends with ...{config.sh_client_id[-6:]}")

    try:
        session = SentinelHubSession(config=config)
        token = session.token  # triggers the OAuth token request
    except Exception as exc:  # noqa: BLE001 - surface any auth failure clearly
        print(f"FAIL: could not obtain an OAuth token: {exc}")
        return 1

    # token is a dict containing access_token + expiry metadata.
    expires_in = token.get("expires_in", "unknown")
    print(f"OK: obtained an access token (expires_in={expires_in}s).")
    print("Auth works. Ready for milestone 2 (fetch one image).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

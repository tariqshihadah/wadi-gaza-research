"""Authentication: turn CDSE OAuth credentials into an ``SHConfig``.

This is the first unit in the pipeline. If this fails, nothing else can work,
so it is deliberately isolated and easy to test on its own.

Credentials are read from environment variables (optionally loaded from a local
``.env`` file):

    SH_CLIENT_ID       OAuth client id
    SH_CLIENT_SECRET   OAuth client secret

Get them from https://dataspace.copernicus.eu -> Dashboard -> OAuth clients.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from sentinelhub import SHConfig

# CDSE Sentinel Hub service endpoints (these are fixed for the CDSE deployment).
CDSE_TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu"
    "/auth/realms/CDSE/protocol/openid-connect/token"
)
CDSE_BASE_URL = "https://sh.dataspace.copernicus.eu"


class MissingCredentialsError(RuntimeError):
    """Raised when CDSE OAuth credentials are not available in the environment."""


def get_config(load_env: bool = True) -> SHConfig:
    """Build an ``SHConfig`` pointed at CDSE from environment credentials.

    Parameters
    ----------
    load_env:
        When True (default), load a local ``.env`` file first so credentials can
        live outside the shell environment.

    Returns
    -------
    SHConfig
        Configured for the CDSE Sentinel Hub endpoints.

    Raises
    ------
    MissingCredentialsError
        If either credential is absent, with a clear, actionable message.
    """
    if load_env:
        load_dotenv()

    client_id = os.environ.get("SH_CLIENT_ID", "").strip()
    client_secret = os.environ.get("SH_CLIENT_SECRET", "").strip()

    missing = [
        name
        for name, value in (
            ("SH_CLIENT_ID", client_id),
            ("SH_CLIENT_SECRET", client_secret),
        )
        if not value
    ]
    if missing:
        raise MissingCredentialsError(
            "Missing CDSE credential(s): "
            + ", ".join(missing)
            + ". Set them in your environment or a local .env file "
            "(see .env.example)."
        )

    config = SHConfig()
    config.sh_client_id = client_id
    config.sh_client_secret = client_secret
    config.sh_token_url = CDSE_TOKEN_URL
    config.sh_base_url = CDSE_BASE_URL
    return config

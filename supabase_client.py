"""
supabase_client
================

Single shared Supabase client for both the Streamlit app and the standalone
event generator. Credentials are read from Streamlit secrets when available
(``st.secrets``) and fall back to plain environment variables, so the same
module works inside ``streamlit run app.py`` and in a bare ``python
generator.py`` process.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from supabase import Client, create_client

_client: Optional[Client] = None

# ``st.secrets`` resolves ``.streamlit/secrets.toml`` relative to the process's
# current working directory, not relative to this file. If the app is launched
# from outside the project root (a different terminal cwd, an IDE run config,
# etc.) that lookup silently misses. As a last-resort fallback, also look for
# the secrets file next to this module so credentials are found regardless of
# where ``streamlit run`` / ``python generator.py`` was invoked from.
_LOCAL_SECRETS_PATH = Path(__file__).parent / ".streamlit" / "secrets.toml"
_local_secrets: Optional[dict] = None


def _load_local_secrets() -> dict:
    global _local_secrets
    if _local_secrets is not None:
        return _local_secrets
    _local_secrets = {}
    if _LOCAL_SECRETS_PATH.exists():
        try:
            try:
                import tomllib as _toml_reader  # Python 3.11+
            except ModuleNotFoundError:
                import tomli as _toml_reader  # Python < 3.11

            with open(_LOCAL_SECRETS_PATH, "rb") as f:
                _local_secrets = _toml_reader.load(f)
        except Exception:
            _local_secrets = {}
    return _local_secrets


def _read_secret(key: str) -> Optional[str]:
    try:
        import streamlit as st

        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    env_val = os.environ.get(key)
    if env_val:
        return env_val
    return _load_local_secrets().get(key) or None


def get_supabase_client() -> Optional[Client]:
    """Return a cached Supabase client, or ``None`` if credentials are missing."""
    global _client
    if _client is not None:
        return _client

    url = _read_secret("SUPABASE_URL")
    key = _read_secret("SUPABASE_KEY")
    if not url or not key:
        return None

    _client = create_client(url, key)
    return _client

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
from typing import Optional

from supabase import Client, create_client

_client: Optional[Client] = None


def _read_secret(key: str) -> Optional[str]:
    try:
        import streamlit as st

        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.environ.get(key)


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

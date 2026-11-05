"""API Key storage via the Windows Credential Manager, never plain config."""
from __future__ import annotations

import keyring
from keyring.errors import KeyringError

SERVICE = "HoshiriPet"
DEFAULT_PROVIDER = "deepseek"


def _account(provider: str) -> str:
    return "deepseek" if provider == "deepseek" else f"{provider}"


def get_key(provider: str = DEFAULT_PROVIDER) -> str:
    try:
        return keyring.get_password(SERVICE, _account(provider)) or ""
    except KeyringError:
        return ""


def set_key(value: str, provider: str = DEFAULT_PROVIDER) -> bool:
    try:
        keyring.set_password(SERVICE, _account(provider), value.strip())
        return True
    except KeyringError:
        return False


def clear_key(provider: str = DEFAULT_PROVIDER) -> None:
    try:
        keyring.delete_password(SERVICE, _account(provider))
    except KeyringError:
        pass

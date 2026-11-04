"""API Key 的存取，走 Windows 凭据管理器，不落明文。"""

from __future__ import annotations

import keyring
from keyring.errors import KeyringError

SERVICE = "HoshiriPet"
ACCOUNT = "deepseek"


def get_key() -> str:
    try:
        return keyring.get_password(SERVICE, ACCOUNT) or ""
    except KeyringError:
        return ""


def set_key(value: str) -> bool:
    try:
        keyring.set_password(SERVICE, ACCOUNT, value.strip())
        return True
    except KeyringError:
        return False


def clear_key() -> None:
    try:
        keyring.delete_password(SERVICE, ACCOUNT)
    except KeyringError:
        pass

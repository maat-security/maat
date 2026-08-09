"""Encrypted local key-value store for Maat.

The store is backed by an in-memory SQLite database. Its contents are
serialized to a SQL script, encrypted with a passphrase-derived key, and
written to disk as a single opaque blob. Nothing readable ever touches
disk — there is no plaintext temp file at any point.

Key derivation: PBKDF2HMAC (SHA-256, 480,000 iterations) over the
passphrase, with a random salt generated once per vault and stored
alongside the encrypted file. The derived key drives a Fernet cipher
(AES-128-CBC + HMAC), which is acceptable for Phase 0 — a full
AES-256-GCM scheme is a later hardening pass, not a blocker here.
"""

import base64
import os
import sqlite3
import sys
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

PBKDF2_ITERATIONS = 480_000
SALT_SIZE_BYTES = 16
APP_DIR_NAME = "Maat"
VAULT_FILE_NAME = "vault.enc"
SALT_FILE_NAME = "vault.salt"

# Module-level store state. Phase 0 supports a single open vault per process.
_connection = None
_fernet = None
_store_path = None


class StoreError(Exception):
    """Raised for any store-level failure: missing vault, wrong
    passphrase, or an operation attempted before the store is open."""


def get_app_data_dir() -> Path:
    """Return the OS-appropriate directory for Maat's local data.

    Windows: %APPDATA%\\Maat
    macOS:   ~/Library/Application Support/Maat
    Linux:   ~/.local/share/Maat

    This path is fixed from Phase 0 onward so a future desktop app
    migration never requires a data migration.
    """
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / APP_DIR_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    return Path.home() / ".local" / "share" / APP_DIR_NAME


def get_vault_path() -> Path:
    """Return the path to the encrypted vault file."""
    return get_app_data_dir() / VAULT_FILE_NAME


def get_salt_path() -> Path:
    """Return the path to the stored key-derivation salt."""
    return get_app_data_dir() / SALT_FILE_NAME


def store_exists() -> bool:
    """Return True if a vault already exists on disk."""
    return get_vault_path().exists() and get_salt_path().exists()


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive a Fernet-compatible key from a passphrase and salt.

    A fresh KDF instance is created per call — cryptography's KDF
    objects are single-use.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    derived = kdf.derive(passphrase.encode("utf-8"))
    return base64.urlsafe_b64encode(derived)


def _new_connection() -> sqlite3.Connection:
    """Create a fresh in-memory SQLite database with the base schema."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    return conn


def _dump_to_bytes(conn: sqlite3.Connection) -> bytes:
    """Serialize the in-memory database to a SQL script, as bytes.

    This is the "temp buffer" the database is written to before
    encryption — an in-memory string, never a file on disk.
    """
    script = "\n".join(conn.iterdump())
    return script.encode("utf-8")


def _load_from_bytes(data: bytes) -> sqlite3.Connection:
    """Rebuild an in-memory database from a serialized SQL script."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(data.decode("utf-8"))
    conn.commit()
    return conn


def _persist() -> None:
    """Encrypt the current in-memory database and write it to disk."""
    if _connection is None or _fernet is None:
        raise StoreError("Store is not open.")
    plaintext = _dump_to_bytes(_connection)
    ciphertext = _fernet.encrypt(plaintext)
    vault_path = get_vault_path()
    vault_path.parent.mkdir(parents=True, exist_ok=True)
    vault_path.write_bytes(ciphertext)


def init_store(passphrase: str) -> None:
    """Create a brand new vault protected by the given passphrase.

    Raises StoreError if a vault already exists at the target path —
    call unlock_store() for an existing vault instead.
    """
    global _connection, _fernet, _store_path

    if not passphrase:
        raise StoreError("Passphrase cannot be empty.")

    if store_exists():
        raise StoreError("A vault already exists. Use unlock_store() instead.")

    app_dir = get_app_data_dir()
    app_dir.mkdir(parents=True, exist_ok=True)

    salt = os.urandom(SALT_SIZE_BYTES)
    get_salt_path().write_bytes(salt)

    key = _derive_key(passphrase, salt)
    _fernet = Fernet(key)
    _connection = _new_connection()
    _store_path = get_vault_path()

    _persist()


def unlock_store(passphrase: str) -> None:
    """Open an existing vault with the given passphrase.

    Raises StoreError if no vault exists, or if the passphrase is wrong.
    """
    global _connection, _fernet, _store_path

    if not store_exists():
        raise StoreError("No vault found. Use init_store() to create one.")

    salt = get_salt_path().read_bytes()
    key = _derive_key(passphrase, salt)
    candidate_fernet = Fernet(key)

    ciphertext = get_vault_path().read_bytes()
    try:
        plaintext = candidate_fernet.decrypt(ciphertext)
    except InvalidToken as exc:
        raise StoreError("Incorrect passphrase.") from exc

    _connection = _load_from_bytes(plaintext)
    _fernet = candidate_fernet
    _store_path = get_vault_path()


def store_get(key: str):
    """Return the value stored under key, or None if not present."""
    if _connection is None:
        raise StoreError("Store is not open.")
    row = _connection.execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def store_set(key: str, value: str) -> None:
    """Set key to value and persist the encrypted vault to disk."""
    if _connection is None:
        raise StoreError("Store is not open.")
    _connection.execute(
        "INSERT INTO kv (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    _connection.commit()
    _persist()


def store_close() -> None:
    """Close the store and clear in-memory state. Does not delete the vault file."""
    global _connection, _fernet, _store_path
    if _connection is not None:
        _connection.close()
    _connection = None
    _fernet = None
    _store_path = None

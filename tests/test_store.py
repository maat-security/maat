"""Tests for store.py's encrypted vault: init/unlock lifecycle,
encryption round-trip, and the honest-failure error paths."""

import pytest

import store


def test_init_store_creates_vault_and_salt_files(isolated_store):
    assert not store.store_exists()
    store.init_store("a-throwaway-test-passphrase")
    assert store.store_exists()
    assert store.get_vault_path().exists()
    assert store.get_salt_path().exists()


def test_vault_file_is_not_plaintext_on_disk(isolated_store):
    store.init_store("a-throwaway-test-passphrase")
    store.store_set("some_key", "some plaintext value that must not appear raw")

    raw_bytes = store.get_vault_path().read_bytes()
    assert b"some plaintext value" not in raw_bytes


def test_init_store_rejects_empty_passphrase(isolated_store):
    with pytest.raises(store.StoreError):
        store.init_store("")


def test_init_store_twice_raises(isolated_store):
    store.init_store("first-passphrase")
    store.store_close()
    with pytest.raises(store.StoreError):
        store.init_store("second-passphrase")


def test_unlock_with_correct_passphrase_restores_data(isolated_store):
    store.init_store("correct-passphrase")
    store.store_set("greeting", "hello vault")
    store.store_close()

    store.unlock_store("correct-passphrase")
    assert store.store_get("greeting") == "hello vault"


def test_unlock_with_wrong_passphrase_raises_and_leaves_no_state(isolated_store):
    store.init_store("correct-passphrase")
    store.store_close()

    with pytest.raises(store.StoreError):
        store.unlock_store("wrong-passphrase")


def test_unlock_with_no_vault_raises(isolated_store):
    with pytest.raises(store.StoreError):
        store.unlock_store("anything")


def test_store_get_set_before_open_raises(isolated_store):
    with pytest.raises(store.StoreError):
        store.store_get("x")
    with pytest.raises(store.StoreError):
        store.store_set("x", "y")


def test_store_set_overwrites_existing_key(isolated_store):
    store.init_store("a-throwaway-test-passphrase")
    store.store_set("key", "first")
    store.store_set("key", "second")
    assert store.store_get("key") == "second"


def test_store_get_missing_key_returns_none(isolated_store):
    store.init_store("a-throwaway-test-passphrase")
    assert store.store_get("never-set") is None

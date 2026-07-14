"""Tests for configuration and environment handling."""

import os
import pytest

from solax_cloud_mcp.config import get_default_wifi_sn, get_token_id


def test_get_token_id_success(monkeypatch):
    """Test that get_token_id returns the token when set."""
    monkeypatch.setenv("SOLAX_TOKEN_ID", "test-token-12345")
    assert get_token_id() == "test-token-12345"


def test_get_token_id_missing(monkeypatch):
    """Test that get_token_id raises RuntimeError when token is not set."""
    monkeypatch.delenv("SOLAX_TOKEN_ID", raising=False)
    with pytest.raises(RuntimeError) as exc_info:
        get_token_id()
    assert "SOLAX_TOKEN_ID" in str(exc_info.value)


def test_get_default_wifi_sn_success(monkeypatch):
    """Test that get_default_wifi_sn returns the value when set."""
    monkeypatch.setenv("SOLAX_WIFI_SN", "SUT1234VB1")
    assert get_default_wifi_sn() == "SUT1234VB1"


def test_get_default_wifi_sn_missing(monkeypatch):
    """Test that get_default_wifi_sn returns None when not set."""
    monkeypatch.delenv("SOLAX_WIFI_SN", raising=False)
    assert get_default_wifi_sn() is None

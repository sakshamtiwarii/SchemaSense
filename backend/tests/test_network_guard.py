import pytest

from app.core import network_guard
from app.core.network_guard import UnsafeHostError


@pytest.mark.asyncio
async def test_rejects_loopback_host():
    with pytest.raises(UnsafeHostError):
        await network_guard.assert_host_is_safe("postgresql://u:p@127.0.0.1:5432/db")


@pytest.mark.asyncio
async def test_rejects_private_network_host():
    with pytest.raises(UnsafeHostError):
        await network_guard.assert_host_is_safe("postgresql://u:p@10.1.2.3:5432/db")


@pytest.mark.asyncio
async def test_rejects_link_local_metadata_host():
    # 169.254.169.254 is the classic cloud-metadata SSRF target.
    with pytest.raises(UnsafeHostError):
        await network_guard.assert_host_is_safe("postgresql://u:p@169.254.169.254:5432/db")


@pytest.mark.asyncio
async def test_allows_public_ip_host():
    await network_guard.assert_host_is_safe("postgresql://u:p@8.8.8.8:5432/db")


@pytest.mark.asyncio
async def test_rejects_missing_host():
    with pytest.raises(UnsafeHostError):
        await network_guard.assert_host_is_safe("not-a-valid-dsn")


@pytest.mark.asyncio
async def test_allow_private_demo_hosts_setting_bypasses_check(monkeypatch):
    monkeypatch.setattr(network_guard.settings, "allow_private_demo_hosts", True)
    await network_guard.assert_host_is_safe("postgresql://u:p@127.0.0.1:5432/db")

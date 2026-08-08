import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit

from app.config import settings


class UnsafeHostError(Exception):
    pass


async def assert_host_is_safe(dsn: str) -> None:
    """Block demo connections into private/internal networks (basic SSRF guard).

    A visitor-supplied connection string makes this server open a TCP
    connection to whatever host they name. Without this check, that's a way
    to probe internal infrastructure or cloud metadata endpoints from the
    server's network position.
    """
    if settings.allow_private_demo_hosts:
        return

    host = urlsplit(dsn).hostname
    if not host:
        raise UnsafeHostError("Connection string is missing a host.")

    try:
        infos = await asyncio.to_thread(socket.getaddrinfo, host, None)
    except socket.gaierror as e:
        raise UnsafeHostError(f"Could not resolve host: {host}") from e

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise UnsafeHostError("Demo connections to private/internal networks aren't allowed.")

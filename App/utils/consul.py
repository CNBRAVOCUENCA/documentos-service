"""Registro de instancias y health checks mediante la API HTTP del agente Consul."""

import ipaddress
import logging
import socket
from urllib.parse import urlsplit

import httpx

from App.config.settings import Settings, settings

logger = logging.getLogger(__name__)


class ConsulRegistration:
    def __init__(self, config: Settings = settings) -> None:
        self.config = config
        self.base_url = self._normalize_addr(config.consul_http_addr)
        self.service_name = config.consul_service_name or config.app_name
        self.hostname = socket.gethostname()
        self.service_id = f"{self.service_name}-{self.hostname}"
        self.headers = {"X-Consul-Token": config.consul_http_token} if config.consul_http_token else {}

    @staticmethod
    def _normalize_addr(addr: str) -> str:
        addr = addr.rstrip("/")
        if addr and "://" not in addr:
            addr = f"http://{addr}"
        return addr

    def _service_address(self) -> str:
        if self.config.consul_service_address:
            return self.config.consul_service_address

        parsed = urlsplit(self.base_url)
        host = parsed.hostname
        if not host:
            raise RuntimeError("Consul address must include a hostname")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)

        try:
            addresses = socket.getaddrinfo(host, port, type=socket.SOCK_DGRAM)
            for family, socktype, proto, _, sockaddr in addresses:
                with socket.socket(family, socktype, proto) as probe:
                    probe.connect(sockaddr)
                    address = probe.getsockname()[0]
                    if address and not ipaddress.ip_address(address).is_loopback:
                        return address
        except OSError:
            raise RuntimeError("Unable to determine this instance's routable address") from None
        raise RuntimeError("Unable to determine this instance's routable address")

    def _payload(self) -> dict:
        address = self._service_address()
        tags = [tag.strip() for tag in self.config.consul_service_tags.split(",") if tag.strip()]
        try:
            is_ipv6 = ipaddress.ip_address(address).version == 6
        except ValueError:
            is_ipv6 = False
        check_address = f"[{address}]" if is_ipv6 else address
        return {
            "ID": self.service_id,
            "Name": self.service_name,
            "Address": address,
            "Port": self.config.consul_service_port,
            "Tags": tags,
            "Check": {
                "HTTP": f"http://{check_address}:{self.config.consul_service_port}/health",
                "Interval": "10s",
                "Timeout": "2s",
                "DeregisterCriticalServiceAfter": "1m",
            },
        }

    async def register(self) -> None:
        if not self.base_url:
            return
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.put(
                    f"{self.base_url}/v1/agent/service/register",
                    json=self._payload(),
                    headers=self.headers,
                )
                response.raise_for_status()
        except Exception as exc:
            logger.error("Consul registration failed (%s)", type(exc).__name__)
            raise RuntimeError("Consul service registration failed") from None

    async def deregister(self) -> None:
        if not self.base_url:
            return
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.put(
                    f"{self.base_url}/v1/agent/service/deregister/{self.service_id}",
                    headers=self.headers,
                )
                response.raise_for_status()
        except Exception as exc:
            logger.error("Consul deregistration failed (%s)", type(exc).__name__)

"""Registro de instancias y health checks mediante la API HTTP del agente Consul."""

import ipaddress
import logging
import socket
from urllib.parse import quote, urlsplit

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
            payload = self._payload()
            await purge_stale_instances(
                self.base_url, self.headers, payload["Address"], payload["Port"], self.service_id
            )
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.put(
                    f"{self.base_url}/v1/agent/service/register",
                    json=payload,
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


async def purge_stale_instances(
    consul_http_addr: str, headers: dict[str, str], address: str, port: int, keep_id: str
) -> int:
    """Da de baja registros viejos que apuntan a la misma IP:puerto que esta instancia.

    Docker reutiliza las IP: si un contenedor anterior no llegó a darse de baja, su
    registro queda en Consul y el health check le pega a ESTE contenedor (misma IP),
    así que nunca falla ni se borra solo. Una IP:puerto identifica a un solo
    contenedor, por eso cualquier otro registro con esa dirección es viejo.
    Un fallo acá no impide el arranque: solo se registra un aviso.
    """
    base = consul_http_addr.strip().rstrip("/")
    if "://" not in base:
        base = f"http://{base}"
    borrados = 0
    try:
        async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
            response = await client.get(f"{base}/v1/agent/services")
            response.raise_for_status()
            for service_id, service in response.json().items():
                if service_id == keep_id:
                    continue
                if service.get("Address") == address and service.get("Port") == port:
                    baja = await client.put(f"{base}/v1/agent/service/deregister/{quote(service_id, safe='')}")
                    baja.raise_for_status()
                    borrados += 1
    except Exception as exc:
        logger.warning("No se pudieron limpiar registros viejos de Consul (%s)", type(exc).__name__)
    return borrados

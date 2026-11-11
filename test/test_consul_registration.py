"""Tests for Consul service registration and lifecycle."""

import socket
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from App.config.settings import Settings
from App.utils.consul import ConsulRegistration


class FakeAsyncClient:
    def __init__(self, *, timeout):
        self.timeout = timeout
        self.put = AsyncMock(return_value=MagicMock())

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None


@pytest.mark.anyio
async def test_register_sends_consul_payload_and_auth_header(monkeypatch):
    client = FakeAsyncClient(timeout=5.0)
    monkeypatch.setattr("App.utils.consul.httpx.AsyncClient", lambda **kwargs: client)
    monkeypatch.setattr("App.utils.consul.socket.gethostname", lambda: "instance-123")
    config = Settings(
        consul_http_addr="consul:8500/",
        consul_http_token="private-token",
        consul_service_name="documents",
        consul_service_port=8123,
        consul_service_tags="traefik.enable=true, team=documents,",
        consul_service_address="10.2.0.4",
    )

    await ConsulRegistration(config).register()

    client.put.assert_awaited_once_with(
        "http://consul:8500/v1/agent/service/register",
        json={
            "ID": "documents-instance-123",
            "Name": "documents",
            "Address": "10.2.0.4",
            "Port": 8123,
            "Tags": ["traefik.enable=true", "team=documents"],
            "Check": {
                "HTTP": "http://10.2.0.4:8123/health",
                "Interval": "10s",
                "Timeout": "2s",
                "DeregisterCriticalServiceAfter": "1m",
            },
        },
        headers={"X-Consul-Token": "private-token"},
    )


@pytest.mark.anyio
async def test_registration_is_disabled_without_consul_address(monkeypatch):
    client_factory = MagicMock()
    monkeypatch.setattr("App.utils.consul.httpx.AsyncClient", client_factory)

    await ConsulRegistration(Settings(consul_http_addr="")).register()
    await ConsulRegistration(Settings(consul_http_addr="")).deregister()

    client_factory.assert_not_called()


def test_service_address_uses_route_to_consul_agent(monkeypatch):
    class ProbeSocket:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def connect(self, address):
            self.remote_address = address

        def getsockname(self):
            return "10.3.0.8", 49152

    probe = ProbeSocket()
    monkeypatch.setattr(
        "App.utils.consul.socket.getaddrinfo",
        lambda host, port, type: [(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP, "", (host, port))],
    )
    monkeypatch.setattr("App.utils.consul.socket.socket", lambda *args: probe)
    registration = ConsulRegistration(Settings(consul_http_addr="http://consul:8500"))

    assert registration._service_address() == "10.3.0.8"
    assert probe.remote_address == ("consul", 8500)


@pytest.mark.anyio
async def test_failed_registration_raises_sanitized_startup_error(monkeypatch, caplog):
    client = FakeAsyncClient(timeout=5.0)
    client.put.side_effect = httpx.ConnectError("request failed")
    monkeypatch.setattr("App.utils.consul.httpx.AsyncClient", lambda **kwargs: client)
    config = Settings(consul_http_addr="http://consul:8500", consul_http_token="private-token")
    monkeypatch.setattr(ConsulRegistration, "_service_address", lambda self: "10.2.0.4")

    with pytest.raises(RuntimeError, match="Consul service registration failed") as error:
        await ConsulRegistration(config).register()

    assert "private-token" not in str(error.value)
    assert "private-token" not in caplog.text


@pytest.mark.anyio
async def test_deregister_failure_is_logged_without_token(monkeypatch, caplog):
    client = FakeAsyncClient(timeout=5.0)
    client.put.side_effect = httpx.ConnectError("private-token")
    monkeypatch.setattr("App.utils.consul.httpx.AsyncClient", lambda **kwargs: client)
    monkeypatch.setattr("App.utils.consul.socket.gethostname", lambda: "replica-42")
    config = Settings(
        consul_http_addr="http://consul:8500",
        consul_http_token="private-token",
        consul_service_address="10.2.0.4",
    )

    await ConsulRegistration(config).deregister()

    client.put.assert_awaited_once_with(
        "http://consul:8500/v1/agent/service/deregister/documentos-service-replica-42",
        headers={"X-Consul-Token": "private-token"},
    )
    assert "Consul deregistration failed" in caplog.text
    assert "private-token" not in caplog.text


@pytest.mark.anyio
async def test_app_lifespan_registers_then_deregisters(monkeypatch):
    from App import main

    registration = MagicMock()
    registration.register = AsyncMock()
    registration.deregister = AsyncMock()
    monkeypatch.setattr(main, "ensure_indexes", lambda: None)
    monkeypatch.setattr(main, "ConsulRegistration", lambda: registration)

    async with main.lifespan(main.app):
        registration.register.assert_awaited_once()
        registration.deregister.assert_not_awaited()

    registration.deregister.assert_awaited_once()


def test_dockerfile_runs_application_as_non_root():
    from pathlib import Path

    dockerfile = Path(__file__).parents[1].joinpath("Dockerfile").read_text()
    instructions = [line.strip() for line in dockerfile.splitlines() if line.strip()]

    assert any(line.startswith("RUN groupadd --system app") for line in instructions)
    assert instructions.index("USER app") > instructions.index("EXPOSE 8000")
    assert instructions[-1].startswith('CMD ["uvicorn"')

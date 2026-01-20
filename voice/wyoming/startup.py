"""
NIGHTWATCH Wyoming Server Startup

Startup configuration and management for Wyoming protocol STT/TTS servers.
Provides integration with the main NIGHTWATCH application lifecycle.

Steps 325-326: Configure Wyoming server startup
Step 321: DGX Spark CUDA acceleration
Step 327: Home Assistant compatibility
Step 328: Wyoming service discovery (mDNS)
"""

from __future__ import annotations

import asyncio
import logging
import socket
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Any

if TYPE_CHECKING:
    from nightwatch.config import VoiceConfig, TTSConfig

logger = logging.getLogger(__name__)


@dataclass
class WyomingServerStatus:
    """Status of Wyoming servers."""
    stt_running: bool = False
    stt_host: str = ""
    stt_port: int = 0
    tts_running: bool = False
    tts_host: str = ""
    tts_port: int = 0
    # Step 327: Home Assistant entity info
    ha_entity_id: str = ""
    ha_friendly_name: str = ""
    # Step 328: Service discovery
    mdns_registered: bool = False


@dataclass
class HomeAssistantEntityInfo:
    """
    Home Assistant entity information for Wyoming integration (Step 327).

    Provides the metadata needed for Home Assistant to discover
    and display NIGHTWATCH voice services.
    """
    entity_id: str
    friendly_name: str
    device_class: str = "voice"
    unique_id: str = ""
    manufacturer: str = "NIGHTWATCH"
    model: str = "Observatory Voice Assistant"
    sw_version: str = "1.0.0"
    supported_features: List[str] = field(default_factory=lambda: [
        "stt", "tts", "intent", "handle"
    ])

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Wyoming info response."""
        return {
            "entity_id": self.entity_id,
            "friendly_name": self.friendly_name,
            "device_class": self.device_class,
            "unique_id": self.unique_id or self.entity_id,
            "device_info": {
                "manufacturer": self.manufacturer,
                "model": self.model,
                "sw_version": self.sw_version,
            },
            "supported_features": self.supported_features,
        }


class WyomingServiceDiscovery:
    """
    mDNS service discovery for Wyoming protocol (Step 328).

    Advertises NIGHTWATCH Wyoming services via Zeroconf/mDNS,
    allowing automatic discovery by Home Assistant and other
    Wyoming-compatible systems.

    Usage:
        discovery = WyomingServiceDiscovery()
        await discovery.register_stt_service("192.168.1.100", 10300)
        await discovery.register_tts_service("192.168.1.100", 10400)
    """

    SERVICE_TYPE_STT = "_wyoming-stt._tcp.local."
    SERVICE_TYPE_TTS = "_wyoming-tts._tcp.local."

    def __init__(self, instance_name: str = "NIGHTWATCH"):
        """
        Initialize service discovery.

        Args:
            instance_name: Service instance name prefix
        """
        self.instance_name = instance_name
        self._zeroconf = None
        self._services: List[Any] = []
        self._loaded = False

    async def _ensure_loaded(self) -> bool:
        """Lazily load zeroconf."""
        if self._loaded:
            return self._zeroconf is not None

        try:
            from zeroconf import Zeroconf
            self._zeroconf = Zeroconf()
            self._loaded = True
            logger.info("Zeroconf initialized for service discovery")
            return True
        except ImportError:
            logger.warning("zeroconf not installed, service discovery disabled")
            self._loaded = True
            return False

    async def register_stt_service(
        self,
        host: str,
        port: int,
        properties: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Register STT service via mDNS (Step 328).

        Args:
            host: Service host IP
            port: Service port
            properties: Additional service properties

        Returns:
            True if registration succeeded
        """
        if not await self._ensure_loaded():
            return False

        try:
            from zeroconf import ServiceInfo

            props = {
                "version": "1",
                "model": "faster-whisper",
                "languages": "en",
                **(properties or {})
            }

            # Resolve host to IP if needed
            ip_addr = socket.gethostbyname(host) if host != "0.0.0.0" else self._get_local_ip()

            service_info = ServiceInfo(
                self.SERVICE_TYPE_STT,
                f"{self.instance_name} STT.{self.SERVICE_TYPE_STT}",
                addresses=[socket.inet_aton(ip_addr)],
                port=port,
                properties=props,
                server=f"{self.instance_name.lower()}-stt.local.",
            )

            self._zeroconf.register_service(service_info)
            self._services.append(service_info)
            logger.info(f"Registered STT service on {ip_addr}:{port}")
            return True

        except Exception as e:
            logger.error(f"Failed to register STT service: {e}")
            return False

    async def register_tts_service(
        self,
        host: str,
        port: int,
        properties: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Register TTS service via mDNS (Step 328).

        Args:
            host: Service host IP
            port: Service port
            properties: Additional service properties

        Returns:
            True if registration succeeded
        """
        if not await self._ensure_loaded():
            return False

        try:
            from zeroconf import ServiceInfo

            props = {
                "version": "1",
                "model": "piper",
                "languages": "en",
                **(properties or {})
            }

            ip_addr = socket.gethostbyname(host) if host != "0.0.0.0" else self._get_local_ip()

            service_info = ServiceInfo(
                self.SERVICE_TYPE_TTS,
                f"{self.instance_name} TTS.{self.SERVICE_TYPE_TTS}",
                addresses=[socket.inet_aton(ip_addr)],
                port=port,
                properties=props,
                server=f"{self.instance_name.lower()}-tts.local.",
            )

            self._zeroconf.register_service(service_info)
            self._services.append(service_info)
            logger.info(f"Registered TTS service on {ip_addr}:{port}")
            return True

        except Exception as e:
            logger.error(f"Failed to register TTS service: {e}")
            return False

    def _get_local_ip(self) -> str:
        """Get local IP address for service registration."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    async def unregister_all(self):
        """Unregister all services."""
        if self._zeroconf is None:
            return

        for service_info in self._services:
            try:
                self._zeroconf.unregister_service(service_info)
            except Exception as e:
                logger.warning(f"Failed to unregister service: {e}")

        self._services.clear()
        logger.info("All mDNS services unregistered")

    async def close(self):
        """Close service discovery."""
        await self.unregister_all()
        if self._zeroconf:
            self._zeroconf.close()
            self._zeroconf = None


class WyomingManager:
    """
    Manages Wyoming protocol STT and TTS server lifecycle.

    Handles startup, shutdown, and health monitoring of Wyoming servers
    for voice pipeline integration.

    Steps 325-326: Wyoming server startup configuration
    Step 321: CUDA acceleration for TTS
    Step 327: Home Assistant compatibility
    Step 328: Wyoming service discovery
    """

    def __init__(
        self,
        voice_config: Optional["VoiceConfig"] = None,
        tts_config: Optional["TTSConfig"] = None,
        enable_discovery: bool = True,
        ha_entity_id: str = "voice_assistant.nightwatch",
        ha_friendly_name: str = "NIGHTWATCH Observatory",
    ):
        """
        Initialize Wyoming manager.

        Args:
            voice_config: STT/voice configuration
            tts_config: TTS configuration
            enable_discovery: Enable mDNS service discovery (Step 328)
            ha_entity_id: Home Assistant entity ID (Step 327)
            ha_friendly_name: Home Assistant friendly name (Step 327)
        """
        self._voice_config = voice_config
        self._tts_config = tts_config
        self._stt_server = None
        self._tts_server = None
        self._stt_task: Optional[asyncio.Task] = None
        self._tts_task: Optional[asyncio.Task] = None

        # Step 327: Home Assistant entity info
        self._ha_entity_info = HomeAssistantEntityInfo(
            entity_id=ha_entity_id,
            friendly_name=ha_friendly_name,
        )

        # Step 328: Service discovery
        self._enable_discovery = enable_discovery
        self._service_discovery: Optional[WyomingServiceDiscovery] = None
        if enable_discovery:
            self._service_discovery = WyomingServiceDiscovery("NIGHTWATCH")

    async def start_stt_server(self) -> bool:
        """
        Start Wyoming STT server (Step 325).

        Returns:
            True if server started successfully
        """
        if self._voice_config is None:
            logger.warning("Voice config not provided, cannot start STT server")
            return False

        if not self._voice_config.enabled:
            logger.info("Voice input disabled, skipping STT server")
            return False

        if not self._voice_config.wyoming_enabled:
            logger.info("Wyoming STT server disabled in config")
            return False

        try:
            from .stt_server import WyomingSTTServer

            # Create STT server with config
            self._stt_server = WyomingSTTServer(
                host=self._voice_config.wyoming_host,
                port=self._voice_config.wyoming_port,
                confidence_threshold=self._voice_config.confidence_threshold,
            )

            # Start in background
            await self._stt_server.start_background()

            logger.info(
                f"Wyoming STT server started on "
                f"{self._voice_config.wyoming_host}:{self._voice_config.wyoming_port}"
            )
            return True

        except ImportError as e:
            logger.error(f"Failed to import STT server: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to start Wyoming STT server: {e}")
            return False

    async def start_tts_server(self) -> bool:
        """
        Start Wyoming TTS server with CUDA acceleration (Steps 321, 326).

        Returns:
            True if server started successfully
        """
        if self._tts_config is None:
            logger.warning("TTS config not provided, cannot start TTS server")
            return False

        if not self._tts_config.enabled:
            logger.info("Voice output disabled, skipping TTS server")
            return False

        if not self._tts_config.wyoming_enabled:
            logger.info("Wyoming TTS server disabled in config")
            return False

        try:
            from .tts_server import WyomingTTSServer

            # Configure CUDA if enabled (Step 321)
            use_cuda = self._tts_config.use_cuda
            if use_cuda:
                try:
                    import torch
                    if torch.cuda.is_available():
                        # Set CUDA device
                        device_id = self._tts_config.cuda_device
                        if device_id < torch.cuda.device_count():
                            torch.cuda.set_device(device_id)
                            logger.info(
                                f"CUDA device {device_id} configured for TTS "
                                f"({torch.cuda.get_device_name(device_id)})"
                            )

                            # Set memory fraction
                            if hasattr(torch.cuda, 'set_per_process_memory_fraction'):
                                torch.cuda.set_per_process_memory_fraction(
                                    self._tts_config.cuda_memory_fraction,
                                    device_id
                                )
                        else:
                            logger.warning(
                                f"CUDA device {device_id} not available, "
                                f"using device 0"
                            )
                    else:
                        logger.warning("CUDA not available, using CPU for TTS")
                        use_cuda = False
                except ImportError:
                    logger.warning("PyTorch not available, using CPU for TTS")
                    use_cuda = False

            # Create TTS server
            self._tts_server = WyomingTTSServer(
                host=self._tts_config.wyoming_host,
                port=self._tts_config.wyoming_port,
            )

            # Start in background
            await self._tts_server.start_background()

            cuda_status = "with CUDA" if use_cuda else "CPU only"
            logger.info(
                f"Wyoming TTS server started on "
                f"{self._tts_config.wyoming_host}:{self._tts_config.wyoming_port} "
                f"({cuda_status})"
            )
            return True

        except ImportError as e:
            logger.error(f"Failed to import TTS server: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to start Wyoming TTS server: {e}")
            return False

    async def start_all(self) -> WyomingServerStatus:
        """
        Start all configured Wyoming servers.

        Returns:
            Status of all servers
        """
        status = WyomingServerStatus()

        # Start STT server
        if await self.start_stt_server():
            status.stt_running = True
            status.stt_host = self._voice_config.wyoming_host
            status.stt_port = self._voice_config.wyoming_port

            # Step 328: Register STT service via mDNS
            if self._service_discovery:
                await self._service_discovery.register_stt_service(
                    status.stt_host,
                    status.stt_port
                )

        # Start TTS server
        if await self.start_tts_server():
            status.tts_running = True
            status.tts_host = self._tts_config.wyoming_host
            status.tts_port = self._tts_config.wyoming_port

            # Step 328: Register TTS service via mDNS
            if self._service_discovery:
                await self._service_discovery.register_tts_service(
                    status.tts_host,
                    status.tts_port
                )

        # Step 327: Add Home Assistant entity info
        if status.stt_running or status.tts_running:
            status.ha_entity_id = self._ha_entity_info.entity_id
            status.ha_friendly_name = self._ha_entity_info.friendly_name
            status.mdns_registered = self._service_discovery is not None

        return status

    async def stop_all(self) -> None:
        """Stop all Wyoming servers."""
        # Step 328: Unregister mDNS services
        if self._service_discovery:
            await self._service_discovery.close()

        if self._stt_server is not None:
            self._stt_server.stop()
            self._stt_server = None
            logger.info("Wyoming STT server stopped")

        if self._tts_server is not None:
            self._tts_server.stop()
            self._tts_server = None
            logger.info("Wyoming TTS server stopped")

    def get_status(self) -> WyomingServerStatus:
        """Get current server status."""
        status = WyomingServerStatus()

        if self._stt_server is not None and self._voice_config:
            status.stt_running = True
            status.stt_host = self._voice_config.wyoming_host
            status.stt_port = self._voice_config.wyoming_port

        if self._tts_server is not None and self._tts_config:
            status.tts_running = True
            status.tts_host = self._tts_config.wyoming_host
            status.tts_port = self._tts_config.wyoming_port

        return status

    @property
    def stt_server(self):
        """Get STT server instance."""
        return self._stt_server

    @property
    def tts_server(self):
        """Get TTS server instance."""
        return self._tts_server

    @property
    def ha_entity_info(self) -> HomeAssistantEntityInfo:
        """Get Home Assistant entity info (Step 327)."""
        return self._ha_entity_info

    def get_ha_info_dict(self) -> Dict[str, Any]:
        """
        Get Home Assistant info as dictionary (Step 327).

        Returns:
            Dictionary suitable for Wyoming INFO response
        """
        return self._ha_entity_info.to_dict()


async def start_wyoming_servers(
    voice_config: Optional["VoiceConfig"] = None,
    tts_config: Optional["TTSConfig"] = None,
) -> WyomingManager:
    """
    Convenience function to start Wyoming servers.

    Args:
        voice_config: STT configuration
        tts_config: TTS configuration

    Returns:
        WyomingManager instance with running servers
    """
    manager = WyomingManager(voice_config, tts_config)
    await manager.start_all()
    return manager


# Export for easy imports
__all__ = [
    "WyomingManager",
    "WyomingServerStatus",
    "HomeAssistantEntityInfo",
    "WyomingServiceDiscovery",
    "start_wyoming_servers",
]

"""
NIGHTWATCH Wyoming Server Startup

Startup configuration and management for Wyoming protocol STT/TTS servers.
Provides integration with the main NIGHTWATCH application lifecycle.

Steps 325-326: Configure Wyoming server startup
Step 321: DGX Spark CUDA acceleration
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

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


class WyomingManager:
    """
    Manages Wyoming protocol STT and TTS server lifecycle.

    Handles startup, shutdown, and health monitoring of Wyoming servers
    for voice pipeline integration.

    Steps 325-326: Wyoming server startup configuration
    Step 321: CUDA acceleration for TTS
    """

    def __init__(
        self,
        voice_config: Optional["VoiceConfig"] = None,
        tts_config: Optional["TTSConfig"] = None,
    ):
        """
        Initialize Wyoming manager.

        Args:
            voice_config: STT/voice configuration
            tts_config: TTS configuration
        """
        self._voice_config = voice_config
        self._tts_config = tts_config
        self._stt_server = None
        self._tts_server = None
        self._stt_task: Optional[asyncio.Task] = None
        self._tts_task: Optional[asyncio.Task] = None

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

        # Start TTS server
        if await self.start_tts_server():
            status.tts_running = True
            status.tts_host = self._tts_config.wyoming_host
            status.tts_port = self._tts_config.wyoming_port

        return status

    async def stop_all(self) -> None:
        """Stop all Wyoming servers."""
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
    "start_wyoming_servers",
]

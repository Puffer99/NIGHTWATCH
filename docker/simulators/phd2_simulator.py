#!/usr/bin/env python3
"""
PHD2 Guiding Simulator (Steps 508-509)

Simulates the PHD2 (Push Here Dummy 2) autoguiding software
JSON-RPC interface for testing guiding integration.

Protocol Reference:
- JSON-RPC over TCP on port 4400
- Event-based notifications
- Methods: get_app_state, get_star_image, guide, dither, etc.

Usage:
    python phd2_simulator.py [--port 4400]
"""

import asyncio
import json
import logging
import os
import random
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("phd2_simulator")


@dataclass
class GuideState:
    """Current state of simulated guider."""
    # Application state
    app_state: str = "Stopped"  # Stopped, Selected, Calibrating, Guiding, LostLock
    connected: bool = True

    # Star tracking
    star_selected: bool = False
    star_x: float = 512.0
    star_y: float = 384.0
    star_snr: float = 15.0  # Signal to noise ratio

    # Guiding stats
    rms_ra: float = 0.0
    rms_dec: float = 0.0
    rms_total: float = 0.0
    guide_step: int = 0

    # Dithering
    is_dithering: bool = False
    dither_dx: float = 0.0
    dither_dy: float = 0.0
    settling: bool = False
    settle_distance: float = 0.0

    # Equipment
    camera_connected: bool = True
    mount_connected: bool = True
    exposure_ms: int = 2000


class PHD2Simulator:
    """
    Simulates PHD2 JSON-RPC interface.

    Supported methods:
    - get_app_state: Current guiding state
    - get_star_image: Current star position
    - get_guide_stats: Guiding RMS statistics
    - guide: Start/stop guiding
    - dither: Execute dither command
    - loop: Start/stop looping exposures
    - find_star: Auto-select guide star
    - set_connected: Connect/disconnect equipment
    """

    def __init__(self, port: int = 4400):
        self.port = port
        self.state = GuideState()
        self._running = False
        self._clients: List[asyncio.StreamWriter] = []
        self._guide_task: Optional[asyncio.Task] = None
        self._last_event_id = 0

    def _next_event_id(self) -> int:
        """Get next event ID."""
        self._last_event_id += 1
        return self._last_event_id

    def _make_response(self, id: Any, result: Any = None,
                       error: Dict = None) -> bytes:
        """Create JSON-RPC response."""
        response = {"jsonrpc": "2.0", "id": id}
        if error:
            response["error"] = error
        else:
            response["result"] = result
        return (json.dumps(response) + "\r\n").encode()

    def _make_event(self, event: str, **params) -> bytes:
        """Create PHD2 event notification."""
        msg = {
            "Event": event,
            "Timestamp": time.time(),
            "Host": "NIGHTWATCH-PHD2-Sim",
            "Inst": 1,
            **params
        }
        return (json.dumps(msg) + "\r\n").encode()

    async def _broadcast_event(self, event: str, **params):
        """Broadcast event to all connected clients."""
        msg = self._make_event(event, **params)
        for writer in self._clients:
            try:
                writer.write(msg)
                await writer.drain()
            except Exception:
                pass

    async def _guide_loop(self):
        """Simulate guiding corrections."""
        while self.state.app_state == "Guiding":
            # Simulate guide frame
            self.state.guide_step += 1

            # Simulate tracking error with random walk
            error_ra = random.gauss(0, 0.5)
            error_dec = random.gauss(0, 0.3)

            # Update RMS (exponential moving average)
            alpha = 0.1
            self.state.rms_ra = (1 - alpha) * self.state.rms_ra + alpha * abs(error_ra)
            self.state.rms_dec = (1 - alpha) * self.state.rms_dec + alpha * abs(error_dec)
            self.state.rms_total = (self.state.rms_ra**2 + self.state.rms_dec**2)**0.5

            # Update star position with error
            self.state.star_x += error_ra * 0.1  # Arcsec to pixels
            self.state.star_y += error_dec * 0.1

            # Broadcast guide step event
            await self._broadcast_event(
                "GuideStep",
                Frame=self.state.guide_step,
                dx=error_ra,
                dy=error_dec,
                RADistanceRaw=error_ra,
                DECDistanceRaw=error_dec,
                RADuration=int(abs(error_ra) * 100),
                DECDuration=int(abs(error_dec) * 100),
                StarMass=1000.0,
                SNR=self.state.star_snr
            )

            await asyncio.sleep(self.state.exposure_ms / 1000)

    async def _settle_loop(self, pixels: float, time_limit: float):
        """Simulate settling after dither."""
        start = time.time()
        self.state.settling = True
        self.state.settle_distance = pixels

        while self.state.settle_distance > 0.5:
            if time.time() - start > time_limit:
                # Timeout
                self.state.settling = False
                await self._broadcast_event("SettleDone", Status=1,
                                           Error="Settle timeout")
                return

            # Gradually reduce distance
            self.state.settle_distance *= 0.7
            await self._broadcast_event("Settling",
                                       Distance=self.state.settle_distance)
            await asyncio.sleep(0.5)

        self.state.settling = False
        self.state.is_dithering = False
        await self._broadcast_event("SettleDone", Status=0)

    def process_request(self, request: Dict) -> bytes:
        """Process a JSON-RPC request."""
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id")

        logger.debug(f"Processing method: {method}")

        # Method handlers
        if method == "get_app_state":
            return self._make_response(req_id, self.state.app_state)

        elif method == "get_connected":
            return self._make_response(req_id, self.state.connected)

        elif method == "set_connected":
            self.state.connected = params.get("connected", True)
            return self._make_response(req_id, 0)

        elif method == "get_star_image":
            if not self.state.star_selected:
                return self._make_response(req_id, None)
            return self._make_response(req_id, {
                "StarPos": [self.state.star_x, self.state.star_y],
                "SNR": self.state.star_snr,
                "HFD": 3.5
            })

        elif method == "get_guide_stats":
            return self._make_response(req_id, {
                "rms_ra": self.state.rms_ra,
                "rms_dec": self.state.rms_dec,
                "rms_tot": self.state.rms_total,
                "peak_ra": self.state.rms_ra * 2,
                "peak_dec": self.state.rms_dec * 2
            })

        elif method == "guide":
            # Start guiding
            if not self.state.star_selected:
                return self._make_response(req_id, error={
                    "code": 1,
                    "message": "No star selected"
                })

            self.state.app_state = "Guiding"
            self.state.rms_ra = 0.3
            self.state.rms_dec = 0.2
            self.state.rms_total = 0.36

            # Start guide loop
            if self._guide_task:
                self._guide_task.cancel()
            self._guide_task = asyncio.create_task(self._guide_loop())

            return self._make_response(req_id, 0)

        elif method == "stop_capture":
            if self._guide_task:
                self._guide_task.cancel()
                self._guide_task = None
            self.state.app_state = "Stopped"
            return self._make_response(req_id, 0)

        elif method == "loop":
            # Start looping (exposing without guiding)
            self.state.app_state = "Looping"
            return self._make_response(req_id, 0)

        elif method == "find_star":
            # Auto-select guide star
            self.state.star_selected = True
            self.state.star_x = 512 + random.uniform(-100, 100)
            self.state.star_y = 384 + random.uniform(-100, 100)
            self.state.star_snr = 15 + random.uniform(0, 10)
            self.state.app_state = "Selected"
            return self._make_response(req_id, 0)

        elif method == "dither":
            # Dither command
            if self.state.app_state != "Guiding":
                return self._make_response(req_id, error={
                    "code": 2,
                    "message": "Not guiding"
                })

            pixels = params.get("amount", 5.0)
            ra_only = params.get("raOnly", False)
            settle_pixels = params.get("settle", {}).get("pixels", 1.5)
            settle_time = params.get("settle", {}).get("time", 10.0)
            settle_timeout = params.get("settle", {}).get("timeout", 40.0)

            self.state.is_dithering = True
            self.state.dither_dx = random.uniform(-pixels, pixels)
            self.state.dither_dy = 0 if ra_only else random.uniform(-pixels, pixels)

            # Apply dither offset
            self.state.star_x += self.state.dither_dx
            self.state.star_y += self.state.dither_dy

            # Start settling
            asyncio.create_task(self._settle_loop(
                (self.state.dither_dx**2 + self.state.dither_dy**2)**0.5,
                settle_timeout
            ))

            return self._make_response(req_id, 0)

        elif method == "set_exposure":
            self.state.exposure_ms = params.get("exposure", 2000)
            return self._make_response(req_id, 0)

        elif method == "get_exposure":
            return self._make_response(req_id, self.state.exposure_ms)

        elif method == "get_camera_connected":
            return self._make_response(req_id, self.state.camera_connected)

        elif method == "get_telescope_connected":
            return self._make_response(req_id, self.state.mount_connected)

        elif method == "get_calibrated":
            return self._make_response(req_id, True)

        elif method == "get_profiles":
            return self._make_response(req_id, [
                {"id": 1, "name": "Simulator Profile"}
            ])

        elif method == "get_current_equipment":
            return self._make_response(req_id, {
                "camera": {"name": "Simulator Camera", "connected": True},
                "mount": {"name": "Simulator Mount", "connected": True}
            })

        # Unknown method
        return self._make_response(req_id, error={
            "code": -32601,
            "message": f"Method not found: {method}"
        })

    async def handle_client(self, reader: asyncio.StreamReader,
                           writer: asyncio.StreamWriter):
        """Handle a client connection."""
        addr = writer.get_extra_info('peername')
        logger.info(f"Client connected: {addr}")
        self._clients.append(writer)

        # Send initial state event
        writer.write(self._make_event("AppState", State=self.state.app_state))
        await writer.drain()

        try:
            buffer = ""
            while True:
                data = await asyncio.wait_for(
                    reader.read(4096),
                    timeout=300.0
                )
                if not data:
                    break

                buffer += data.decode()

                # Process complete JSON messages
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        request = json.loads(line)
                        response = self.process_request(request)
                        writer.write(response)
                        await writer.drain()
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e}")

        except asyncio.TimeoutError:
            logger.debug(f"Client timeout: {addr}")
        except Exception as e:
            logger.error(f"Client error: {e}")
        finally:
            self._clients.remove(writer)
            writer.close()
            await writer.wait_closed()
            logger.info(f"Client disconnected: {addr}")

    async def run(self):
        """Start the simulator server."""
        self._running = True
        server = await asyncio.start_server(
            self.handle_client,
            '0.0.0.0',
            self.port
        )

        addr = server.sockets[0].getsockname()
        logger.info(f"PHD2 simulator listening on {addr}")
        logger.info("JSON-RPC interface ready")

        async with server:
            await server.serve_forever()


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='PHD2 Guiding Simulator'
    )
    parser.add_argument(
        '--port', type=int,
        default=int(os.environ.get('PHD2_SIM_PORT', '4400')),
        help='TCP port to listen on (default: 4400)'
    )
    args = parser.parse_args()

    simulator = PHD2Simulator(port=args.port)
    await simulator.run()


if __name__ == "__main__":
    asyncio.run(main())

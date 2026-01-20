#!/usr/bin/env python3
"""
AAG CloudWatcher Serial Protocol Simulator (Steps 506-507)

Simulates the AAG CloudWatcher Solo cloud sensor for testing.
Implements the CloudWatcher serial protocol over TCP (socat bridge).

Protocol Reference:
- Commands are single characters or short strings
- Responses follow AAG format with checksums
- Key readings: cloud temperature, ambient temp, rain sensor, brightness

Usage:
    python cloud_simulator.py [--port 8081] [--serial-port /dev/pts/X]
"""

import asyncio
import logging
import os
import random
import struct
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("cloud_simulator")


@dataclass
class CloudSensorState:
    """Current state of simulated cloud sensor."""
    # Sky temperature (infrared) - key cloud indicator
    sky_temperature: float = -25.0  # Clear sky is very cold
    ambient_temperature: float = 55.0  # Fahrenheit

    # Rain sensor (capacitive)
    rain_frequency: int = 2300  # Dry = ~2300, wet = lower
    is_raining: bool = False

    # Light sensor
    brightness: int = 1  # 1 = dark, higher = brighter

    # Internal state
    heater_pwm: int = 0  # 0-100%
    switch_status: int = 1  # 1 = safe, 0 = unsafe

    # Device info
    firmware_version: str = "5.88"
    serial_number: str = "NWSIM001"


class CloudWatcherSimulator:
    """
    Simulates AAG CloudWatcher Solo serial protocol.

    Protocol commands:
    - 'A' - Get ambient temperature
    - 'C' - Get cloud/sky temperature
    - 'E' - Get rain sensor frequency
    - 'K' - Get switch status
    - 'D' - Get brightness
    - 'Q' - Get all sensor data
    - 'v' - Get firmware version
    - 'Z' - Zero rain sensor
    """

    def __init__(self, port: int = 8081):
        self.port = port
        self.state = CloudSensorState()
        self._running = False
        self._last_update = time.time()
        self._rain_event_until: Optional[float] = None
        self._cloud_event_until: Optional[float] = None

        # Configuration from environment
        self.state.ambient_temperature = float(os.environ.get(
            'CLOUD_SIM_TEMP_F', '55.0'))
        self.state.sky_temperature = float(os.environ.get(
            'CLOUD_SIM_SKY_TEMP', '-25.0'))
        self.events_enabled = os.environ.get(
            'CLOUD_SIM_EVENTS_ENABLED', 'false').lower() == 'true'

    def _calculate_checksum(self, data: bytes) -> int:
        """Calculate CloudWatcher checksum."""
        return sum(data) & 0xFF

    def _format_response(self, code: str, values: list) -> bytes:
        """Format response in CloudWatcher protocol."""
        # Format: !code value1 value2 ... checksum
        value_str = ' '.join(str(v) for v in values)
        response = f"!{code} {value_str}"
        checksum = self._calculate_checksum(response.encode())
        return f"{response} {checksum:02X}\r\n".encode()

    def _update_simulation(self):
        """Update simulated sensor values."""
        now = time.time()
        elapsed = now - self._last_update
        self._last_update = now

        # Diurnal temperature variation
        hour = datetime.now().hour
        # Coldest around 5am, warmest around 3pm
        temp_offset = 10 * (1 - abs(hour - 15) / 12)
        base_temp = float(os.environ.get('CLOUD_SIM_TEMP_F', '55.0'))
        self.state.ambient_temperature = base_temp + temp_offset + random.gauss(0, 0.5)

        # Sky temperature varies with clouds
        if self._cloud_event_until and now < self._cloud_event_until:
            # Cloudy - sky temp closer to ambient
            self.state.sky_temperature = self.state.ambient_temperature - 15 + random.gauss(0, 2)
        else:
            # Clear - sky is cold
            self.state.sky_temperature = -25 + random.gauss(0, 3)
            self._cloud_event_until = None

        # Rain events
        if self._rain_event_until and now < self._rain_event_until:
            self.state.is_raining = True
            self.state.rain_frequency = 1500 + random.randint(-200, 200)  # Wet
        else:
            self.state.is_raining = False
            self.state.rain_frequency = 2300 + random.randint(-50, 50)  # Dry
            self._rain_event_until = None

        # Light sensor - dark at night
        if 6 <= hour <= 18:
            self.state.brightness = min(60000, 1000 + (hour - 6) * 5000)
        else:
            self.state.brightness = random.randint(1, 10)  # Dark

        # Random events if enabled
        if self.events_enabled and random.random() < 0.001 * elapsed:
            if random.random() < 0.3:
                # Trigger rain event (5-15 minutes)
                duration = random.uniform(300, 900)
                self._rain_event_until = now + duration
                logger.info(f"Rain event triggered for {duration:.0f}s")
            else:
                # Trigger cloud event (10-30 minutes)
                duration = random.uniform(600, 1800)
                self._cloud_event_until = now + duration
                logger.info(f"Cloud event triggered for {duration:.0f}s")

        # Switch status based on conditions
        # Unsafe if: raining, cloudy (sky temp > -10), or very bright
        cloud_delta = self.state.ambient_temperature - self.state.sky_temperature
        is_cloudy = cloud_delta < 20  # Less than 20°F difference = cloudy
        self.state.switch_status = 0 if (self.state.is_raining or is_cloudy) else 1

    def process_command(self, cmd: bytes) -> bytes:
        """Process a CloudWatcher command and return response."""
        self._update_simulation()

        cmd_str = cmd.decode().strip().upper()

        if not cmd_str:
            return b""

        logger.debug(f"Processing command: {cmd_str}")

        if cmd_str == 'A':
            # Ambient temperature (tenths of degree C)
            temp_c = (self.state.ambient_temperature - 32) * 5 / 9
            return self._format_response('A', [int(temp_c * 10)])

        elif cmd_str == 'C':
            # Sky/cloud temperature (tenths of degree C)
            temp_c = (self.state.sky_temperature - 32) * 5 / 9
            return self._format_response('C', [int(temp_c * 10)])

        elif cmd_str == 'E':
            # Rain sensor frequency
            return self._format_response('E', [self.state.rain_frequency])

        elif cmd_str == 'K':
            # Switch status
            return self._format_response('K', [self.state.switch_status])

        elif cmd_str == 'D':
            # Brightness/daylight
            return self._format_response('D', [self.state.brightness])

        elif cmd_str == 'Q':
            # All sensor data
            temp_c = (self.state.ambient_temperature - 32) * 5 / 9
            sky_c = (self.state.sky_temperature - 32) * 5 / 9
            return self._format_response('Q', [
                int(sky_c * 10),      # Sky temp
                int(temp_c * 10),     # Ambient temp
                self.state.rain_frequency,
                self.state.heater_pwm,
                self.state.brightness,
                self.state.switch_status
            ])

        elif cmd_str == 'V':
            # Firmware version
            return f"!V {self.state.firmware_version}\r\n".encode()

        elif cmd_str == 'Z':
            # Zero/reset rain sensor
            self.state.rain_frequency = 2300
            return b"!Z OK\r\n"

        elif cmd_str.startswith('H'):
            # Set heater PWM (H followed by 0-100)
            try:
                pwm = int(cmd_str[1:])
                self.state.heater_pwm = max(0, min(100, pwm))
                return f"!H {self.state.heater_pwm}\r\n".encode()
            except ValueError:
                pass

        # Unknown command
        return b"!? Unknown\r\n"

    async def handle_client(self, reader: asyncio.StreamReader,
                           writer: asyncio.StreamWriter):
        """Handle a client connection."""
        addr = writer.get_extra_info('peername')
        logger.info(f"Client connected: {addr}")

        try:
            while True:
                # Read command (single character or line)
                data = await asyncio.wait_for(
                    reader.read(100),
                    timeout=60.0
                )
                if not data:
                    break

                response = self.process_command(data)
                if response:
                    writer.write(response)
                    await writer.drain()

        except asyncio.TimeoutError:
            logger.debug(f"Client timeout: {addr}")
        except Exception as e:
            logger.error(f"Client error: {e}")
        finally:
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
        logger.info(f"CloudWatcher simulator listening on {addr}")
        logger.info(f"Events enabled: {self.events_enabled}")

        async with server:
            await server.serve_forever()


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='AAG CloudWatcher Serial Protocol Simulator'
    )
    parser.add_argument(
        '--port', type=int,
        default=int(os.environ.get('CLOUD_SIM_PORT', '8081')),
        help='TCP port to listen on (default: 8081)'
    )
    args = parser.parse_args()

    simulator = CloudWatcherSimulator(port=args.port)
    await simulator.run()


if __name__ == "__main__":
    asyncio.run(main())

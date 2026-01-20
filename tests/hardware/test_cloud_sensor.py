#!/usr/bin/env python3
"""
Cloud Sensor Test (Step 642)

Verifies AAG CloudWatcher communication and sensor readings.
Tests serial/TCP protocol communication and validates sensor data.

Usage:
    python -m tests.hardware.test_cloud_sensor [--host HOST] [--port PORT]
    pytest tests/hardware/test_cloud_sensor.py -v -m hardware

Requirements:
    - AAG CloudWatcher connected via serial or TCP
    - For TCP: Cloud sensor simulator running on specified port
"""

import argparse
import socket
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class CloudSensorReading:
    """Parsed cloud sensor reading."""
    sky_temp_c: Optional[float] = None
    ambient_temp_c: Optional[float] = None
    rain_frequency: Optional[int] = None
    brightness: Optional[int] = None
    switch_status: Optional[int] = None
    heater_pwm: Optional[int] = None


class CloudSensorTest:
    """Test AAG CloudWatcher cloud sensor communication."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8081,
        timeout: float = 5.0,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.results: dict[str, bool] = {}
        self.socket: Optional[socket.socket] = None

    def connect(self) -> bool:
        """Establish TCP connection to cloud sensor."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            return True
        except (socket.error, OSError) as e:
            print(f"  Connection error: {e}")
            return False

    def disconnect(self):
        """Close connection."""
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None

    def send_command(self, cmd: str) -> Optional[str]:
        """Send command and receive response."""
        if not self.socket:
            return None
        try:
            self.socket.sendall(cmd.encode())
            response = self.socket.recv(256).decode().strip()
            return response
        except (socket.error, socket.timeout) as e:
            print(f"  Communication error: {e}")
            return None

    def parse_response(self, response: str) -> tuple[Optional[str], list[str]]:
        """Parse CloudWatcher response format: !CODE value1 value2 ... checksum"""
        if not response or not response.startswith("!"):
            return None, []
        parts = response[1:].split()
        if len(parts) < 2:
            return None, []
        code = parts[0]
        values = parts[1:-1]  # Exclude checksum
        return code, values

    # -------------------------------------------------------------------------
    # Test Methods
    # -------------------------------------------------------------------------

    def test_connection(self) -> bool:
        """Test basic connection to cloud sensor."""
        print("\n[1/7] Testing connection...")
        result = self.connect()
        if result:
            print(f"  ✓ Connected to {self.host}:{self.port}")
        else:
            print(f"  ✗ Failed to connect to {self.host}:{self.port}")
        self.results["connection"] = result
        return result

    def test_ambient_temperature(self) -> bool:
        """Test ambient temperature reading (command A)."""
        print("\n[2/7] Testing ambient temperature...")
        response = self.send_command("A")
        if not response:
            print("  ✗ No response to 'A' command")
            self.results["ambient_temp"] = False
            return False

        code, values = self.parse_response(response)
        if code != "A" or not values:
            print(f"  ✗ Invalid response: {response}")
            self.results["ambient_temp"] = False
            return False

        try:
            temp_tenths = int(values[0])
            temp_c = temp_tenths / 10.0
            temp_f = temp_c * 9 / 5 + 32

            # Validate reasonable range (-40 to 60 C)
            if -40 <= temp_c <= 60:
                print(f"  ✓ Ambient: {temp_c:.1f}°C ({temp_f:.1f}°F)")
                self.results["ambient_temp"] = True
                return True
            else:
                print(f"  ✗ Temperature out of range: {temp_c}°C")
                self.results["ambient_temp"] = False
                return False
        except (ValueError, IndexError) as e:
            print(f"  ✗ Parse error: {e}")
            self.results["ambient_temp"] = False
            return False

    def test_sky_temperature(self) -> bool:
        """Test sky/cloud temperature reading (command C)."""
        print("\n[3/7] Testing sky temperature...")
        response = self.send_command("C")
        if not response:
            print("  ✗ No response to 'C' command")
            self.results["sky_temp"] = False
            return False

        code, values = self.parse_response(response)
        if code != "C" or not values:
            print(f"  ✗ Invalid response: {response}")
            self.results["sky_temp"] = False
            return False

        try:
            temp_tenths = int(values[0])
            temp_c = temp_tenths / 10.0
            temp_f = temp_c * 9 / 5 + 32

            # Sky temp can be very cold (-50 to 30 C typical)
            if -60 <= temp_c <= 40:
                cloud_status = "Clear" if temp_c < -10 else "Cloudy"
                print(f"  ✓ Sky: {temp_c:.1f}°C ({temp_f:.1f}°F) - {cloud_status}")
                self.results["sky_temp"] = True
                return True
            else:
                print(f"  ✗ Temperature out of range: {temp_c}°C")
                self.results["sky_temp"] = False
                return False
        except (ValueError, IndexError) as e:
            print(f"  ✗ Parse error: {e}")
            self.results["sky_temp"] = False
            return False

    def test_rain_sensor(self) -> bool:
        """Test rain sensor reading (command E)."""
        print("\n[4/7] Testing rain sensor...")
        response = self.send_command("E")
        if not response:
            print("  ✗ No response to 'E' command")
            self.results["rain_sensor"] = False
            return False

        code, values = self.parse_response(response)
        if code != "E" or not values:
            print(f"  ✗ Invalid response: {response}")
            self.results["rain_sensor"] = False
            return False

        try:
            frequency = int(values[0])
            # Dry is typically ~2300, wet is lower
            rain_status = "Dry" if frequency > 2000 else "Wet/Rain"
            print(f"  ✓ Rain frequency: {frequency} Hz - {rain_status}")
            self.results["rain_sensor"] = True
            return True
        except (ValueError, IndexError) as e:
            print(f"  ✗ Parse error: {e}")
            self.results["rain_sensor"] = False
            return False

    def test_brightness(self) -> bool:
        """Test brightness/daylight sensor (command D)."""
        print("\n[5/7] Testing brightness sensor...")
        response = self.send_command("D")
        if not response:
            print("  ✗ No response to 'D' command")
            self.results["brightness"] = False
            return False

        code, values = self.parse_response(response)
        if code != "D" or not values:
            print(f"  ✗ Invalid response: {response}")
            self.results["brightness"] = False
            return False

        try:
            brightness = int(values[0])
            if brightness < 100:
                light_status = "Dark (nighttime)"
            elif brightness < 10000:
                light_status = "Dim (twilight)"
            else:
                light_status = "Bright (daylight)"
            print(f"  ✓ Brightness: {brightness} - {light_status}")
            self.results["brightness"] = True
            return True
        except (ValueError, IndexError) as e:
            print(f"  ✗ Parse error: {e}")
            self.results["brightness"] = False
            return False

    def test_switch_status(self) -> bool:
        """Test switch/safety status (command K)."""
        print("\n[6/7] Testing switch status...")
        response = self.send_command("K")
        if not response:
            print("  ✗ No response to 'K' command")
            self.results["switch"] = False
            return False

        code, values = self.parse_response(response)
        if code != "K" or not values:
            print(f"  ✗ Invalid response: {response}")
            self.results["switch"] = False
            return False

        try:
            status = int(values[0])
            status_text = "Safe (open allowed)" if status == 1 else "Unsafe (close required)"
            print(f"  ✓ Switch: {status} - {status_text}")
            self.results["switch"] = True
            return True
        except (ValueError, IndexError) as e:
            print(f"  ✗ Parse error: {e}")
            self.results["switch"] = False
            return False

    def test_all_sensors(self) -> bool:
        """Test combined sensor query (command Q)."""
        print("\n[7/7] Testing combined sensor query...")
        response = self.send_command("Q")
        if not response:
            print("  ✗ No response to 'Q' command")
            self.results["combined"] = False
            return False

        code, values = self.parse_response(response)
        if code != "Q" or len(values) < 5:
            print(f"  ✗ Invalid response: {response}")
            self.results["combined"] = False
            return False

        try:
            reading = CloudSensorReading(
                sky_temp_c=int(values[0]) / 10.0,
                ambient_temp_c=int(values[1]) / 10.0,
                rain_frequency=int(values[2]),
                heater_pwm=int(values[3]),
                brightness=int(values[4]),
                switch_status=int(values[5]) if len(values) > 5 else None,
            )

            print(f"  ✓ Sky temp: {reading.sky_temp_c:.1f}°C")
            print(f"  ✓ Ambient temp: {reading.ambient_temp_c:.1f}°C")
            print(f"  ✓ Rain freq: {reading.rain_frequency} Hz")
            print(f"  ✓ Heater: {reading.heater_pwm}%")
            print(f"  ✓ Brightness: {reading.brightness}")
            if reading.switch_status is not None:
                print(f"  ✓ Switch: {'Safe' if reading.switch_status else 'Unsafe'}")

            self.results["combined"] = True
            return True
        except (ValueError, IndexError) as e:
            print(f"  ✗ Parse error: {e}")
            self.results["combined"] = False
            return False

    def run_all_tests(self) -> bool:
        """Run all cloud sensor tests."""
        print("=" * 60)
        print("AAG CloudWatcher Cloud Sensor Test (Step 642)")
        print("=" * 60)
        print(f"\nTarget: {self.host}:{self.port}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            # Test connection first
            if not self.test_connection():
                return False

            # Run sensor tests
            self.test_ambient_temperature()
            self.test_sky_temperature()
            self.test_rain_sensor()
            self.test_brightness()
            self.test_switch_status()
            self.test_all_sensors()

        finally:
            self.disconnect()

        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        passed = sum(1 for v in self.results.values() if v)
        total = len(self.results)
        print(f"\nPassed: {passed}/{total}")

        for test, result in self.results.items():
            status = "✓" if result else "✗"
            print(f"  {status} {test}")

        all_passed = all(self.results.values())
        print(f"\nOverall: {'PASS' if all_passed else 'FAIL'}")
        return all_passed


def main():
    """Main entry point for cloud sensor test."""
    parser = argparse.ArgumentParser(
        description="AAG CloudWatcher Cloud Sensor Test"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Cloud sensor host (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8081,
        help="Cloud sensor port (default: 8081)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Connection timeout in seconds (default: 5)",
    )
    args = parser.parse_args()

    test = CloudSensorTest(
        host=args.host,
        port=args.port,
        timeout=args.timeout,
    )

    success = test.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

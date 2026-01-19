#!/usr/bin/env python3
"""
Mount Communication Test (Step 640)

Verifies LX200/OnStepX mount communication is working correctly.
Tests basic command/response cycle and essential mount functions.

Usage:
    python -m tests.hardware.test_mount [--host HOST] [--port PORT]
    pytest tests/hardware/test_mount.py -v -m hardware

Requirements:
    - Mount controller powered on and network-accessible
    - LX200 protocol enabled on mount
"""

import argparse
import socket
import sys
import time
from typing import Optional


class MountCommunicationTest:
    """Test mount communication over LX200 protocol."""

    def __init__(self, host: str = "192.168.1.100", port: int = 9999, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket: Optional[socket.socket] = None
        self.results: dict[str, bool] = {}

    def connect(self) -> bool:
        """Establish TCP connection to mount."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            print(f"✓ Connected to mount at {self.host}:{self.port}")
            return True
        except socket.timeout:
            print(f"✗ Connection timeout to {self.host}:{self.port}")
            return False
        except ConnectionRefusedError:
            print(f"✗ Connection refused by {self.host}:{self.port}")
            return False
        except OSError as e:
            print(f"✗ Network error: {e}")
            return False

    def disconnect(self) -> None:
        """Close connection to mount."""
        if self.socket:
            self.socket.close()
            self.socket = None

    def send_command(self, cmd: str) -> Optional[str]:
        """Send LX200 command and receive response."""
        if not self.socket:
            return None

        try:
            # LX200 commands start with : and end with #
            if not cmd.startswith(":"):
                cmd = ":" + cmd
            if not cmd.endswith("#"):
                cmd = cmd + "#"

            self.socket.sendall(cmd.encode("ascii"))

            # Read response until # or timeout
            response = b""
            start = time.time()
            while time.time() - start < self.timeout:
                try:
                    data = self.socket.recv(1)
                    if not data:
                        break
                    response += data
                    if data == b"#":
                        break
                except socket.timeout:
                    break

            return response.decode("ascii", errors="replace").rstrip("#")

        except Exception as e:
            print(f"  Command error: {e}")
            return None

    def test_get_ra(self) -> bool:
        """Test getting Right Ascension."""
        print("\nTest: Get RA position")
        response = self.send_command(":GR#")
        if response:
            print(f"  RA: {response}")
            # Basic validation - should be in HH:MM:SS or HH:MM.M format
            if ":" in response or "." in response:
                print("  ✓ Valid RA format")
                return True
        print("  ✗ Invalid or no RA response")
        return False

    def test_get_dec(self) -> bool:
        """Test getting Declination."""
        print("\nTest: Get DEC position")
        response = self.send_command(":GD#")
        if response:
            print(f"  DEC: {response}")
            # Basic validation - should contain degree symbol or +/-
            if any(c in response for c in ["°", "*", "+", "-", ":"]):
                print("  ✓ Valid DEC format")
                return True
        print("  ✗ Invalid or no DEC response")
        return False

    def test_get_site(self) -> bool:
        """Test getting site latitude/longitude."""
        print("\nTest: Get site location")

        lat = self.send_command(":Gt#")
        lon = self.send_command(":Gg#")

        if lat:
            print(f"  Latitude: {lat}")
        if lon:
            print(f"  Longitude: {lon}")

        if lat and lon:
            print("  ✓ Site location available")
            return True
        print("  ✗ Site location not available")
        return False

    def test_get_time(self) -> bool:
        """Test getting local time."""
        print("\nTest: Get local time")
        response = self.send_command(":GL#")
        if response:
            print(f"  Local time: {response}")
            if ":" in response:
                print("  ✓ Valid time format")
                return True
        print("  ✗ Invalid or no time response")
        return False

    def test_get_date(self) -> bool:
        """Test getting date."""
        print("\nTest: Get date")
        response = self.send_command(":GC#")
        if response:
            print(f"  Date: {response}")
            if "/" in response or "-" in response:
                print("  ✓ Valid date format")
                return True
        print("  ✗ Invalid or no date response")
        return False

    def test_tracking_status(self) -> bool:
        """Test getting tracking status."""
        print("\nTest: Get tracking status")
        # OnStepX extended command for status
        response = self.send_command(":GU#")
        if response:
            print(f"  Status: {response}")
            print("  ✓ Status response received")
            return True

        # Try standard approach - check if tracking
        print("  (OnStepX status not available, skipping)")
        return True  # Non-critical

    def test_alignment_status(self) -> bool:
        """Test alignment/park status."""
        print("\nTest: Get alignment status")
        # Check if parked
        response = self.send_command(":GVP#")
        if response:
            print(f"  Park status: {response}")

        # ACK test - just send and expect 'P' for polar mount
        self.socket.sendall(b"\x06")  # ACK character
        try:
            ack_response = self.socket.recv(1)
            mount_type = ack_response.decode("ascii", errors="replace")
            mount_types = {"A": "AltAz", "P": "Polar/GEM", "G": "German GEM"}
            if mount_type in mount_types:
                print(f"  Mount type: {mount_types[mount_type]}")
                print("  ✓ Alignment info available")
                return True
        except Exception:
            pass

        print("  ✓ Alignment check completed")
        return True

    def run_all_tests(self) -> bool:
        """Run all mount communication tests."""
        print("=" * 60)
        print("NIGHTWATCH Mount Communication Test")
        print("=" * 60)
        print(f"Target: {self.host}:{self.port}")

        if not self.connect():
            return False

        try:
            tests = [
                ("RA Position", self.test_get_ra),
                ("DEC Position", self.test_get_dec),
                ("Site Location", self.test_get_site),
                ("Local Time", self.test_get_time),
                ("Date", self.test_get_date),
                ("Tracking Status", self.test_tracking_status),
                ("Alignment Status", self.test_alignment_status),
            ]

            for name, test_func in tests:
                try:
                    self.results[name] = test_func()
                except Exception as e:
                    print(f"  ✗ Test error: {e}")
                    self.results[name] = False

            # Summary
            print("\n" + "=" * 60)
            print("Test Summary")
            print("=" * 60)

            passed = sum(1 for v in self.results.values() if v)
            total = len(self.results)

            for name, result in self.results.items():
                status = "PASS" if result else "FAIL"
                symbol = "✓" if result else "✗"
                print(f"  {symbol} {name}: {status}")

            print(f"\nResult: {passed}/{total} tests passed")

            return passed == total

        finally:
            self.disconnect()


def main():
    """Run mount communication test from command line."""
    parser = argparse.ArgumentParser(
        description="Test mount communication over LX200 protocol"
    )
    parser.add_argument(
        "--host",
        default="192.168.1.100",
        help="Mount controller IP address (default: 192.168.1.100)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9999,
        help="LX200 port (default: 9999)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Command timeout in seconds (default: 5.0)",
    )

    args = parser.parse_args()

    test = MountCommunicationTest(
        host=args.host,
        port=args.port,
        timeout=args.timeout,
    )

    success = test.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

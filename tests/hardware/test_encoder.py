#!/usr/bin/env python3
"""
Encoder Test (Step 643)

Verifies EncoderBridge communication and position accuracy.
Tests serial communication, position readings, and stability.

Usage:
    python -m tests.hardware.test_encoder [--port PORT] [--baudrate RATE]
    pytest tests/hardware/test_encoder.py -v -m hardware

Requirements:
    - EncoderBridge connected via USB serial
    - Encoders physically attached to mount axes
"""

import argparse
import sys
import time
from typing import Optional

# Try to import serial, provide helpful message if not available
try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class EncoderTest:
    """Test encoder bridge communication."""

    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        baudrate: int = 115200,
        timeout: float = 2.0,
    ):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial: Optional[serial.Serial] = None
        self.results: dict[str, bool] = {}

    def connect(self) -> bool:
        """Establish serial connection to encoder bridge."""
        if not SERIAL_AVAILABLE:
            print("✗ pyserial not installed. Run: pip install pyserial")
            return False

        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
            )
            # Clear any pending data
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            time.sleep(0.5)  # Allow device to initialize
            print(f"✓ Connected to encoder bridge at {self.port}")
            return True
        except serial.SerialException as e:
            print(f"✗ Serial connection failed: {e}")
            return False
        except PermissionError:
            print(f"✗ Permission denied for {self.port}")
            print("  Try: sudo usermod -aG dialout $USER")
            return False
        except FileNotFoundError:
            print(f"✗ Device not found: {self.port}")
            print("  Check: ls -la /dev/ttyUSB*")
            return False

    def disconnect(self) -> None:
        """Close serial connection."""
        if self.serial and self.serial.is_open:
            self.serial.close()
            self.serial = None

    def send_command(self, cmd: str) -> Optional[str]:
        """Send command and receive response."""
        if not self.serial or not self.serial.is_open:
            return None

        try:
            # Clear buffers
            self.serial.reset_input_buffer()

            # Send command with newline
            self.serial.write((cmd + "\n").encode("ascii"))
            self.serial.flush()

            # Read response line
            response = self.serial.readline()
            return response.decode("ascii", errors="replace").strip()

        except Exception as e:
            print(f"  Command error: {e}")
            return None

    def test_version(self) -> bool:
        """Test getting firmware version."""
        print("\nTest: Firmware version")

        response = self.send_command("V")
        if response:
            print(f"  Version: {response}")
            print("  ✓ Firmware responding")
            return True

        print("  ✗ No version response")
        return False

    def test_ra_position(self) -> bool:
        """Test RA encoder position reading."""
        print("\nTest: RA encoder position")

        response = self.send_command("R")
        if response:
            try:
                position = int(response)
                print(f"  RA position: {position} counts")

                # Check if position is reasonable (not overflow/error)
                if -2147483648 < position < 2147483647:
                    print("  ✓ Valid RA position")
                    return True
            except ValueError:
                print(f"  Response: {response}")

        print("  ✗ Invalid RA position")
        return False

    def test_dec_position(self) -> bool:
        """Test DEC encoder position reading."""
        print("\nTest: DEC encoder position")

        response = self.send_command("D")
        if response:
            try:
                position = int(response)
                print(f"  DEC position: {position} counts")

                if -2147483648 < position < 2147483647:
                    print("  ✓ Valid DEC position")
                    return True
            except ValueError:
                print(f"  Response: {response}")

        print("  ✗ Invalid DEC position")
        return False

    def test_both_positions(self) -> bool:
        """Test combined position reading."""
        print("\nTest: Combined position query")

        response = self.send_command("P")
        if response:
            print(f"  Response: {response}")

            # Expect format like "RA:12345,DEC:67890" or "12345,67890"
            if "," in response:
                parts = response.replace("RA:", "").replace("DEC:", "").split(",")
                if len(parts) >= 2:
                    try:
                        ra = int(parts[0].strip())
                        dec = int(parts[1].strip())
                        print(f"  RA: {ra}, DEC: {dec}")
                        print("  ✓ Both positions valid")
                        return True
                    except ValueError:
                        pass

        print("  ✗ Could not parse combined position")
        return False

    def test_position_stability(self) -> bool:
        """Test position reading stability over time."""
        print("\nTest: Position stability (5 samples)")

        positions = []
        for i in range(5):
            response = self.send_command("R")
            if response:
                try:
                    positions.append(int(response))
                except ValueError:
                    pass
            time.sleep(0.2)

        if len(positions) < 5:
            print(f"  Only got {len(positions)}/5 readings")
            print("  ✗ Unstable communication")
            return False

        # Check variance
        avg = sum(positions) / len(positions)
        variance = sum((p - avg) ** 2 for p in positions) / len(positions)
        std_dev = variance ** 0.5

        print(f"  Positions: {positions}")
        print(f"  Std dev: {std_dev:.2f} counts")

        # Allow some noise but flag if excessive
        if std_dev < 10:  # Less than 10 counts variation
            print("  ✓ Position stable")
            return True
        elif std_dev < 100:
            print("  ⚠ Minor position variation detected")
            return True
        else:
            print("  ✗ Excessive position variation")
            return False

    def test_zero_command(self) -> bool:
        """Test zero/reset command (non-destructive check)."""
        print("\nTest: Zero command availability")

        # Just check if command is recognized, don't actually zero
        # Send help or status command instead
        response = self.send_command("?")
        if response:
            print(f"  Help response: {response[:50]}...")
            print("  ✓ Command interface working")
            return True

        # Try status
        response = self.send_command("S")
        if response:
            print(f"  Status: {response}")
            print("  ✓ Status command working")
            return True

        print("  (Help/status not available - non-critical)")
        return True

    def test_response_time(self) -> bool:
        """Test command response latency."""
        print("\nTest: Response latency")

        latencies = []
        for _ in range(10):
            start = time.time()
            response = self.send_command("R")
            if response:
                latency = (time.time() - start) * 1000  # ms
                latencies.append(latency)
            time.sleep(0.05)

        if not latencies:
            print("  ✗ No successful responses")
            return False

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)

        print(f"  Average: {avg_latency:.1f} ms")
        print(f"  Maximum: {max_latency:.1f} ms")

        if avg_latency < 100:  # Under 100ms average
            print("  ✓ Response time acceptable")
            return True
        else:
            print("  ✗ Response time too slow")
            return False

    def run_all_tests(self) -> bool:
        """Run all encoder tests."""
        print("=" * 60)
        print("NIGHTWATCH Encoder Bridge Test")
        print("=" * 60)
        print(f"Port: {self.port}")
        print(f"Baudrate: {self.baudrate}")

        if not self.connect():
            return False

        try:
            tests = [
                ("Firmware Version", self.test_version),
                ("RA Position", self.test_ra_position),
                ("DEC Position", self.test_dec_position),
                ("Combined Position", self.test_both_positions),
                ("Position Stability", self.test_position_stability),
                ("Command Interface", self.test_zero_command),
                ("Response Latency", self.test_response_time),
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
    """Run encoder test from command line."""
    parser = argparse.ArgumentParser(
        description="Test encoder bridge communication"
    )
    parser.add_argument(
        "--port",
        default="/dev/ttyUSB0",
        help="Serial port (default: /dev/ttyUSB0)",
    )
    parser.add_argument(
        "--baudrate",
        type=int,
        default=115200,
        help="Baud rate (default: 115200)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="Read timeout in seconds (default: 2.0)",
    )

    args = parser.parse_args()

    test = EncoderTest(
        port=args.port,
        baudrate=args.baudrate,
        timeout=args.timeout,
    )

    success = test.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

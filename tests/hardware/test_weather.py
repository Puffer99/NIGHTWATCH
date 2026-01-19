#!/usr/bin/env python3
"""
Weather Station Test (Step 641)

Verifies Ecowitt weather station communication and data quality.
Tests HTTP data reception and validates sensor readings.

Usage:
    python -m tests.hardware.test_weather [--host HOST] [--port PORT]
    pytest tests/hardware/test_weather.py -v -m hardware

Requirements:
    - Ecowitt gateway powered on and network-accessible
    - Gateway configured to push data to NIGHTWATCH server
"""

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError


class WeatherStationTest:
    """Test weather station communication."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        gateway_host: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.gateway_host = gateway_host  # Ecowitt gateway IP
        self.results: dict[str, bool] = {}
        self.weather_data: Optional[dict[str, Any]] = None

    def fetch_weather_api(self) -> Optional[dict[str, Any]]:
        """Fetch weather data from NIGHTWATCH API."""
        url = f"http://{self.host}:{self.port}/weather/current"
        try:
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except URLError as e:
            print(f"  API error: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"  JSON parse error: {e}")
            return None

    def ping_gateway(self) -> bool:
        """Check if gateway is reachable."""
        if not self.gateway_host:
            return True  # Skip if not configured

        import subprocess

        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", self.gateway_host],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    def test_api_availability(self) -> bool:
        """Test if weather API endpoint is available."""
        print("\nTest: Weather API availability")
        url = f"http://{self.host}:{self.port}/weather/current"
        print(f"  URL: {url}")

        try:
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, timeout=10) as response:
                if response.status == 200:
                    print("  ✓ API endpoint responding")
                    return True
        except URLError as e:
            print(f"  ✗ API not available: {e}")
        except Exception as e:
            print(f"  ✗ Error: {e}")

        return False

    def test_data_freshness(self) -> bool:
        """Test if weather data is recent."""
        print("\nTest: Data freshness")

        data = self.fetch_weather_api()
        if not data:
            print("  ✗ Could not fetch weather data")
            return False

        self.weather_data = data

        # Check for timestamp field
        timestamp = data.get("timestamp") or data.get("dateutc") or data.get("updated")
        if timestamp:
            try:
                if isinstance(timestamp, str):
                    # Try parsing ISO format
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                elif isinstance(timestamp, (int, float)):
                    dt = datetime.fromtimestamp(timestamp)
                else:
                    dt = None

                if dt:
                    age = datetime.now(dt.tzinfo) - dt if dt.tzinfo else datetime.now() - dt
                    age_seconds = abs(age.total_seconds())
                    print(f"  Data age: {age_seconds:.0f} seconds")

                    if age_seconds < 300:  # 5 minutes
                        print("  ✓ Data is fresh")
                        return True
                    else:
                        print("  ✗ Data is stale (> 5 minutes old)")
                        return False
            except Exception as e:
                print(f"  Warning: Could not parse timestamp: {e}")

        # No timestamp, assume fresh if we got data
        print("  ✓ Data received (no timestamp to verify)")
        return True

    def test_temperature(self) -> bool:
        """Test temperature reading validity."""
        print("\nTest: Temperature reading")

        data = self.weather_data or self.fetch_weather_api()
        if not data:
            print("  ✗ No weather data available")
            return False

        # Look for temperature in various formats
        temp = None
        for key in ["temperature_f", "tempf", "temp_f", "temperature"]:
            if key in data:
                temp = float(data[key])
                break

        if temp is None:
            for key in ["temperature_c", "tempc", "temp_c"]:
                if key in data:
                    temp = float(data[key]) * 9 / 5 + 32  # Convert to F
                    break

        if temp is not None:
            print(f"  Temperature: {temp:.1f}°F")

            # Sanity check: reasonable outdoor temperature range
            if -40 <= temp <= 140:  # -40°F to 140°F
                print("  ✓ Temperature in valid range")
                return True
            else:
                print("  ✗ Temperature out of range")
                return False

        print("  ✗ Temperature reading not found")
        return False

    def test_humidity(self) -> bool:
        """Test humidity reading validity."""
        print("\nTest: Humidity reading")

        data = self.weather_data or self.fetch_weather_api()
        if not data:
            print("  ✗ No weather data available")
            return False

        humidity = None
        for key in ["humidity", "humidity_pct", "humidityin"]:
            if key in data:
                humidity = float(data[key])
                break

        if humidity is not None:
            print(f"  Humidity: {humidity:.0f}%")

            if 0 <= humidity <= 100:
                print("  ✓ Humidity in valid range")
                return True
            else:
                print("  ✗ Humidity out of range")
                return False

        print("  ✗ Humidity reading not found")
        return False

    def test_wind(self) -> bool:
        """Test wind speed reading validity."""
        print("\nTest: Wind speed reading")

        data = self.weather_data or self.fetch_weather_api()
        if not data:
            print("  ✗ No weather data available")
            return False

        wind = None
        for key in ["wind_mph", "windspeedmph", "windspeed"]:
            if key in data:
                wind = float(data[key])
                break

        if wind is not None:
            print(f"  Wind speed: {wind:.1f} mph")

            if 0 <= wind <= 200:  # Reasonable range
                print("  ✓ Wind speed in valid range")
                return True
            else:
                print("  ✗ Wind speed out of range")
                return False

        print("  ✗ Wind speed reading not found")
        return False

    def test_pressure(self) -> bool:
        """Test barometric pressure reading."""
        print("\nTest: Barometric pressure")

        data = self.weather_data or self.fetch_weather_api()
        if not data:
            print("  ✗ No weather data available")
            return False

        pressure = None
        for key in ["baromrelin", "pressure_in", "barom", "pressure"]:
            if key in data:
                pressure = float(data[key])
                break

        if pressure is not None:
            print(f"  Pressure: {pressure:.2f} inHg")

            # Valid barometric pressure range (sea level adjusted)
            if 25 <= pressure <= 35:  # inHg
                print("  ✓ Pressure in valid range")
                return True
            else:
                print("  ✗ Pressure out of range")
                return False

        print("  (Pressure reading not found - non-critical)")
        return True  # Non-critical field

    def test_safety_status(self) -> bool:
        """Test safety determination."""
        print("\nTest: Safety status")

        data = self.weather_data or self.fetch_weather_api()
        if not data:
            print("  ✗ No weather data available")
            return False

        is_safe = data.get("is_safe")
        if is_safe is not None:
            status = "SAFE" if is_safe else "UNSAFE"
            print(f"  Safety status: {status}")
            print("  ✓ Safety status available")
            return True

        print("  (Safety status not in response - will be computed)")
        return True

    def test_gateway_connectivity(self) -> bool:
        """Test gateway network connectivity."""
        print("\nTest: Gateway connectivity")

        if not self.gateway_host:
            print("  (Gateway IP not configured - skipping)")
            return True

        print(f"  Gateway: {self.gateway_host}")

        if self.ping_gateway():
            print("  ✓ Gateway reachable")
            return True
        else:
            print("  ✗ Gateway not reachable")
            return False

    def run_all_tests(self) -> bool:
        """Run all weather station tests."""
        print("=" * 60)
        print("NIGHTWATCH Weather Station Test")
        print("=" * 60)
        print(f"API: http://{self.host}:{self.port}/weather/current")
        if self.gateway_host:
            print(f"Gateway: {self.gateway_host}")

        tests = [
            ("API Availability", self.test_api_availability),
            ("Gateway Connectivity", self.test_gateway_connectivity),
            ("Data Freshness", self.test_data_freshness),
            ("Temperature", self.test_temperature),
            ("Humidity", self.test_humidity),
            ("Wind Speed", self.test_wind),
            ("Pressure", self.test_pressure),
            ("Safety Status", self.test_safety_status),
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

        # Critical tests that must pass
        critical = ["API Availability", "Temperature", "Humidity", "Wind Speed"]
        critical_passed = all(self.results.get(t, False) for t in critical)

        if not critical_passed:
            print("\n⚠ CRITICAL TESTS FAILED - Weather monitoring may not work!")

        return passed == total


def main():
    """Run weather station test from command line."""
    parser = argparse.ArgumentParser(
        description="Test weather station communication"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="NIGHTWATCH API host (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="NIGHTWATCH API port (default: 8080)",
    )
    parser.add_argument(
        "--gateway",
        default=None,
        help="Ecowitt gateway IP for connectivity test",
    )

    args = parser.parse_args()

    test = WeatherStationTest(
        host=args.host,
        port=args.port,
        gateway_host=args.gateway,
    )

    success = test.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

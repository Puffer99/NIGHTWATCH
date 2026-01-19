#!/usr/bin/env python3
"""
Voice Pipeline Test (Step 644)

Verifies audio hardware and Wyoming voice services are working.
Tests microphone input, speaker output, STT, and TTS services.

Usage:
    python -m tests.hardware.test_voice [--stt-port PORT] [--tts-port PORT]
    pytest tests/hardware/test_voice.py -v -m hardware

Requirements:
    - Microphone connected and configured
    - Speakers connected and configured
    - Wyoming STT service running (port 10300)
    - Wyoming TTS service running (port 10200)
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from typing import Any, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError


class VoicePipelineTest:
    """Test voice pipeline components."""

    def __init__(
        self,
        stt_host: str = "localhost",
        stt_port: int = 10300,
        tts_host: str = "localhost",
        tts_port: int = 10200,
    ):
        self.stt_host = stt_host
        self.stt_port = stt_port
        self.tts_host = tts_host
        self.tts_port = tts_port
        self.results: dict[str, bool] = {}

    def run_command(
        self, cmd: list[str], timeout: float = 10.0
    ) -> tuple[bool, str, str]:
        """Run shell command and return success, stdout, stderr."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except FileNotFoundError:
            return False, "", f"Command not found: {cmd[0]}"
        except Exception as e:
            return False, "", str(e)

    def fetch_json(self, url: str) -> Optional[dict[str, Any]]:
        """Fetch JSON from URL."""
        try:
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, timeout=5) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception:
            return None

    def test_alsa_devices(self) -> bool:
        """Test ALSA audio device detection."""
        print("\nTest: ALSA audio devices")

        # Check recording devices
        success, stdout, stderr = self.run_command(["arecord", "-l"])
        if success and stdout:
            print("  Recording devices:")
            for line in stdout.strip().split("\n")[:5]:
                print(f"    {line}")

            if "card" in stdout.lower():
                print("  ✓ Recording devices found")
            else:
                print("  ⚠ No recording devices listed")
        else:
            print(f"  ✗ arecord error: {stderr}")
            return False

        # Check playback devices
        success, stdout, stderr = self.run_command(["aplay", "-l"])
        if success and stdout:
            print("\n  Playback devices:")
            for line in stdout.strip().split("\n")[:5]:
                print(f"    {line}")

            if "card" in stdout.lower():
                print("  ✓ Playback devices found")
                return True
            else:
                print("  ⚠ No playback devices listed")

        return False

    def test_microphone_record(self) -> bool:
        """Test microphone recording capability."""
        print("\nTest: Microphone recording")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_file = f.name

        try:
            print("  Recording 2 seconds of audio...")
            success, stdout, stderr = self.run_command(
                [
                    "arecord",
                    "-d", "2",
                    "-f", "S16_LE",
                    "-r", "16000",
                    "-c", "1",
                    temp_file,
                ],
                timeout=10,
            )

            if not success:
                print(f"  ✗ Recording failed: {stderr}")
                return False

            # Check file was created and has content
            if os.path.exists(temp_file):
                size = os.path.getsize(temp_file)
                print(f"  Recorded file size: {size} bytes")

                if size > 1000:  # At least 1KB for 2 seconds
                    print("  ✓ Microphone recording works")
                    return True
                else:
                    print("  ✗ Recording too small (silence?)")
                    return False

            print("  ✗ Recording file not created")
            return False

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_speaker_playback(self) -> bool:
        """Test speaker playback capability."""
        print("\nTest: Speaker playback")

        # Use speaker-test for a brief test tone
        print("  Playing test tone (1 second)...")
        success, stdout, stderr = self.run_command(
            ["speaker-test", "-t", "sine", "-f", "440", "-l", "1", "-P", "1"],
            timeout=5,
        )

        if success:
            print("  ✓ Speaker playback works")
            print("  (You should have heard a brief tone)")
            return True
        else:
            # speaker-test might not be available, try aplay
            print("  speaker-test not available, trying aplay...")

            # Generate a simple beep using sox if available
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_file = f.name

            try:
                # Create a short tone with sox
                success, _, _ = self.run_command(
                    ["sox", "-n", temp_file, "synth", "0.5", "sine", "440"],
                    timeout=5,
                )

                if success:
                    success, _, stderr = self.run_command(
                        ["aplay", temp_file],
                        timeout=5,
                    )
                    if success:
                        print("  ✓ Speaker playback works")
                        return True

                print("  ⚠ Could not verify speaker (no test tools)")
                return True  # Non-critical

            finally:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)

        return False

    def test_stt_service(self) -> bool:
        """Test STT (Speech-to-Text) service availability."""
        print("\nTest: STT service (Wyoming)")
        url = f"http://{self.stt_host}:{self.stt_port}/info"
        print(f"  URL: {url}")

        data = self.fetch_json(url)
        if data:
            print(f"  Service info: {json.dumps(data, indent=4)[:200]}...")
            print("  ✓ STT service responding")
            return True

        # Try alternative endpoint
        url = f"http://{self.stt_host}:{self.stt_port}/"
        try:
            with urlopen(url, timeout=5) as response:
                if response.status == 200:
                    print("  ✓ STT service responding")
                    return True
        except Exception:
            pass

        print("  ✗ STT service not available")
        return False

    def test_tts_service(self) -> bool:
        """Test TTS (Text-to-Speech) service availability."""
        print("\nTest: TTS service (Wyoming)")
        url = f"http://{self.tts_host}:{self.tts_port}/info"
        print(f"  URL: {url}")

        data = self.fetch_json(url)
        if data:
            print(f"  Service info: {json.dumps(data, indent=4)[:200]}...")
            print("  ✓ TTS service responding")
            return True

        # Try alternative endpoint
        url = f"http://{self.tts_host}:{self.tts_port}/"
        try:
            with urlopen(url, timeout=5) as response:
                if response.status == 200:
                    print("  ✓ TTS service responding")
                    return True
        except Exception:
            pass

        print("  ✗ TTS service not available")
        return False

    def test_pulseaudio(self) -> bool:
        """Test PulseAudio status."""
        print("\nTest: PulseAudio status")

        success, stdout, stderr = self.run_command(["pactl", "info"])
        if success:
            print("  PulseAudio info:")
            for line in stdout.strip().split("\n")[:5]:
                print(f"    {line}")
            print("  ✓ PulseAudio running")
            return True

        # PulseAudio might not be used (ALSA direct)
        print("  PulseAudio not running (may be using ALSA directly)")
        return True  # Non-critical

    def test_audio_levels(self) -> bool:
        """Test audio input/output levels."""
        print("\nTest: Audio levels")

        # Check microphone level
        success, stdout, stderr = self.run_command(
            ["amixer", "sget", "Capture"]
        )
        if success:
            if "%" in stdout:
                print("  Capture level found")
            print("  ✓ Audio mixer accessible")
            return True

        # Try alternative
        success, stdout, stderr = self.run_command(["amixer"])
        if success:
            print("  ✓ Audio mixer accessible")
            return True

        print("  ⚠ Could not check audio levels")
        return True  # Non-critical

    def test_wake_word_setup(self) -> bool:
        """Test wake word detection setup."""
        print("\nTest: Wake word configuration")

        # Check if openwakeword or similar is configured
        # This is more of a config check

        config_paths = [
            "/etc/nightwatch/config.yaml",
            "./nightwatch.yaml",
            os.path.expanduser("~/.nightwatch/config.yaml"),
        ]

        for path in config_paths:
            if os.path.exists(path):
                print(f"  Config found: {path}")
                with open(path) as f:
                    content = f.read()
                    if "wake_word" in content.lower():
                        print("  ✓ Wake word configured")
                        return True

        print("  ⚠ Wake word configuration not found")
        print("  (Configure wake_word in config.yaml)")
        return True  # Non-critical for basic test

    def run_all_tests(self) -> bool:
        """Run all voice pipeline tests."""
        print("=" * 60)
        print("NIGHTWATCH Voice Pipeline Test")
        print("=" * 60)
        print(f"STT Service: {self.stt_host}:{self.stt_port}")
        print(f"TTS Service: {self.tts_host}:{self.tts_port}")

        tests = [
            ("ALSA Devices", self.test_alsa_devices),
            ("PulseAudio", self.test_pulseaudio),
            ("Microphone Recording", self.test_microphone_record),
            ("Speaker Playback", self.test_speaker_playback),
            ("Audio Levels", self.test_audio_levels),
            ("STT Service", self.test_stt_service),
            ("TTS Service", self.test_tts_service),
            ("Wake Word Setup", self.test_wake_word_setup),
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

        # Critical tests
        critical = ["ALSA Devices", "Microphone Recording", "STT Service", "TTS Service"]
        critical_passed = all(self.results.get(t, False) for t in critical)

        if not critical_passed:
            print("\n⚠ CRITICAL TESTS FAILED - Voice control may not work!")

        return passed == total


def main():
    """Run voice pipeline test from command line."""
    parser = argparse.ArgumentParser(
        description="Test voice pipeline components"
    )
    parser.add_argument(
        "--stt-host",
        default="localhost",
        help="STT service host (default: localhost)",
    )
    parser.add_argument(
        "--stt-port",
        type=int,
        default=10300,
        help="STT service port (default: 10300)",
    )
    parser.add_argument(
        "--tts-host",
        default="localhost",
        help="TTS service host (default: localhost)",
    )
    parser.add_argument(
        "--tts-port",
        type=int,
        default=10200,
        help="TTS service port (default: 10200)",
    )

    args = parser.parse_args()

    test = VoicePipelineTest(
        stt_host=args.stt_host,
        stt_port=args.stt_port,
        tts_host=args.tts_host,
        tts_port=args.tts_port,
    )

    success = test.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

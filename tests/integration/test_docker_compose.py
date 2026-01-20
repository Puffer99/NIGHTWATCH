"""
Integration tests for Docker Compose configuration files.

Step 515: Validates all docker-compose files for correct syntax and structure.
"""

import os
import subprocess
import pytest

# Path to docker directory
DOCKER_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "docker")


class TestDockerComposeValidation:
    """Tests for Docker Compose file validation."""

    @pytest.fixture(scope="class")
    def compose_files(self):
        """Get list of all docker-compose files."""
        files = []
        for f in os.listdir(DOCKER_DIR):
            if f.startswith("docker-compose") and f.endswith(".yml"):
                files.append(os.path.join(DOCKER_DIR, f))
        return files

    def test_compose_files_exist(self, compose_files):
        """Test that docker-compose files exist."""
        assert len(compose_files) >= 1, "At least one docker-compose file should exist"

        expected_files = [
            "docker-compose.dev.yml",
            "docker-compose.test.yml",
            "docker-compose.prod.yml",
        ]
        for expected in expected_files:
            path = os.path.join(DOCKER_DIR, expected)
            assert os.path.exists(path), f"Missing {expected}"

    @pytest.mark.parametrize("compose_file", [
        "docker-compose.dev.yml",
        "docker-compose.test.yml",
        "docker-compose.prod.yml",
    ])
    def test_compose_config_valid(self, compose_file):
        """Test that docker-compose file has valid syntax."""
        filepath = os.path.join(DOCKER_DIR, compose_file)

        if not os.path.exists(filepath):
            pytest.skip(f"{compose_file} not found")

        result = subprocess.run(
            ["docker", "compose", "-f", filepath, "config", "--quiet"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, (
            f"{compose_file} validation failed:\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    def test_dev_compose_has_required_services(self):
        """Test dev compose has Alpaca and INDI services."""
        filepath = os.path.join(DOCKER_DIR, "docker-compose.dev.yml")

        result = subprocess.run(
            ["docker", "compose", "-f", filepath, "config", "--services"],
            capture_output=True,
            text=True,
        )

        services = result.stdout.strip().split("\n")
        assert "alpaca-simulators" in services, "Missing alpaca-simulators service"
        assert "indi-server" in services, "Missing indi-server service"

    def test_test_compose_has_required_services(self):
        """Test CI compose has minimal required services."""
        filepath = os.path.join(DOCKER_DIR, "docker-compose.test.yml")

        if not os.path.exists(filepath):
            pytest.skip("docker-compose.test.yml not found")

        result = subprocess.run(
            ["docker", "compose", "-f", filepath, "config", "--services"],
            capture_output=True,
            text=True,
        )

        services = result.stdout.strip().split("\n")
        assert "alpaca-simulators" in services, "Missing alpaca-simulators service"

    def test_compose_has_healthchecks(self):
        """Test that services have healthchecks configured."""
        import yaml

        filepath = os.path.join(DOCKER_DIR, "docker-compose.dev.yml")

        with open(filepath, "r") as f:
            config = yaml.safe_load(f)

        services = config.get("services", {})
        for name, service in services.items():
            if not name.startswith("#"):  # Skip comments
                assert "healthcheck" in service, (
                    f"Service '{name}' missing healthcheck"
                )

    def test_compose_networks_defined(self):
        """Test that networks are properly defined."""
        import yaml

        for compose_file in ["docker-compose.dev.yml", "docker-compose.test.yml"]:
            filepath = os.path.join(DOCKER_DIR, compose_file)

            if not os.path.exists(filepath):
                continue

            with open(filepath, "r") as f:
                config = yaml.safe_load(f)

            assert "networks" in config, f"{compose_file} missing networks section"
            networks = config.get("networks", {})
            assert len(networks) >= 1, f"{compose_file} should define at least one network"

    def test_prod_compose_has_security_settings(self):
        """Test production compose has security-relevant settings."""
        import yaml

        filepath = os.path.join(DOCKER_DIR, "docker-compose.prod.yml")

        if not os.path.exists(filepath):
            pytest.skip("docker-compose.prod.yml not found")

        with open(filepath, "r") as f:
            config = yaml.safe_load(f)

        services = config.get("services", {})

        # Check main service has restart policy
        if "nightwatch" in services:
            assert services["nightwatch"].get("restart") is not None, (
                "Production nightwatch service should have restart policy"
            )


class TestDockerComposePortConflicts:
    """Tests for port conflict detection."""

    def test_no_duplicate_ports_within_file(self):
        """Test that no ports are duplicated within a compose file."""
        import yaml

        for compose_file in os.listdir(DOCKER_DIR):
            if not compose_file.endswith(".yml"):
                continue

            filepath = os.path.join(DOCKER_DIR, compose_file)

            with open(filepath, "r") as f:
                config = yaml.safe_load(f)

            services = config.get("services", {})
            all_ports = []

            for name, service in services.items():
                if isinstance(service, dict):
                    ports = service.get("ports", [])
                    for port in ports:
                        if isinstance(port, str):
                            host_port = port.split(":")[0]
                        else:
                            host_port = str(port)
                        all_ports.append((host_port, name))

            # Check for duplicates
            seen = {}
            for port, service in all_ports:
                if port in seen:
                    pytest.fail(
                        f"Port {port} used by both '{seen[port]}' and '{service}' "
                        f"in {compose_file}"
                    )
                seen[port] = service

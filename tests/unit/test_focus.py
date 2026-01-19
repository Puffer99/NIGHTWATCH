"""
Unit tests for NIGHTWATCH focuser service.

Tests focuser configuration, state management, and auto-focus data structures.
"""

import pytest
from datetime import datetime, timedelta
from services.focus.focuser_service import (
    FocuserService,
    FocuserConfig,
    FocuserState,
    AutoFocusMethod,
    FocusMetric,
    FocusRun,
)


class TestFocuserState:
    """Tests for FocuserState enum."""

    def test_idle_state(self):
        """Test idle state value."""
        assert FocuserState.IDLE.value == "idle"

    def test_moving_state(self):
        """Test moving state value."""
        assert FocuserState.MOVING.value == "moving"

    def test_autofocus_state(self):
        """Test autofocus state value."""
        assert FocuserState.AUTOFOCUS.value == "autofocus"

    def test_calibrating_state(self):
        """Test calibrating state value."""
        assert FocuserState.CALIBRATING.value == "calibrating"

    def test_error_state(self):
        """Test error state value."""
        assert FocuserState.ERROR.value == "error"


class TestAutoFocusMethod:
    """Tests for AutoFocusMethod enum."""

    def test_vcurve_method(self):
        """Test V-curve method value."""
        assert AutoFocusMethod.VCURVE.value == "vcurve"

    def test_bahtinov_method(self):
        """Test Bahtinov method value."""
        assert AutoFocusMethod.BAHTINOV.value == "bahtinov"

    def test_contrast_method(self):
        """Test contrast method value."""
        assert AutoFocusMethod.CONTRAST.value == "contrast"

    def test_hfd_method(self):
        """Test HFD method value."""
        assert AutoFocusMethod.HFD.value == "hfd"


class TestFocuserConfig:
    """Tests for FocuserConfig dataclass."""

    def test_default_config(self):
        """Test default focuser configuration."""
        config = FocuserConfig()

        assert config.max_position == 50000
        assert config.step_size_um == 1.0
        assert config.backlash_steps == 100
        assert config.temp_coefficient == -2.5
        assert config.temp_interval_c == 2.0
        assert config.time_interval_min == 30.0
        assert config.autofocus_method == AutoFocusMethod.HFD
        assert config.autofocus_step_size == 100
        assert config.autofocus_samples == 9
        assert config.autofocus_exposure_sec == 2.0
        assert config.hfd_target == 3.0
        assert config.focus_tolerance == 10

    def test_custom_config(self):
        """Test custom focuser configuration."""
        config = FocuserConfig(
            max_position=100000,
            step_size_um=0.5,
            backlash_steps=200,
            temp_coefficient=-3.0,
            autofocus_method=AutoFocusMethod.VCURVE,
            autofocus_step_size=50,
            autofocus_samples=15,
        )

        assert config.max_position == 100000
        assert config.step_size_um == 0.5
        assert config.backlash_steps == 200
        assert config.temp_coefficient == -3.0
        assert config.autofocus_method == AutoFocusMethod.VCURVE
        assert config.autofocus_step_size == 50
        assert config.autofocus_samples == 15

    def test_temperature_compensation_settings(self):
        """Test temperature compensation configuration."""
        config = FocuserConfig(
            temp_coefficient=-2.5,  # Typical for refractors
            temp_interval_c=1.5,    # More aggressive temp tracking
            time_interval_min=20.0, # More frequent time-based refocus
        )

        assert config.temp_coefficient == -2.5
        assert config.temp_interval_c == 1.5
        assert config.time_interval_min == 20.0


class TestFocusMetric:
    """Tests for FocusMetric dataclass."""

    def test_metric_creation(self):
        """Test creating focus metric."""
        metric = FocusMetric(
            timestamp=datetime.now(),
            position=25000,
            hfd=3.5,
            fwhm=2.8,
            peak_value=45000,
            star_count=25,
            temperature_c=15.0,
        )

        assert metric.position == 25000
        assert metric.hfd == 3.5
        assert metric.fwhm == 2.8
        assert metric.peak_value == 45000
        assert metric.star_count == 25
        assert metric.temperature_c == 15.0

    def test_metric_at_different_positions(self):
        """Test metrics at various focus positions."""
        # Out of focus - high HFD
        metric_far = FocusMetric(
            timestamp=datetime.now(),
            position=20000,
            hfd=8.5,
            fwhm=6.8,
            peak_value=20000,
            star_count=15,
            temperature_c=15.0,
        )

        # In focus - low HFD
        metric_focus = FocusMetric(
            timestamp=datetime.now(),
            position=25000,
            hfd=2.8,
            fwhm=2.2,
            peak_value=55000,
            star_count=30,
            temperature_c=15.0,
        )

        assert metric_far.hfd > metric_focus.hfd
        assert metric_far.peak_value < metric_focus.peak_value

    def test_metric_cold_temperature(self):
        """Test metric at cold temperature."""
        metric = FocusMetric(
            timestamp=datetime.now(),
            position=25000,
            hfd=3.0,
            fwhm=2.4,
            peak_value=50000,
            star_count=25,
            temperature_c=-10.0,
        )

        assert metric.temperature_c == -10.0


class TestFocusRun:
    """Tests for FocusRun dataclass."""

    def test_focus_run_creation(self):
        """Test creating focus run."""
        run = FocusRun(
            run_id="focus_20240115_220000",
            start_time=datetime.now(),
            method=AutoFocusMethod.HFD,
            initial_position=24000,
        )

        assert run.run_id == "focus_20240115_220000"
        assert run.method == AutoFocusMethod.HFD
        assert run.initial_position == 24000
        assert run.final_position == 0
        assert run.measurements == []
        assert run.best_hfd == float('inf')
        assert run.success is False
        assert run.error is None
        assert run.end_time is None

    def test_successful_focus_run(self):
        """Test successful focus run."""
        start = datetime.now()
        measurements = [
            FocusMetric(
                timestamp=start,
                position=24000,
                hfd=5.0,
                fwhm=4.0,
                peak_value=30000,
                star_count=20,
                temperature_c=15.0,
            ),
            FocusMetric(
                timestamp=start + timedelta(seconds=5),
                position=25000,
                hfd=2.8,  # Best focus
                fwhm=2.2,
                peak_value=55000,
                star_count=30,
                temperature_c=15.0,
            ),
            FocusMetric(
                timestamp=start + timedelta(seconds=10),
                position=26000,
                hfd=5.2,
                fwhm=4.2,
                peak_value=28000,
                star_count=18,
                temperature_c=15.0,
            ),
        ]

        run = FocusRun(
            run_id="focus_success",
            start_time=start,
            end_time=start + timedelta(seconds=15),
            method=AutoFocusMethod.HFD,
            initial_position=24000,
            final_position=25000,
            measurements=measurements,
            best_hfd=2.8,
            success=True,
        )

        assert run.success is True
        assert run.final_position == 25000
        assert run.best_hfd == 2.8
        assert len(run.measurements) == 3

    def test_failed_focus_run(self):
        """Test failed focus run."""
        run = FocusRun(
            run_id="focus_failed",
            start_time=datetime.now(),
            method=AutoFocusMethod.HFD,
            initial_position=24000,
            success=False,
            error="No stars detected in image",
        )

        assert run.success is False
        assert run.error == "No stars detected in image"


class TestFocuserServiceInitialization:
    """Tests for FocuserService initialization."""

    def test_default_initialization(self):
        """Test default focuser service initialization."""
        focuser = FocuserService()

        assert focuser.connected is False
        assert focuser.state == FocuserState.IDLE
        assert focuser.position == 25000  # Mid-range default
        assert focuser.temperature == 20.0

    def test_custom_config_initialization(self):
        """Test focuser service with custom config."""
        config = FocuserConfig(
            max_position=80000,
            temp_coefficient=-3.0,
        )
        focuser = FocuserService(config=config)

        assert focuser.config.max_position == 80000
        assert focuser.config.temp_coefficient == -3.0


class TestFocuserConfigValidation:
    """Tests for focuser configuration boundary conditions."""

    def test_max_position_bounds(self):
        """Test maximum position bounds."""
        # Short travel
        config_short = FocuserConfig(max_position=10000)
        assert config_short.max_position == 10000

        # Long travel
        config_long = FocuserConfig(max_position=200000)
        assert config_long.max_position == 200000

    def test_step_size_precision(self):
        """Test step size precision settings."""
        # Coarse steps
        config_coarse = FocuserConfig(step_size_um=2.0)
        assert config_coarse.step_size_um == 2.0

        # Fine steps
        config_fine = FocuserConfig(step_size_um=0.1)
        assert config_fine.step_size_um == 0.1

    def test_backlash_compensation(self):
        """Test backlash compensation settings."""
        # No backlash
        config_none = FocuserConfig(backlash_steps=0)
        assert config_none.backlash_steps == 0

        # Large backlash
        config_large = FocuserConfig(backlash_steps=500)
        assert config_large.backlash_steps == 500

    def test_temperature_coefficient_range(self):
        """Test temperature coefficient range."""
        # Refractor (positive temp = shorter focus)
        config_refractor = FocuserConfig(temp_coefficient=-2.5)
        assert config_refractor.temp_coefficient == -2.5

        # SCT (opposite sign)
        config_sct = FocuserConfig(temp_coefficient=1.5)
        assert config_sct.temp_coefficient == 1.5

    def test_autofocus_samples(self):
        """Test autofocus sample counts."""
        # Few samples (fast)
        config_fast = FocuserConfig(autofocus_samples=5)
        assert config_fast.autofocus_samples == 5

        # Many samples (accurate)
        config_accurate = FocuserConfig(autofocus_samples=21)
        assert config_accurate.autofocus_samples == 21


class TestFocusMetricBoundaries:
    """Tests for focus metric boundary conditions."""

    def test_very_low_hfd(self):
        """Test very low HFD (excellent focus)."""
        metric = FocusMetric(
            timestamp=datetime.now(),
            position=25000,
            hfd=1.5,  # Excellent seeing
            fwhm=1.2,
            peak_value=60000,
            star_count=50,
            temperature_c=10.0,
        )

        assert metric.hfd == 1.5

    def test_very_high_hfd(self):
        """Test very high HFD (far out of focus)."""
        metric = FocusMetric(
            timestamp=datetime.now(),
            position=10000,
            hfd=25.0,  # Way out of focus
            fwhm=20.0,
            peak_value=5000,
            star_count=5,
            temperature_c=15.0,
        )

        assert metric.hfd == 25.0

    def test_near_saturation_peak(self):
        """Test near-saturation peak value."""
        metric = FocusMetric(
            timestamp=datetime.now(),
            position=25000,
            hfd=3.0,
            fwhm=2.4,
            peak_value=65000,  # Near 16-bit saturation
            star_count=30,
            temperature_c=15.0,
        )

        assert metric.peak_value == 65000

    def test_zero_star_count(self):
        """Test zero star count (failed detection)."""
        metric = FocusMetric(
            timestamp=datetime.now(),
            position=25000,
            hfd=0.0,  # No measurement possible
            fwhm=0.0,
            peak_value=0,
            star_count=0,
            temperature_c=15.0,
        )

        assert metric.star_count == 0


class TestFocusRunMeasurements:
    """Tests for focus run measurement handling."""

    def test_empty_measurements(self):
        """Test focus run with no measurements."""
        run = FocusRun(
            run_id="empty_run",
            start_time=datetime.now(),
        )

        assert len(run.measurements) == 0
        assert run.best_hfd == float('inf')

    def test_single_measurement(self):
        """Test focus run with single measurement."""
        metric = FocusMetric(
            timestamp=datetime.now(),
            position=25000,
            hfd=3.0,
            fwhm=2.4,
            peak_value=50000,
            star_count=25,
            temperature_c=15.0,
        )

        run = FocusRun(
            run_id="single_run",
            start_time=datetime.now(),
            measurements=[metric],
            best_hfd=3.0,
        )

        assert len(run.measurements) == 1
        assert run.best_hfd == 3.0

    def test_many_measurements(self):
        """Test focus run with many measurements (fine V-curve)."""
        now = datetime.now()
        measurements = [
            FocusMetric(
                timestamp=now + timedelta(seconds=i * 3),
                position=23000 + i * 200,
                hfd=8.0 - 0.5 * i if i < 10 else 3.0 + 0.5 * (i - 10),
                fwhm=6.0,
                peak_value=30000,
                star_count=20,
                temperature_c=15.0,
            )
            for i in range(21)  # 21 measurements
        ]

        run = FocusRun(
            run_id="fine_vcurve",
            start_time=now,
            end_time=now + timedelta(seconds=63),
            measurements=measurements,
            best_hfd=min(m.hfd for m in measurements),
        )

        assert len(run.measurements) == 21


class TestAutoFocusMethods:
    """Tests for auto-focus method configurations."""

    def test_hfd_method_config(self):
        """Test HFD method configuration."""
        config = FocuserConfig(autofocus_method=AutoFocusMethod.HFD)
        assert config.autofocus_method == AutoFocusMethod.HFD

    def test_vcurve_method_config(self):
        """Test V-curve method configuration."""
        config = FocuserConfig(autofocus_method=AutoFocusMethod.VCURVE)
        assert config.autofocus_method == AutoFocusMethod.VCURVE

    def test_bahtinov_method_config(self):
        """Test Bahtinov method configuration."""
        config = FocuserConfig(autofocus_method=AutoFocusMethod.BAHTINOV)
        assert config.autofocus_method == AutoFocusMethod.BAHTINOV

    def test_contrast_method_config(self):
        """Test contrast method configuration."""
        config = FocuserConfig(autofocus_method=AutoFocusMethod.CONTRAST)
        assert config.autofocus_method == AutoFocusMethod.CONTRAST

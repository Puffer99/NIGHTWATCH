"""
Unit tests for weather service (Step 209).

Tests the Ecowitt weather client including data parsing,
safety assessment, and sensor reading methods.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from services.weather.ecowitt import (
    EcowittClient,
    WeatherData,
    WeatherCondition,
    WindCondition,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def weather_client():
    """Create a weather client instance."""
    return EcowittClient(
        gateway_ip="192.168.1.50",
        gateway_port=80,
        poll_interval=30.0,
    )


@pytest.fixture
def sample_weather_data():
    """Create sample weather data for testing."""
    return WeatherData(
        timestamp=datetime.now(),
        temperature_f=72.5,
        temperature_c=22.5,
        feels_like_f=71.0,
        dew_point_f=55.0,
        ambient_temperature_c=22.5,
        humidity_percent=45.0,
        wind_speed_mph=8.5,
        wind_gust_mph=12.3,
        wind_direction_deg=180,
        wind_direction_str="S",
        rain_rate_in_hr=0.0,
        rain_daily_in=0.0,
        rain_event_in=0.0,
        is_raining=False,
        rain_sensor_status="ok",
        solar_radiation_wm2=450.0,
        uv_index=5.2,
        pressure_inhg=29.92,
        pressure_trend="steady",
        sky_quality_mpsas=21.2,
        sky_brightness="good",
        condition=WeatherCondition.GOOD,
        wind_condition=WindCondition.LIGHT,
        safe_to_observe=True,
    )


@pytest.fixture
def unsafe_weather_data():
    """Create unsafe weather data for testing."""
    return WeatherData(
        timestamp=datetime.now(),
        temperature_f=72.5,
        temperature_c=22.5,
        feels_like_f=71.0,
        dew_point_f=55.0,
        ambient_temperature_c=22.5,
        humidity_percent=90.0,  # High humidity
        wind_speed_mph=30.0,  # High wind
        wind_gust_mph=45.0,  # Very high gusts
        wind_direction_deg=270,
        wind_direction_str="W",
        rain_rate_in_hr=0.5,  # Raining
        rain_daily_in=1.2,
        rain_event_in=0.8,
        is_raining=True,
        rain_sensor_status="ok",
        solar_radiation_wm2=0.0,
        uv_index=0.0,
        pressure_inhg=29.50,
        pressure_trend="falling",
        sky_quality_mpsas=None,
        sky_brightness=None,
        condition=WeatherCondition.DANGEROUS,
        wind_condition=WindCondition.STRONG,
        safe_to_observe=False,
    )


# =============================================================================
# Client Initialization Tests
# =============================================================================


class TestEcowittClientInit:
    """Tests for EcowittClient initialization."""

    def test_default_initialization(self):
        """Test client initializes with defaults."""
        client = EcowittClient()
        assert client.gateway_ip == "192.168.1.50"
        assert client.gateway_port == 80
        assert client.poll_interval == 30.0

    def test_custom_initialization(self):
        """Test client initializes with custom values."""
        client = EcowittClient(
            gateway_ip="10.0.0.100",
            gateway_port=8080,
            poll_interval=60.0,
        )
        assert client.gateway_ip == "10.0.0.100"
        assert client.gateway_port == 8080
        assert client.poll_interval == 60.0

    def test_base_url_construction(self, weather_client):
        """Test base URL is constructed correctly."""
        assert weather_client._base_url == "http://192.168.1.50:80"

    def test_initial_state(self, weather_client):
        """Test initial client state."""
        assert weather_client._latest_data is None
        assert weather_client._callbacks == []


# =============================================================================
# Weather Condition Assessment Tests
# =============================================================================


class TestWeatherConditionAssessment:
    """Tests for weather condition assessment methods."""

    def test_wind_condition_calm(self, weather_client):
        """Test calm wind assessment."""
        condition = weather_client._assess_wind(3.0, 4.0)
        assert condition == WindCondition.CALM

    def test_wind_condition_light(self, weather_client):
        """Test light wind assessment."""
        condition = weather_client._assess_wind(10.0, 12.0)
        assert condition == WindCondition.LIGHT

    def test_wind_condition_moderate(self, weather_client):
        """Test moderate wind assessment."""
        condition = weather_client._assess_wind(20.0, 22.0)
        assert condition == WindCondition.MODERATE

    def test_wind_condition_strong(self, weather_client):
        """Test strong wind assessment."""
        condition = weather_client._assess_wind(28.0, 35.0)
        assert condition == WindCondition.STRONG

    def test_wind_condition_gust_dominates(self, weather_client):
        """Test that gusts can push condition higher."""
        # Low sustained wind but high gust
        condition = weather_client._assess_wind(5.0, 30.0)
        assert condition == WindCondition.STRONG

    def test_overall_excellent(self, weather_client):
        """Test excellent overall condition."""
        condition = weather_client._assess_overall(
            temp_f=65.0,
            humidity=50.0,
            wind_speed=5.0,
            wind_gust=8.0,
            rain_rate=0.0,
        )
        assert condition == WeatherCondition.EXCELLENT

    def test_overall_good(self, weather_client):
        """Test good overall condition."""
        condition = weather_client._assess_overall(
            temp_f=55.0,
            humidity=60.0,
            wind_speed=12.0,
            wind_gust=18.0,
            rain_rate=0.0,
        )
        assert condition == WeatherCondition.GOOD

    def test_overall_marginal_humidity(self, weather_client):
        """Test marginal condition due to humidity."""
        condition = weather_client._assess_overall(
            temp_f=65.0,
            humidity=88.0,
            wind_speed=5.0,
            wind_gust=8.0,
            rain_rate=0.0,
        )
        assert condition == WeatherCondition.MARGINAL

    def test_overall_poor_wind(self, weather_client):
        """Test poor condition due to wind."""
        condition = weather_client._assess_overall(
            temp_f=65.0,
            humidity=50.0,
            wind_speed=28.0,
            wind_gust=32.0,
            rain_rate=0.0,
        )
        assert condition == WeatherCondition.POOR

    def test_overall_dangerous_rain(self, weather_client):
        """Test dangerous condition due to rain."""
        condition = weather_client._assess_overall(
            temp_f=65.0,
            humidity=50.0,
            wind_speed=5.0,
            wind_gust=8.0,
            rain_rate=0.1,
        )
        assert condition == WeatherCondition.DANGEROUS

    def test_overall_dangerous_gust(self, weather_client):
        """Test dangerous condition due to extreme gust."""
        condition = weather_client._assess_overall(
            temp_f=65.0,
            humidity=50.0,
            wind_speed=20.0,
            wind_gust=40.0,
            rain_rate=0.0,
        )
        assert condition == WeatherCondition.DANGEROUS


# =============================================================================
# Safety Assessment Tests
# =============================================================================


class TestSafetyAssessment:
    """Tests for safety determination."""

    def test_safe_conditions(self, weather_client):
        """Test safe conditions return True."""
        is_safe = weather_client._is_safe_to_observe(
            temp_f=65.0,
            humidity=50.0,
            wind_speed=10.0,
            wind_gust=15.0,
            rain_rate=0.0,
        )
        assert is_safe is True

    def test_unsafe_rain(self, weather_client):
        """Test rain makes conditions unsafe."""
        is_safe = weather_client._is_safe_to_observe(
            temp_f=65.0,
            humidity=50.0,
            wind_speed=5.0,
            wind_gust=8.0,
            rain_rate=0.01,
        )
        assert is_safe is False

    def test_unsafe_wind(self, weather_client):
        """Test high wind makes conditions unsafe."""
        is_safe = weather_client._is_safe_to_observe(
            temp_f=65.0,
            humidity=50.0,
            wind_speed=30.0,
            wind_gust=32.0,
            rain_rate=0.0,
        )
        assert is_safe is False

    def test_unsafe_gust(self, weather_client):
        """Test high gust makes conditions unsafe."""
        is_safe = weather_client._is_safe_to_observe(
            temp_f=65.0,
            humidity=50.0,
            wind_speed=20.0,
            wind_gust=40.0,
            rain_rate=0.0,
        )
        assert is_safe is False

    def test_unsafe_humidity(self, weather_client):
        """Test high humidity makes conditions unsafe."""
        is_safe = weather_client._is_safe_to_observe(
            temp_f=65.0,
            humidity=90.0,
            wind_speed=5.0,
            wind_gust=8.0,
            rain_rate=0.0,
        )
        assert is_safe is False

    def test_unsafe_cold(self, weather_client):
        """Test cold temperature makes conditions unsafe."""
        is_safe = weather_client._is_safe_to_observe(
            temp_f=15.0,  # Below TEMP_MIN_F
            humidity=50.0,
            wind_speed=5.0,
            wind_gust=8.0,
            rain_rate=0.0,
        )
        assert is_safe is False


# =============================================================================
# Calculation Tests
# =============================================================================


class TestCalculations:
    """Tests for weather calculation methods."""

    def test_dew_point_calculation(self, weather_client):
        """Test dew point calculation."""
        # At 70°F and 50% humidity, dew point is approximately 50°F
        dew_point = weather_client._calculate_dew_point(70.0, 50.0)
        assert 48.0 < dew_point < 52.0

    def test_dew_point_high_humidity(self, weather_client):
        """Test dew point at high humidity approaches temperature."""
        dew_point = weather_client._calculate_dew_point(70.0, 95.0)
        assert dew_point > 65.0  # Should be close to temperature

    def test_feels_like_wind_chill(self, weather_client):
        """Test feels-like with wind chill."""
        feels_like = weather_client._calculate_feels_like(
            temp_f=40.0,
            wind_mph=15.0,
            humidity=50.0,
        )
        assert feels_like < 40.0  # Wind chill lowers perceived temp

    def test_feels_like_no_wind(self, weather_client):
        """Test feels-like with no wind."""
        feels_like = weather_client._calculate_feels_like(
            temp_f=65.0,
            wind_mph=0.0,
            humidity=50.0,
        )
        assert feels_like == 65.0  # No change

    def test_wind_direction_string_north(self, weather_client):
        """Test wind direction string for north."""
        direction = weather_client._wind_direction_to_string(0)
        assert direction == "N"

    def test_wind_direction_string_south(self, weather_client):
        """Test wind direction string for south."""
        direction = weather_client._wind_direction_to_string(180)
        assert direction == "S"

    def test_wind_direction_string_east(self, weather_client):
        """Test wind direction string for east."""
        direction = weather_client._wind_direction_to_string(90)
        assert direction == "E"

    def test_wind_direction_string_west(self, weather_client):
        """Test wind direction string for west."""
        direction = weather_client._wind_direction_to_string(270)
        assert direction == "W"

    def test_wind_direction_string_northeast(self, weather_client):
        """Test wind direction string for northeast."""
        direction = weather_client._wind_direction_to_string(45)
        assert direction == "NE"


# =============================================================================
# Sensor Reading Tests (Steps 203-205)
# =============================================================================


class TestSensorReadings:
    """Tests for individual sensor reading methods."""

    def test_sky_quality_with_data(self, weather_client, sample_weather_data):
        """Test sky quality reading with data (Step 203)."""
        weather_client._latest_data = sample_weather_data
        sqm = weather_client.get_sky_quality()
        assert sqm == 21.2

    def test_sky_quality_no_data(self, weather_client):
        """Test sky quality reading without data (Step 203)."""
        sqm = weather_client.get_sky_quality()
        assert sqm is None

    def test_sky_brightness_excellent(self, weather_client, sample_weather_data):
        """Test sky brightness category excellent (Step 203)."""
        sample_weather_data.sky_quality_mpsas = 21.8
        weather_client._latest_data = sample_weather_data
        category = weather_client.get_sky_brightness_category()
        assert category == "excellent"

    def test_sky_brightness_good(self, weather_client, sample_weather_data):
        """Test sky brightness category good (Step 203)."""
        sample_weather_data.sky_quality_mpsas = 21.0
        weather_client._latest_data = sample_weather_data
        category = weather_client.get_sky_brightness_category()
        assert category == "good"

    def test_sky_brightness_fair(self, weather_client, sample_weather_data):
        """Test sky brightness category fair (Step 203)."""
        sample_weather_data.sky_quality_mpsas = 20.0
        weather_client._latest_data = sample_weather_data
        category = weather_client.get_sky_brightness_category()
        assert category == "fair"

    def test_sky_brightness_poor(self, weather_client, sample_weather_data):
        """Test sky brightness category poor (Step 203)."""
        sample_weather_data.sky_quality_mpsas = 18.5
        weather_client._latest_data = sample_weather_data
        category = weather_client.get_sky_brightness_category()
        assert category == "poor"

    def test_rain_sensor_reading(self, weather_client, sample_weather_data):
        """Test rain sensor reading (Step 204)."""
        weather_client._latest_data = sample_weather_data
        rain = weather_client.get_rain_sensor_reading()
        assert rain["rain_rate_in_hr"] == 0.0
        assert rain["is_raining"] is False
        assert rain["sensor_status"] == "ok"

    def test_rain_sensor_no_data(self, weather_client):
        """Test rain sensor reading without data (Step 204)."""
        rain = weather_client.get_rain_sensor_reading()
        assert rain["sensor_status"] == "no_data"

    def test_is_rain_detected_false(self, weather_client, sample_weather_data):
        """Test rain detection false (Step 204)."""
        weather_client._latest_data = sample_weather_data
        assert weather_client.is_rain_detected() is False

    def test_is_rain_detected_true(self, weather_client, unsafe_weather_data):
        """Test rain detection true (Step 204)."""
        weather_client._latest_data = unsafe_weather_data
        assert weather_client.is_rain_detected() is True

    def test_ambient_temperature_celsius(self, weather_client, sample_weather_data):
        """Test ambient temperature in Celsius (Step 205)."""
        weather_client._latest_data = sample_weather_data
        temp = weather_client.get_ambient_temperature()
        assert temp == 22.5

    def test_ambient_temperature_fahrenheit(self, weather_client, sample_weather_data):
        """Test ambient temperature in Fahrenheit (Step 205)."""
        weather_client._latest_data = sample_weather_data
        temp = weather_client.get_ambient_temperature_f()
        assert temp == 72.5

    def test_ambient_temperature_no_data(self, weather_client):
        """Test ambient temperature without data (Step 205)."""
        temp = weather_client.get_ambient_temperature()
        assert temp is None

    def test_is_dew_risk_false(self, weather_client, sample_weather_data):
        """Test dew risk false when temp well above dew point (Step 205)."""
        weather_client._latest_data = sample_weather_data
        assert weather_client.is_dew_risk() is False

    def test_is_dew_risk_true(self, weather_client, sample_weather_data):
        """Test dew risk true when temp near dew point (Step 205)."""
        sample_weather_data.temperature_f = 56.0  # Close to dew_point_f=55.0
        weather_client._latest_data = sample_weather_data
        assert weather_client.is_dew_risk() is True

    def test_temperature_trend_insufficient_history(self, weather_client):
        """Test temperature trend returns None with insufficient history (Step 205)."""
        # With no history, should return None
        trend = weather_client.get_temperature_trend()
        assert trend is None


# =============================================================================
# Temperature History Tests (Step 205)
# =============================================================================


class TestTemperatureHistory:
    """Tests for temperature history tracking (Step 205)."""

    def test_initial_history_empty(self, weather_client):
        """Test temperature history is initially empty."""
        assert len(weather_client._temperature_history) == 0

    def test_record_temperature(self, weather_client):
        """Test recording temperature adds to history."""
        from datetime import datetime
        now = datetime.now()
        weather_client._record_temperature(now, 72.5)
        assert len(weather_client._temperature_history) == 1
        assert weather_client._temperature_history[0] == (now, 72.5)

    def test_record_multiple_temperatures(self, weather_client):
        """Test recording multiple temperatures."""
        from datetime import datetime, timedelta
        base = datetime.now()
        weather_client._record_temperature(base, 70.0)
        weather_client._record_temperature(base + timedelta(seconds=30), 71.0)
        weather_client._record_temperature(base + timedelta(seconds=60), 72.0)
        assert len(weather_client._temperature_history) == 3

    def test_history_max_size_limit(self, weather_client):
        """Test history is trimmed when exceeding max size."""
        from datetime import datetime, timedelta
        weather_client._temperature_history_max_size = 5
        base = datetime.now()
        for i in range(10):
            weather_client._record_temperature(base + timedelta(seconds=i * 30), 70.0 + i)
        assert len(weather_client._temperature_history) == 5
        # Should keep the most recent entries
        assert weather_client._temperature_history[-1][1] == 79.0

    def test_get_temperature_history_default_limit(self, weather_client):
        """Test get_temperature_history with default limit."""
        from datetime import datetime, timedelta
        base = datetime.now()
        for i in range(70):
            weather_client._record_temperature(base + timedelta(seconds=i * 30), 70.0 + i * 0.1)
        history = weather_client.get_temperature_history()
        assert len(history) == 60  # Default limit is 60

    def test_get_temperature_history_custom_limit(self, weather_client):
        """Test get_temperature_history with custom limit."""
        from datetime import datetime, timedelta
        base = datetime.now()
        for i in range(20):
            weather_client._record_temperature(base + timedelta(seconds=i * 30), 70.0)
        history = weather_client.get_temperature_history(limit=10)
        assert len(history) == 10

    def test_clear_temperature_history(self, weather_client):
        """Test clearing temperature history."""
        from datetime import datetime
        weather_client._record_temperature(datetime.now(), 70.0)
        weather_client._record_temperature(datetime.now(), 71.0)
        count = weather_client.clear_temperature_history()
        assert count == 2
        assert len(weather_client._temperature_history) == 0

    def test_temperature_trend_rising(self, weather_client):
        """Test temperature trend detection - rising."""
        from datetime import datetime, timedelta
        now = datetime.now()
        # Add older readings (40-70 minutes ago) - cooler
        for i in range(4):
            weather_client._record_temperature(now - timedelta(minutes=70 - i * 10), 65.0)
        # Add recent readings (0-30 minutes ago) - warmer
        for i in range(4):
            weather_client._record_temperature(now - timedelta(minutes=30 - i * 10), 70.0)
        trend = weather_client.get_temperature_trend(window_minutes=30)
        assert trend == "rising"

    def test_temperature_trend_falling(self, weather_client):
        """Test temperature trend detection - falling."""
        from datetime import datetime, timedelta
        now = datetime.now()
        # Add older readings (40-70 minutes ago) - warmer
        for i in range(4):
            weather_client._record_temperature(now - timedelta(minutes=70 - i * 10), 75.0)
        # Add recent readings (0-30 minutes ago) - cooler
        for i in range(4):
            weather_client._record_temperature(now - timedelta(minutes=30 - i * 10), 70.0)
        trend = weather_client.get_temperature_trend(window_minutes=30)
        assert trend == "falling"

    def test_temperature_trend_stable(self, weather_client):
        """Test temperature trend detection - stable."""
        from datetime import datetime, timedelta
        now = datetime.now()
        # Add older readings (40-70 minutes ago)
        for i in range(4):
            weather_client._record_temperature(now - timedelta(minutes=70 - i * 10), 70.0)
        # Add recent readings (0-30 minutes ago) - same temp
        for i in range(4):
            weather_client._record_temperature(now - timedelta(minutes=30 - i * 10), 70.5)
        trend = weather_client.get_temperature_trend(window_minutes=30)
        assert trend == "stable"

    def test_temperature_trend_needs_both_windows(self, weather_client):
        """Test trend returns None if only one window has data."""
        from datetime import datetime, timedelta
        now = datetime.now()
        # Only add recent readings
        for i in range(4):
            weather_client._record_temperature(now - timedelta(minutes=i * 5), 70.0)
        trend = weather_client.get_temperature_trend(window_minutes=30)
        assert trend is None

    def test_temperature_trend_custom_window(self, weather_client):
        """Test temperature trend with custom window size."""
        from datetime import datetime, timedelta
        now = datetime.now()
        # Add readings for 20-minute windows
        for i in range(4):
            weather_client._record_temperature(now - timedelta(minutes=35 - i * 5), 65.0)
        for i in range(4):
            weather_client._record_temperature(now - timedelta(minutes=15 - i * 5), 70.0)
        trend = weather_client.get_temperature_trend(window_minutes=15)
        assert trend == "rising"


# =============================================================================
# Callback Tests
# =============================================================================


class TestCallbacks:
    """Tests for callback registration."""

    def test_register_callback(self, weather_client):
        """Test callback registration."""

        def my_callback(data):
            pass

        weather_client.register_callback(my_callback)
        assert len(weather_client._callbacks) == 1
        assert weather_client._callbacks[0] == my_callback

    def test_register_multiple_callbacks(self, weather_client):
        """Test multiple callback registration."""

        def callback1(data):
            pass

        def callback2(data):
            pass

        weather_client.register_callback(callback1)
        weather_client.register_callback(callback2)
        assert len(weather_client._callbacks) == 2


# =============================================================================
# Latest Data Property Tests
# =============================================================================


class TestLatestDataProperty:
    """Tests for the latest data property."""

    def test_latest_initially_none(self, weather_client):
        """Test latest data is initially None."""
        assert weather_client.latest is None

    def test_latest_returns_data(self, weather_client, sample_weather_data):
        """Test latest returns stored data."""
        weather_client._latest_data = sample_weather_data
        assert weather_client.latest == sample_weather_data

    def test_latest_safe_to_observe(self, weather_client, sample_weather_data):
        """Test safe_to_observe via latest property."""
        weather_client._latest_data = sample_weather_data
        assert weather_client.latest.safe_to_observe is True

    def test_latest_unsafe_to_observe(self, weather_client, unsafe_weather_data):
        """Test unsafe_to_observe via latest property."""
        weather_client._latest_data = unsafe_weather_data
        assert weather_client.latest.safe_to_observe is False


# =============================================================================
# Pressure History Tests
# =============================================================================


class TestPressureHistory:
    """Tests for pressure history tracking."""

    def test_initial_pressure_history_empty(self, weather_client):
        """Test pressure history is initially empty."""
        assert len(weather_client._pressure_history) == 0

    def test_record_pressure(self, weather_client):
        """Test recording pressure adds to history."""
        from datetime import datetime
        now = datetime.now()
        weather_client._record_pressure(now, 29.92)
        assert len(weather_client._pressure_history) == 1
        assert weather_client._pressure_history[0] == (now, 29.92)

    def test_record_multiple_pressures(self, weather_client):
        """Test recording multiple pressure readings."""
        from datetime import datetime, timedelta
        base = datetime.now()
        weather_client._record_pressure(base, 29.90)
        weather_client._record_pressure(base + timedelta(seconds=30), 29.92)
        weather_client._record_pressure(base + timedelta(seconds=60), 29.94)
        assert len(weather_client._pressure_history) == 3

    def test_pressure_history_max_size_limit(self, weather_client):
        """Test pressure history is trimmed when exceeding max size."""
        from datetime import datetime, timedelta
        weather_client._pressure_history_max_size = 5
        base = datetime.now()
        for i in range(10):
            weather_client._record_pressure(base + timedelta(seconds=i * 30), 29.90 + i * 0.01)
        assert len(weather_client._pressure_history) == 5
        # Should keep the most recent entries
        assert weather_client._pressure_history[-1][1] == 29.99

    def test_get_pressure_history_default_limit(self, weather_client):
        """Test get_pressure_history with default limit."""
        from datetime import datetime, timedelta
        base = datetime.now()
        for i in range(70):
            weather_client._record_pressure(base + timedelta(seconds=i * 30), 29.90 + i * 0.001)
        history = weather_client.get_pressure_history()
        assert len(history) == 60  # Default limit is 60

    def test_get_pressure_history_custom_limit(self, weather_client):
        """Test get_pressure_history with custom limit."""
        from datetime import datetime, timedelta
        base = datetime.now()
        for i in range(20):
            weather_client._record_pressure(base + timedelta(seconds=i * 30), 29.92)
        history = weather_client.get_pressure_history(limit=10)
        assert len(history) == 10

    def test_clear_pressure_history(self, weather_client):
        """Test clearing pressure history."""
        from datetime import datetime
        weather_client._record_pressure(datetime.now(), 29.90)
        weather_client._record_pressure(datetime.now(), 29.92)
        count = weather_client.clear_pressure_history()
        assert count == 2
        assert len(weather_client._pressure_history) == 0

    def test_pressure_trend_rising(self, weather_client):
        """Test pressure trend detection - rising."""
        from datetime import datetime, timedelta
        now = datetime.now()
        # Add older readings (80-120 minutes ago) - lower pressure
        for i in range(4):
            weather_client._record_pressure(now - timedelta(minutes=120 - i * 10), 29.80)
        # Add recent readings (0-60 minutes ago) - higher pressure
        for i in range(4):
            weather_client._record_pressure(now - timedelta(minutes=60 - i * 15), 29.95)
        trend = weather_client.get_pressure_trend(window_minutes=60)
        assert trend == "rising"

    def test_pressure_trend_falling(self, weather_client):
        """Test pressure trend detection - falling."""
        from datetime import datetime, timedelta
        now = datetime.now()
        # Add older readings (80-120 minutes ago) - higher pressure
        for i in range(4):
            weather_client._record_pressure(now - timedelta(minutes=120 - i * 10), 30.10)
        # Add recent readings (0-60 minutes ago) - lower pressure
        for i in range(4):
            weather_client._record_pressure(now - timedelta(minutes=60 - i * 15), 29.85)
        trend = weather_client.get_pressure_trend(window_minutes=60)
        assert trend == "falling"

    def test_pressure_trend_steady(self, weather_client):
        """Test pressure trend detection - steady."""
        from datetime import datetime, timedelta
        now = datetime.now()
        # Add older readings (80-120 minutes ago)
        for i in range(4):
            weather_client._record_pressure(now - timedelta(minutes=120 - i * 10), 29.92)
        # Add recent readings (0-60 minutes ago) - nearly same pressure
        for i in range(4):
            weather_client._record_pressure(now - timedelta(minutes=60 - i * 15), 29.93)
        trend = weather_client.get_pressure_trend(window_minutes=60)
        assert trend == "steady"

    def test_pressure_trend_insufficient_history(self, weather_client):
        """Test pressure trend returns None with insufficient history."""
        # With no history, should return None
        trend = weather_client.get_pressure_trend()
        assert trend is None

    def test_pressure_trend_needs_both_windows(self, weather_client):
        """Test trend returns None if only one window has data."""
        from datetime import datetime, timedelta
        now = datetime.now()
        # Only add recent readings
        for i in range(4):
            weather_client._record_pressure(now - timedelta(minutes=i * 10), 29.92)
        trend = weather_client.get_pressure_trend(window_minutes=60)
        assert trend is None

    def test_pressure_trend_custom_window(self, weather_client):
        """Test pressure trend with custom window size."""
        from datetime import datetime, timedelta
        now = datetime.now()
        # Add readings for 30-minute windows
        for i in range(4):
            weather_client._record_pressure(now - timedelta(minutes=50 - i * 5), 29.80)
        for i in range(4):
            weather_client._record_pressure(now - timedelta(minutes=20 - i * 5), 30.00)
        trend = weather_client.get_pressure_trend(window_minutes=30)
        assert trend == "rising"

    def test_get_pressure_trend_for_data_with_history(self, weather_client):
        """Test _get_pressure_trend_for_data returns trend when history exists."""
        from datetime import datetime, timedelta
        now = datetime.now()
        # Add enough history for trend detection - falling pressure
        for i in range(4):
            weather_client._record_pressure(now - timedelta(minutes=120 - i * 10), 30.00)
        for i in range(4):
            weather_client._record_pressure(now - timedelta(minutes=60 - i * 15), 29.80)
        trend = weather_client._get_pressure_trend_for_data(29.75)
        assert trend == "falling"

    def test_get_pressure_trend_for_data_no_history(self, weather_client):
        """Test _get_pressure_trend_for_data returns steady when no history."""
        trend = weather_client._get_pressure_trend_for_data(29.92)
        assert trend == "steady"

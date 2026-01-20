"""
NIGHTWATCH Configurable Star Field Generator (Step 530)

Generates synthetic star field images for testing astrometry,
focusing, and plate solving without requiring actual sky images.

Features:
- Configurable star density and brightness distribution
- Gaussian PSF with configurable FWHM (seeing simulation)
- Background noise simulation
- Hot pixel and cosmic ray artifacts
- Support for color (RGB) and monochrome images
"""

import logging
import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

logger = logging.getLogger("NIGHTWATCH.StarField")


@dataclass
class Star:
    """A star in the synthetic field."""
    x: float           # X position in pixels
    y: float           # Y position in pixels
    magnitude: float   # Visual magnitude
    flux: float        # Integrated flux (ADU)
    fwhm: float        # FWHM in pixels (seeing)
    color_index: float = 0.0  # B-V color index


@dataclass
class StarFieldConfig:
    """Configuration for star field generation."""
    # Image dimensions
    width: int = 1024
    height: int = 1024
    bit_depth: int = 16  # 8 or 16

    # Star parameters
    num_stars: int = 100
    min_magnitude: float = 6.0   # Brightest stars
    max_magnitude: float = 14.0  # Faintest stars
    magnitude_distribution: str = "uniform"  # uniform, exponential

    # PSF parameters (seeing simulation)
    fwhm_pixels: float = 3.0      # Seeing FWHM in pixels
    fwhm_variation: float = 0.2   # Random variation (+/- 20%)

    # Background
    background_level: float = 500.0   # Mean background ADU
    background_noise: float = 20.0    # Background stddev

    # Artifacts
    hot_pixels: int = 10          # Number of hot pixels
    cosmic_rays: int = 2          # Number of cosmic ray hits
    vignetting: float = 0.0       # Vignetting strength (0-1)

    # Sensor characteristics
    gain: float = 1.0             # e-/ADU
    read_noise: float = 5.0       # Read noise in e-
    dark_current: float = 0.01    # e-/pixel/sec
    exposure_sec: float = 30.0    # Exposure time

    # Color options
    is_color: bool = False        # Generate RGB image
    bayer_pattern: str = "RGGB"   # For debayering simulation


class StarFieldGenerator:
    """
    Generates synthetic star field images (Step 530).

    Creates realistic test images with configurable star density,
    seeing, noise, and artifacts for testing image processing
    and astrometry algorithms.

    Usage:
        config = StarFieldConfig(width=2048, height=2048, num_stars=500)
        generator = StarFieldGenerator(config)
        image = generator.generate()
    """

    def __init__(self, config: Optional[StarFieldConfig] = None):
        """
        Initialize star field generator.

        Args:
            config: Generation configuration
        """
        self.config = config or StarFieldConfig()
        self._stars: List[Star] = []
        self._rng = random.Random()

    def set_seed(self, seed: int):
        """Set random seed for reproducible fields."""
        self._rng.seed(seed)
        random.seed(seed)

    def generate_stars(self) -> List[Star]:
        """
        Generate random star positions and magnitudes.

        Returns:
            List of Star objects
        """
        cfg = self.config
        stars = []

        for _ in range(cfg.num_stars):
            # Random position
            x = self._rng.uniform(0, cfg.width)
            y = self._rng.uniform(0, cfg.height)

            # Random magnitude based on distribution
            if cfg.magnitude_distribution == "exponential":
                # More faint stars than bright (realistic)
                mag = cfg.min_magnitude + (
                    -math.log(self._rng.random()) *
                    (cfg.max_magnitude - cfg.min_magnitude) / 5.0
                )
                mag = min(mag, cfg.max_magnitude)
            else:
                # Uniform distribution
                mag = self._rng.uniform(cfg.min_magnitude, cfg.max_magnitude)

            # Convert magnitude to flux
            # Flux ratio: 10^((m1-m2)/2.5)
            # Reference: mag 10 = 10000 ADU
            flux = 10000.0 * (10.0 ** ((10.0 - mag) / 2.5))

            # Scale by exposure and gain
            flux = flux * cfg.exposure_sec * cfg.gain

            # Random seeing variation
            fwhm = cfg.fwhm_pixels * (1.0 + self._rng.uniform(
                -cfg.fwhm_variation, cfg.fwhm_variation
            ))

            # Random color index (for color images)
            color_index = self._rng.gauss(0.5, 0.3)  # Centered on G-type stars

            stars.append(Star(
                x=x, y=y,
                magnitude=mag,
                flux=flux,
                fwhm=fwhm,
                color_index=color_index
            ))

        self._stars = stars
        logger.info(f"Generated {len(stars)} stars")
        return stars

    def generate(self) -> bytes:
        """
        Generate star field image.

        Returns:
            Image data as bytes (row-major, 8 or 16-bit)
        """
        cfg = self.config

        # Generate stars if not already done
        if not self._stars:
            self.generate_stars()

        # Create image array
        if cfg.bit_depth == 16:
            max_val = 65535
            import array
            image = array.array('H', [0] * (cfg.width * cfg.height))
        else:
            max_val = 255
            image = bytearray(cfg.width * cfg.height)

        # Add background with noise
        self._add_background(image, max_val)

        # Add stars
        self._add_stars(image, max_val)

        # Add artifacts
        self._add_hot_pixels(image, max_val)
        self._add_cosmic_rays(image, max_val)

        # Apply vignetting
        if cfg.vignetting > 0:
            self._apply_vignetting(image, max_val)

        # Convert to bytes
        if cfg.bit_depth == 16:
            return image.tobytes()
        else:
            return bytes(image)

    def _add_background(self, image, max_val: int):
        """Add background level with Gaussian noise."""
        cfg = self.config

        for i in range(len(image)):
            # Background + read noise + dark current
            dark = cfg.dark_current * cfg.exposure_sec * cfg.gain
            noise = self._rng.gauss(0, cfg.background_noise)
            read = self._rng.gauss(0, cfg.read_noise * cfg.gain)

            value = cfg.background_level + dark + noise + read
            value = max(0, min(max_val, int(value)))
            image[i] = value

    def _add_stars(self, image, max_val: int):
        """Add stars with Gaussian PSF."""
        cfg = self.config

        for star in self._stars:
            self._draw_gaussian_star(
                image, star.x, star.y, star.flux, star.fwhm, max_val
            )

    def _draw_gaussian_star(
        self,
        image,
        cx: float,
        cy: float,
        flux: float,
        fwhm: float,
        max_val: int
    ):
        """Draw a single star with Gaussian PSF."""
        cfg = self.config

        # Calculate sigma from FWHM
        sigma = fwhm / 2.355

        # Determine affected pixels (3 sigma radius)
        radius = int(3 * sigma + 1)

        x_min = max(0, int(cx - radius))
        x_max = min(cfg.width, int(cx + radius + 1))
        y_min = max(0, int(cy - radius))
        y_max = min(cfg.height, int(cy + radius + 1))

        # Normalization factor for 2D Gaussian
        norm = flux / (2 * math.pi * sigma * sigma)

        for y in range(y_min, y_max):
            for x in range(x_min, x_max):
                # Distance from star center
                dx = x - cx
                dy = y - cy
                r2 = dx * dx + dy * dy

                # Gaussian profile
                intensity = norm * math.exp(-r2 / (2 * sigma * sigma))

                # Add to pixel with Poisson noise
                if intensity > 0.1:
                    # Simple Poisson approximation
                    intensity += self._rng.gauss(0, math.sqrt(intensity))

                idx = y * cfg.width + x
                new_val = image[idx] + int(intensity)
                image[idx] = min(max_val, max(0, new_val))

    def _add_hot_pixels(self, image, max_val: int):
        """Add random hot pixels."""
        cfg = self.config

        for _ in range(cfg.hot_pixels):
            x = self._rng.randint(0, cfg.width - 1)
            y = self._rng.randint(0, cfg.height - 1)
            idx = y * cfg.width + x

            # Hot pixel at 80-100% of max
            value = int(max_val * self._rng.uniform(0.8, 1.0))
            image[idx] = value

    def _add_cosmic_rays(self, image, max_val: int):
        """Add cosmic ray hits (bright streaks)."""
        cfg = self.config

        for _ in range(cfg.cosmic_rays):
            # Random start position
            x = self._rng.randint(0, cfg.width - 1)
            y = self._rng.randint(0, cfg.height - 1)

            # Random direction and length
            angle = self._rng.uniform(0, 2 * math.pi)
            length = self._rng.randint(3, 15)

            dx = math.cos(angle)
            dy = math.sin(angle)

            for i in range(length):
                px = int(x + i * dx)
                py = int(y + i * dy)

                if 0 <= px < cfg.width and 0 <= py < cfg.height:
                    idx = py * cfg.width + px
                    # Cosmic rays are saturated
                    image[idx] = max_val

    def _apply_vignetting(self, image, max_val: int):
        """Apply vignetting (brightness falloff at edges)."""
        cfg = self.config

        cx = cfg.width / 2
        cy = cfg.height / 2
        max_r = math.sqrt(cx * cx + cy * cy)

        for y in range(cfg.height):
            for x in range(cfg.width):
                # Distance from center
                dx = x - cx
                dy = y - cy
                r = math.sqrt(dx * dx + dy * dy)

                # Vignetting factor (1 at center, decreases at edges)
                factor = 1.0 - cfg.vignetting * (r / max_r) ** 2

                idx = y * cfg.width + x
                image[idx] = int(image[idx] * factor)

    def get_star_catalog(self) -> List[dict]:
        """
        Get catalog of generated stars.

        Returns:
            List of star dictionaries with positions and properties
        """
        return [
            {
                "x": star.x,
                "y": star.y,
                "magnitude": star.magnitude,
                "flux": star.flux,
                "fwhm": star.fwhm,
                "color_index": star.color_index,
            }
            for star in self._stars
        ]

    def generate_with_tracking_error(
        self,
        ra_drift_arcsec: float = 0.0,
        dec_drift_arcsec: float = 0.0,
        plate_scale_arcsec_per_pixel: float = 1.0
    ) -> bytes:
        """
        Generate image with simulated tracking error (elongated stars).

        Args:
            ra_drift_arcsec: RA drift during exposure
            dec_drift_arcsec: Dec drift during exposure
            plate_scale_arcsec_per_pixel: Image scale

        Returns:
            Image with tracking error
        """
        # Convert drift to pixels
        ra_drift_px = ra_drift_arcsec / plate_scale_arcsec_per_pixel
        dec_drift_px = dec_drift_arcsec / plate_scale_arcsec_per_pixel

        # For now, use elongated Gaussian (simplified)
        # A full implementation would use motion blur kernel
        original_fwhm = self.config.fwhm_pixels

        # Increase effective FWHM based on drift
        drift_amount = math.sqrt(ra_drift_px**2 + dec_drift_px**2)
        self.config.fwhm_pixels = math.sqrt(original_fwhm**2 + drift_amount**2)

        # Regenerate with larger FWHM
        self._stars = []
        image = self.generate()

        # Restore original
        self.config.fwhm_pixels = original_fwhm

        return image


# =============================================================================
# Preset configurations
# =============================================================================

def get_dense_field_config() -> StarFieldConfig:
    """Get config for dense star field (e.g., Milky Way region)."""
    return StarFieldConfig(
        num_stars=500,
        min_magnitude=8.0,
        max_magnitude=16.0,
        magnitude_distribution="exponential",
        fwhm_pixels=2.5,
        background_level=800,
    )


def get_sparse_field_config() -> StarFieldConfig:
    """Get config for sparse star field (e.g., high galactic latitude)."""
    return StarFieldConfig(
        num_stars=50,
        min_magnitude=6.0,
        max_magnitude=12.0,
        magnitude_distribution="uniform",
        fwhm_pixels=3.5,
        background_level=300,
    )


def get_focus_test_config() -> StarFieldConfig:
    """Get config for focus testing (few bright stars)."""
    return StarFieldConfig(
        num_stars=10,
        min_magnitude=4.0,
        max_magnitude=8.0,
        fwhm_pixels=5.0,  # Out of focus
        background_level=200,
        background_noise=10,
    )


def get_planetary_field_config() -> StarFieldConfig:
    """Get config for planetary imaging field (high resolution)."""
    return StarFieldConfig(
        width=640,
        height=480,
        num_stars=20,
        min_magnitude=6.0,
        max_magnitude=10.0,
        fwhm_pixels=2.0,
        background_level=100,
        exposure_sec=0.01,  # Short exposure
    )


# =============================================================================
# Main for testing
# =============================================================================

if __name__ == "__main__":
    print("Star Field Generator Test\n")

    # Create generator with default config
    config = StarFieldConfig(
        width=512,
        height=512,
        num_stars=50,
        fwhm_pixels=3.0,
        hot_pixels=5,
        cosmic_rays=2,
    )

    generator = StarFieldGenerator(config)
    generator.set_seed(42)  # Reproducible

    print("Generating star field...")
    image = generator.generate()
    print(f"Generated image: {len(image)} bytes")

    # Get star catalog
    catalog = generator.get_star_catalog()
    print(f"\nGenerated {len(catalog)} stars:")
    for i, star in enumerate(catalog[:5]):
        print(f"  Star {i}: ({star['x']:.1f}, {star['y']:.1f}) "
              f"mag={star['magnitude']:.1f} flux={star['flux']:.0f}")

    if len(catalog) > 5:
        print(f"  ... and {len(catalog) - 5} more")

    # Save to file for inspection
    try:
        from PIL import Image
        import numpy as np

        arr = np.frombuffer(image, dtype=np.uint16).reshape(
            (config.height, config.width)
        )
        # Scale to 8-bit for viewing
        arr8 = (arr / 256).astype(np.uint8)
        img = Image.fromarray(arr8)
        img.save("/tmp/star_field_test.png")
        print(f"\nSaved test image to /tmp/star_field_test.png")
    except ImportError:
        print("\n(PIL/numpy not available for image save)")

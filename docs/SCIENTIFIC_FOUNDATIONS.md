# NIGHTWATCH Scientific Foundations
## Optical Theory and Atmospheric Physics for High-Resolution Planetary Imaging

---

## Document Purpose

This appendix provides the theoretical physics and optical engineering foundations underlying the NIGHTWATCH telescope system design choices. All assertions are grounded in peer-reviewed literature and established optical theory. This document serves as a reference for understanding why specific components were selected and how they interact with atmospheric and detector physics to achieve diffraction-limited planetary imaging.

---

## Table of Contents

1. [Maksutov-Newtonian Optical Theory](#1-maksutov-newtonian-optical-theory)
2. [Central Obstruction and Modulation Transfer Function](#2-central-obstruction-and-modulation-transfer-function)
3. [Wavefront Quality Metrics: Strehl Ratio and the Maréchal Criterion](#3-wavefront-quality-metrics-strehl-ratio-and-the-maréchal-criterion)
4. [Atmospheric Turbulence: Kolmogorov Theory](#4-atmospheric-turbulence-kolmogorov-theory)
5. [Lucky Imaging: Theory and Implementation](#5-lucky-imaging-theory-and-implementation)
6. [Detector Sampling Theory](#6-detector-sampling-theory)
7. [Thermal Equilibrium in Closed-Tube Systems](#7-thermal-equilibrium-in-closed-tube-systems)
8. [References](#8-references)

---

## 1. Maksutov-Newtonian Optical Theory

### 1.1 Historical Development

The Maksutov optical system was first described by Dmitri Dmitrievich Maksutov in his seminal 1944 paper "New Catadioptric Meniscus Systems" published in the *Journal of the Optical Society of America* (Maksutov, 1944). This publication introduced the astronomical community to the use of a thick, steeply curved meniscus lens as a full-aperture corrector for spherical mirrors.

Independently, Albert Bouwers in the Netherlands developed a similar concentric meniscus design in 1940–1941, though his system did not correct chromatic aberration and was limited to monochromatic applications (Bouwers, 1946).

### 1.2 Aberration Correction Mechanism

The Maksutov design exploits a fundamental principle: a meniscus lens with steeply curved surfaces introduces spherical aberration of the *opposite sign* to that produced by a spherical mirror. By careful selection of the meniscus curvatures, thickness, and position, the positive spherical aberration of the corrector precisely cancels the negative spherical aberration of the primary mirror.

The optical path difference (OPD) for spherical aberration in a wavefront can be expressed as:

$$W_{040} = A_{040} \rho^4$$

where $A_{040}$ is the spherical aberration coefficient and $\rho$ is the normalized pupil coordinate. The meniscus corrector is designed such that:

$$A_{040}^{mirror} + A_{040}^{meniscus} \approx 0$$

### 1.3 Chromatic Correction

A key insight of Maksutov's design is that chromatic aberration can be minimized by making the meniscus lens *weakly diverging* overall. The longitudinal chromatic aberration of a thin lens is proportional to its optical power:

$$\delta f_{chrom} = -\frac{f}{V}$$

where $f$ is the focal length and $V$ is the Abbe number of the glass. By using a meniscus with near-zero net power but substantial surface curvature, the Maksutov design achieves chromatic correction far superior to simple achromatic doublets of equivalent aperture.

### 1.4 The Maksutov-Newtonian Configuration

The Maksutov-Newtonian (Mak-Newt) variant routes light to a side-mounted focuser via a flat diagonal secondary mirror, rather than through a hole in the primary (as in the Maksutov-Cassegrain). This configuration offers several advantages:

1. **Reduced central obstruction**: The flat diagonal can be sized for minimal obstruction (~25% by diameter for the MN76) compared to MCT designs (typically 30–35%).

2. **No image shift during focus**: Unlike Cassegrain designs that focus by moving the primary mirror, the Newtonian focuser is mechanically decoupled from the optical train.

3. **Coma correction**: The full-aperture meniscus corrects coma that would otherwise plague fast Newtonian reflectors, enabling f/6 focal ratios with excellent off-axis performance.

### 1.5 Higher-Order Aberrations

The steeply curved surfaces of the Maksutov meniscus generate higher-order aberrations, particularly sixth-order spherical aberration, that cannot be fully cancelled without aspheric surfaces. As noted by Rutten & van Venrooij (1988), the residual higher-order aberration in well-designed Maksutov systems is typically below the diffraction limit for apertures up to ~200mm.

The wavefront error from sixth-order spherical aberration follows:

$$W_{060} = A_{060} \rho^6$$

In optimized Maksutov designs, $|A_{060}| < \lambda/20$ for visible wavelengths, ensuring negligible impact on Strehl ratio.

---

## 2. Central Obstruction and Modulation Transfer Function

### 2.1 The Modulation Transfer Function

The Modulation Transfer Function (MTF) quantifies the ability of an optical system to transfer spatial frequency content from object to image. For a diffraction-limited circular aperture, the MTF is given by the autocorrelation of the pupil function (Goodman, 2005):

$$MTF(\nu) = \frac{2}{\pi}\left[\cos^{-1}\left(\frac{\nu}{\nu_c}\right) - \frac{\nu}{\nu_c}\sqrt{1-\left(\frac{\nu}{\nu_c}\right)^2}\right]$$

where $\nu$ is spatial frequency and $\nu_c = D/(\lambda f)$ is the cutoff frequency, with $D$ the aperture diameter, $\lambda$ the wavelength, and $f$ the focal length.

### 2.2 Effect of Central Obstruction

A central obstruction of linear ratio $\epsilon = d/D$ (secondary diameter to primary diameter) modifies the MTF in a characteristic manner (Schroeder, 2000):

1. **Mid-frequency depression**: Spatial frequencies in the range $0.2\nu_c$ to $0.7\nu_c$ experience reduced modulation transfer.

2. **High-frequency enhancement**: A slight *increase* in MTF occurs near the cutoff frequency $\nu_c$.

3. **Unchanged cutoff**: The theoretical resolution limit (cutoff frequency) remains unchanged.

The integral contrast (IC), defined as the area under the MTF curve, provides a single-number metric for extended object imaging performance. For an obstruction ratio $\epsilon$, the IC is approximately:

$$IC \approx 1 - \epsilon^2$$

For the MN76 with $\epsilon = 0.25$:
$$IC \approx 1 - 0.0625 = 0.9375$$

This represents only a 6.25% reduction in integral contrast compared to an unobstructed aperture.

### 2.3 Practical Impact on Planetary Imaging

The spatial frequency range most critical for planetary detail—Martian surface features, Jovian cloud bands, Saturn's ring divisions—corresponds to mid-range spatial frequencies where the depression from central obstruction is most pronounced.

Boreman (2001) demonstrated that obstructions exceeding 35% cause objectionable degradation of mid-frequency contrast. The MN76's 25% obstruction places it well within acceptable limits, providing contrast transfer superior to most Schmidt-Cassegrain telescopes (33–35% obstruction) and comparable to premium Maksutov-Cassegrains.

A commonly cited rule of thumb (Zmek, 1993) suggests:

$$D_{eff} \approx D - d$$

where $D_{eff}$ is the "effective aperture" for contrast purposes. For the MN76:

$$D_{eff} \approx 178 - 44.5 = 133.5 \text{ mm}$$

This approximation, while not rigorous, provides intuition for the contrast penalty of obstruction.

---

## 3. Wavefront Quality Metrics: Strehl Ratio and the Maréchal Criterion

### 3.1 Definition of Strehl Ratio

The Strehl ratio $S$, introduced by Karl Strehl in 1902, quantifies the peak intensity of the point spread function (PSF) relative to a perfect, aberration-free optical system (Strehl, 1902):

$$S = \frac{I_{max}^{aberrated}}{I_{max}^{perfect}}$$

For an optical system with wavefront aberration $W(\rho, \theta)$ over the pupil, the Strehl ratio can be expressed as:

$$S = \left| \frac{1}{\pi} \int_0^{2\pi} \int_0^1 e^{i k W(\rho, \theta)} \rho \, d\rho \, d\theta \right|^2$$

where $k = 2\pi/\lambda$ is the wavenumber.

### 3.2 The Maréchal Approximation

For small wavefront errors (RMS wavefront error $\sigma_W < \lambda/10$), the Strehl ratio can be approximated by the Maréchal formula (Born & Wolf, 1999):

$$S \approx e^{-(2\pi\sigma_W/\lambda)^2} \approx 1 - (2\pi\sigma_W/\lambda)^2$$

This approximation, derived from a Taylor expansion of the exponential in the diffraction integral, is valid for $S > 0.6$ (Mahajan, 1983).

### 3.3 The Rayleigh and Maréchal Criteria

Lord Rayleigh's quarter-wave criterion states that image quality is "not sensibly degraded" when the maximum wavefront error does not exceed $\lambda/4$ peak-to-valley (P-V). For low-order aberrations like primary spherical aberration, this corresponds to:

$$\sigma_W^{RMS} \approx \frac{\lambda/4}{3.5} \approx 0.071\lambda$$

Substituting into the Maréchal formula:

$$S \approx 1 - (2\pi \times 0.071)^2 \approx 0.80$$

This establishes the **Maréchal criterion**: an optical system is considered "diffraction-limited" when $S \geq 0.80$.

### 3.4 Application to the MN76

Intes Micro specifies their optics at $\lambda/8$ P-V or better, which for typical primary aberrations corresponds to:

$$\sigma_W^{RMS} \approx \frac{\lambda/8}{3.5} \approx 0.036\lambda$$

Yielding a Strehl ratio:

$$S \approx 1 - (2\pi \times 0.036)^2 \approx 0.95$$

Hand-figured examples achieving $\lambda/10$ P-V would yield $S \approx 0.97$, approaching the practical limit for manufacturable optics.

### 3.5 Aberration Budgeting

For a complete optical system, independent aberration sources add in quadrature:

$$\sigma_{total}^2 = \sigma_{optics}^2 + \sigma_{collimation}^2 + \sigma_{thermal}^2 + \sigma_{atmosphere}^2$$

The total Strehl ratio is then:

$$S_{total} = S_{optics} \times S_{collimation} \times S_{thermal} \times S_{atmosphere}$$

This multiplicative relationship emphasizes the importance of controlling all error sources to maintain high image quality.

---

## 4. Atmospheric Turbulence: Kolmogorov Theory

### 4.1 The Kolmogorov-Obukhov Model

The modern understanding of atmospheric turbulence is founded on the work of Kolmogorov (1941) and Obukhov (1949), who established that turbulent energy cascades from large-scale eddies to small-scale eddies following a universal statistical law.

For the refractive index structure function:

$$D_n(r) = \langle [n(\vec{x}) - n(\vec{x} + \vec{r})]^2 \rangle = C_n^2 r^{2/3}$$

where $C_n^2$ is the refractive index structure constant (units: m$^{-2/3}$), characterizing the strength of turbulence.

### 4.2 The Phase Power Spectrum

The three-dimensional power spectrum of refractive index fluctuations follows the Kolmogorov power law (Tatarskii, 1961):

$$\Phi_n(\kappa) = 0.033 C_n^2 \kappa^{-11/3}$$

valid in the inertial range $L_0^{-1} < \kappa < l_0^{-1}$, where $L_0$ (outer scale, typically 10–100m) and $l_0$ (inner scale, typically 1–10mm) bound the turbulent cascade.

The corresponding two-dimensional phase structure function for a wavefront propagating through a turbulent path of length $L$ is:

$$D_\phi(r) = 6.88 \left(\frac{r}{r_0}\right)^{5/3}$$

### 4.3 The Fried Parameter

Fried (1966) introduced the coherence length $r_0$, now universally known as the Fried parameter, defined as:

$$r_0 = \left[ 0.423 k^2 \sec(\zeta) \int_0^L C_n^2(h) \, dh \right]^{-3/5}$$

where $k = 2\pi/\lambda$, $\zeta$ is the zenith angle, and the integral is over the turbulent path.

The Fried parameter has crucial physical interpretations:

1. **Coherence scale**: $r_0$ is the diameter over which the RMS phase variance is approximately 1 radian.

2. **Effective aperture**: For long exposures, a telescope of diameter $D > r_0$ achieves resolution limited by $r_0$, not $D$.

3. **Wavelength dependence**: $r_0 \propto \lambda^{6/5}$, improving significantly at longer wavelengths.

Typical values at good sites: $r_0 = 10–20$ cm at $\lambda = 500$ nm for zenith observations.

### 4.4 The Atmospheric Coherence Time

The coherence time $\tau_0$ characterizes the timescale over which the turbulent phase remains correlated (Roddier, 1981):

$$\tau_0 = 0.314 \frac{r_0}{\bar{v}}$$

where $\bar{v}$ is the effective wind velocity (typically 10–30 m/s weighted by $C_n^2$).

For typical conditions ($r_0 = 10$ cm, $\bar{v} = 15$ m/s):

$$\tau_0 \approx 2.1 \text{ ms}$$

This establishes the exposure time requirement for "freezing" atmospheric turbulence in lucky imaging.

### 4.5 The Isoplanatic Angle

The isoplanatic angle $\theta_0$ defines the angular patch over which the wavefront distortion remains correlated (Fried, 1982):

$$\theta_0 = 0.314 \frac{r_0}{\bar{h}}$$

where $\bar{h}$ is the effective turbulence height. Beyond this angle, anisoplanatism degrades the correlation between wavefronts from different directions.

Fried (1982) showed that the optical transfer function for angular separation $\theta$ is degraded by:

$$MTF(\theta) = MTF(0) \times \exp\left[-\left(\frac{\theta}{\theta_0}\right)^{5/3}\right]$$

For typical conditions, $\theta_0 \approx 2–5$ arcseconds, which comfortably encompasses planetary disks (Mars at opposition: ~25"; Jupiter: ~45").

---

## 5. Lucky Imaging: Theory and Implementation

### 5.1 Fundamental Principle

Lucky imaging exploits the statistical nature of atmospheric turbulence. While long-exposure images are degraded to the seeing limit ($\lambda/r_0$), short exposures occasionally capture moments when the instantaneous wavefront distortion is anomalously small, yielding near-diffraction-limited images.

### 5.2 Fried's Probability Formula

Fried (1978) derived the probability of obtaining a "lucky" short-exposure image:

$$P_{lucky} \approx 5.6 \exp\left[-0.1557\left(\frac{D}{r_0}\right)^2\right] \quad \text{for } D/r_0 \geq 3.5$$

A "lucky" image is defined as one where the integrated squared wavefront error over the aperture is less than 1 radian².

### 5.3 Application to the MN76

For the MN76 with $D = 178$ mm and typical seeing conditions:

| Seeing (arcsec) | $r_0$ (cm) | $D/r_0$ | $P_{lucky}$ |
|-----------------|------------|---------|-------------|
| 1.0" (excellent)| 20         | 8.9     | 0.0003      |
| 1.5" (good)     | 13         | 13.7    | ~10⁻⁹       |
| 2.0" (average)  | 10         | 17.8    | ~10⁻¹⁵      |

These probabilities apply to *diffraction-limited* images. For high-resolution planetary imaging, a more relaxed criterion (Strehl > 0.5) significantly increases the selection yield.

### 5.4 Frame Selection and Stacking

Modern lucky imaging employs several enhancements over Fried's original concept:

1. **Partial correction**: Rather than demanding diffraction-limited frames, selecting the best 1–10% of frames provides substantial resolution improvement with practical data volumes.

2. **Multi-aperture lucky imaging**: For $D >> r_0$, the aperture can be subdivided into $r_0$-sized sub-apertures, each processed independently, then recombined (Law et al., 2006).

3. **Image sharpening metrics**: Frame quality is assessed via contrast metrics (e.g., image entropy, gradient magnitude, Laplacian variance) rather than direct wavefront measurement.

### 5.5 Exposure Time Requirements

For effective lucky imaging, the exposure time $t_{exp}$ must satisfy:

$$t_{exp} < \tau_0$$

to "freeze" the atmospheric turbulence. For $\tau_0 \approx 2–10$ ms at visible wavelengths, exposure times of 10–30 ms are commonly employed, accepting some motion blur in exchange for improved signal-to-noise ratio.

The coherence time scales with wavelength as:

$$\tau_0 \propto \lambda^{6/5}$$

This favors near-infrared imaging, where $\tau_0$ can exceed 20 ms even in moderate seeing.

---

## 6. Detector Sampling Theory

### 6.1 The Nyquist Criterion

The Nyquist-Shannon sampling theorem states that to fully reconstruct a band-limited signal, the sampling frequency must exceed twice the highest frequency present in the signal. For imaging:

$$\Delta x_{pixel} \leq \frac{\lambda f}{2D}$$

where $\Delta x_{pixel}$ is the pixel size, $f$ is the focal length, and $D$ is the aperture diameter. This corresponds to:

$$\theta_{pixel} \leq \frac{\lambda}{2D}$$

in angular terms, or **2 pixels per resolution element** (the Airy disk FWHM).

### 6.2 Critical Sampling for the MN76

For the MN76 at $\lambda = 550$ nm:

- Rayleigh resolution: $\theta_R = 1.22\lambda/D = 0.78"$
- Airy disk FWHM: $\theta_{FWHM} \approx 1.02\lambda/D = 0.65"$
- Nyquist sampling: $\theta_{pixel} \leq 0.33"$/pixel

At the native focal length $f = 1068$ mm:

$$\Delta x_{Nyquist} = \frac{\theta_{pixel} \times f}{206265} = \frac{0.33 \times 1068}{206265} = 1.7 \, \mu\text{m}$$

Modern planetary cameras (2.4–3.75 µm pixels) achieve critical sampling with a 2× Barlow, yielding:

| Camera Pixel | Native Scale | With 2× Barlow |
|--------------|--------------|----------------|
| 2.4 µm       | 0.46"/pixel  | 0.23"/pixel    |
| 2.9 µm       | 0.56"/pixel  | 0.28"/pixel    |
| 3.75 µm      | 0.72"/pixel  | 0.36"/pixel    |

### 6.3 Oversampling Considerations

For lucky imaging, modest oversampling (3–4 pixels per FWHM) is beneficial:

1. **Sub-pixel registration**: Image stacking algorithms can align frames to sub-pixel precision when oversampled.

2. **Drizzle reconstruction**: The "drizzle" algorithm (Fruchter & Hook, 2002) can recover resolution beyond the detector limit when combining many dithered frames.

3. **Deconvolution headroom**: Wavelet sharpening and deconvolution algorithms perform better on oversampled data.

### 6.4 Signal-to-Noise Considerations

The SNR for planetary imaging is:

$$SNR = \frac{N_*}{\sqrt{N_* + n_{pix}(N_{sky} + N_{dark} + N_{read}^2)}}$$

where $N_*$ is signal electrons, $n_{pix}$ is the number of pixels in the measurement aperture, and $N_{sky}$, $N_{dark}$, $N_{read}$ are sky background, dark current, and read noise contributions.

For bright planets, $N_* >> n_{pix} N_{read}^2$, and SNR approaches $\sqrt{N_*}$ (shot noise limited). This permits the short exposures (10–30 ms) required for lucky imaging without SNR penalty.

---

## 7. Thermal Equilibrium in Closed-Tube Systems

### 7.1 The Thermal Boundary Layer Problem

When a telescope mirror is warmer than ambient air, a boundary layer of heated air rises from the mirror surface, creating local turbulence that degrades image quality. This "mirror seeing" can dominate optical aberrations even in excellent atmospheric conditions.

The temperature differential required to induce significant degradation is surprisingly small. Racine (1984) demonstrated that image quality degrades noticeably when:

$$\Delta T_{mirror-air} > 1°\text{C}$$

For professional telescopes, requirements are more stringent. The Gemini telescopes specify (Gemini Observatory, 1994):

- Mirror warmer than ambient: $\Delta T < 0.2°$C
- Mirror cooler than ambient: $\Delta T < 0.6°$C

The asymmetry reflects that warm mirrors are more problematic (rising convective plumes) than cool mirrors (stable stratification).

### 7.2 Thermal Time Constant

The characteristic time for a glass mirror to equilibrate with ambient temperature is:

$$\tau_{thermal} = \frac{\rho c_p t^2}{k}$$

where $\rho$ is density, $c_p$ is specific heat capacity, $t$ is mirror thickness, and $k$ is thermal conductivity.

For Pyrex/borosilicate glass ($k \approx 1.1$ W/m·K, $\rho c_p \approx 1.9 \times 10^6$ J/m³·K):

| Mirror Thickness | $\tau_{thermal}$ |
|------------------|------------------|
| 20 mm            | ~12 minutes      |
| 30 mm            | ~27 minutes      |
| 50 mm            | ~75 minutes      |

These are characteristic times; practical equilibration to within 1°C requires 2–3 time constants.

### 7.3 Advantages of Closed-Tube Design

The Maksutov-Newtonian's sealed tube provides several thermal advantages:

1. **Isolation from tube currents**: Unlike open-tube Newtonians, air cannot flow freely through the tube, eliminating convective tube currents.

2. **Thermal buffering**: The meniscus corrector acts as a thermal buffer, slowing the rate of temperature change seen by the primary mirror.

3. **Equilibration path**: The enclosed air volume equilibrates with the tube walls, which in turn equilibrate with ambient conditions. This staged process reduces thermal shock to the primary mirror.

4. **Dust protection**: Sealed tubes prevent dust accumulation on optical surfaces, eliminating the need for frequent cleaning that can degrade coatings.

### 7.4 Application to Permanent Installation

For NIGHTWATCH's permanent pier installation in Nevada, thermal considerations are favorable:

- The telescope remains outdoors, pre-equilibrating during the day
- Desert environments have predictable diurnal temperature cycles
- No thermal shock from moving between indoor storage and outdoor use
- Active cooling (fans) can accelerate equilibration if needed before a session

---

## 8. References

### Foundational Optics Texts

- Born, M., & Wolf, E. (1999). *Principles of Optics* (7th ed.). Cambridge University Press.
- Goodman, J. W. (2005). *Introduction to Fourier Optics* (3rd ed.). Roberts & Company.
- Schroeder, D. J. (2000). *Astronomical Optics* (2nd ed.). Academic Press.

### Telescope Design

- Maksutov, D. D. (1944). New catadioptric meniscus systems. *Journal of the Optical Society of America*, 34(5), 270–284.
- Bouwers, A. (1946). *Achievements in Optics*. Elsevier.
- Rutten, H. G. J., & van Venrooij, M. A. M. (1988). *Telescope Optics: Evaluation and Design*. Willmann-Bell.

### Image Quality Metrics

- Strehl, K. (1902). Über Luftschlieren und Zonenfehler. *Zeitschrift für Instrumentenkunde*, 22, 213–217.
- Maréchal, A. (1947). Étude des effets combinés de la diffraction et des aberrations géométriques sur l'image d'un point lumineux. *Revue d'Optique*, 26, 257–277.
- Mahajan, V. N. (1983). Strehl ratio for primary aberrations in terms of their aberration variance. *Journal of the Optical Society of America*, 73(6), 860–861.
- Mahajan, V. N. (1982). Strehl ratio for primary aberrations: some analytical results for circular and annular pupils. *Journal of the Optical Society of America*, 72(9), 1258–1266.

### Modulation Transfer Function

- Boreman, G. D. (2001). *Modulation Transfer Function in Optical and Electro-Optical Systems*. SPIE Press.
- Zmek, W. (1993). Rules of thumb for planetary scopes. *Sky & Telescope*, 86(1), 91–93; 86(3), 92–94.

### Atmospheric Turbulence

- Kolmogorov, A. N. (1941). The local structure of turbulence in incompressible viscous fluid for very large Reynolds numbers. *Doklady Akademii Nauk SSSR*, 30, 301–305.
- Tatarskii, V. I. (1961). *Wave Propagation in a Turbulent Medium*. McGraw-Hill.
- Fried, D. L. (1966). Optical resolution through a randomly inhomogeneous medium for very long and very short exposures. *Journal of the Optical Society of America*, 56(10), 1372–1379.
- Roddier, F. (1981). The effects of atmospheric turbulence in optical astronomy. *Progress in Optics*, 19, 281–376.

### Lucky Imaging

- Fried, D. L. (1978). Probability of getting a lucky short-exposure image through turbulence. *Journal of the Optical Society of America*, 68(12), 1651–1658.
- Law, N. M., Mackay, C. D., & Baldwin, J. E. (2006). Lucky imaging: high angular resolution imaging in the visible from the ground. *Astronomy & Astrophysics*, 446(2), 739–745.

### Isoplanatism and Adaptive Optics

- Fried, D. L. (1982). Anisoplanatism in adaptive optics. *Journal of the Optical Society of America*, 72(1), 52–61.

### Thermal Effects

- Racine, R. (1984). Mirror, dome, and natural seeing at CFHT. *Publications of the Astronomical Society of the Pacific*, 96(584), 649–655.
- Gemini Observatory. (1994). *Gemini Primary Mirror Thermal Control System Requirements*.

### Sampling and Detection

- Fruchter, A. S., & Hook, R. N. (2002). Drizzle: A method for the linear reconstruction of undersampled images. *Publications of the Astronomical Society of the Pacific*, 114(792), 144–152.

---

## Appendix A: Derived Parameters for NIGHTWATCH

### A.1 Optical System Parameters

| Parameter | Value | Derivation |
|-----------|-------|------------|
| Aperture ($D$) | 178 mm | MN76 specification |
| Focal length ($f$) | 1068 mm | MN76 specification |
| Focal ratio | f/6 | $f/D$ |
| Central obstruction ($\epsilon$) | 0.25 | Secondary/primary diameter |
| Rayleigh resolution | 0.78" | $1.22\lambda/D$ at 550 nm |
| Dawes limit | 0.65" | $116/D_{mm}$ empirical |
| Cutoff frequency | 1.82 cy/arcsec | $D/\lambda$ |

### A.2 Diffraction-Limited Performance

| Parameter | Value | Notes |
|-----------|-------|-------|
| Airy disk diameter | 1.56" | $2.44\lambda/D$ at 550 nm |
| First dark ring | 0.78" radius | |
| Peak Strehl (spec) | 0.95 | For $\lambda/8$ P-V optics |
| Integral contrast | 0.94 | For 25% obstruction |

### A.3 Atmospheric Parameters (Typical Nevada Site)

| Parameter | Value | Conditions |
|-----------|-------|------------|
| $r_0$ | 10–15 cm | Good seeing nights |
| $\tau_0$ | 3–8 ms | Moderate wind |
| $\theta_0$ | 2–4" | Single layer approximation |
| $D/r_0$ | 12–18 | Sets lucky imaging probability |

### A.4 Sampling Requirements

| Configuration | Image Scale | Sampling |
|---------------|-------------|----------|
| Native, 2.9µm pixel | 0.56"/pixel | 1.4× FWHM |
| 2× Barlow, 2.9µm pixel | 0.28"/pixel | 2.8× FWHM (optimal) |
| 3× Barlow, 2.9µm pixel | 0.19"/pixel | 4.1× FWHM (oversampled) |

---

*Document version: 1.0*
*Created: 2026-01-19*
*Author: NIGHTWATCH Project*

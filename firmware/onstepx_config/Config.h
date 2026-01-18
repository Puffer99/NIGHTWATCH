// NIGHTWATCH OnStepX Configuration
// Autonomous Mak-Newt Observatory System
// Central Nevada Dark Sky Installation
//
// Hardware: Teensy 4.1 + TMC5160 drivers + harmonic drives
// OTA: Intes-Micro MN78 (178mm f/6 Mak-Newt)
// Mount: DIY GEM with CSF-32-100 (RA) and CSF-25-80 (DEC)

#pragma once

// =============================================================================
// PINMAP SELECTION
// =============================================================================
// Select the appropriate pinmap for Teensy 4.1
#define PINMAP                      PINMAP_TEENSY41

// =============================================================================
// SERIAL PORTS
// =============================================================================
#define SERIAL_A_BAUD_DEFAULT       9600       // LX200 protocol
#define SERIAL_B_BAUD_DEFAULT       57600      // Debugging
#define SERIAL_B                    Serial     // USB serial

// =============================================================================
// MOUNT TYPE
// =============================================================================
#define MOUNT_TYPE                  GEM        // German Equatorial Mount
#define MOUNT_COORDS                OBSERVED_PLACE

// =============================================================================
// AXIS 1 (RA) CONFIGURATION
// =============================================================================
// Motor: NEMA17 1.8°/step + 27:1 planetary gearbox
// Drive: CSF-32-100 harmonic drive (100:1 ratio)
// Total reduction: 200 steps × 16 microsteps × 27 × 100 = 8,640,000 steps/revolution

#define AXIS1_DRIVER_MODEL          TMC5160
#define AXIS1_DRIVER_MICROSTEPS     16
#define AXIS1_DRIVER_MICROSTEPS_GOTO 4         // Lower microstepping for faster slews
#define AXIS1_DRIVER_IHOLD          600        // mA holding current
#define AXIS1_DRIVER_IRUN           1200       // mA running current
#define AXIS1_DRIVER_IGOTO          1500       // mA goto current
#define AXIS1_DRIVER_STATUS         ON
#define AXIS1_DRIVER_DECAY          STEALTHCHOP
#define AXIS1_DRIVER_DECAY_GOTO     SPREADCYCLE

// Steps per degree calculation:
// (200 steps/rev × 16 microsteps × 27 gearbox × 100 harmonic) / 360° = 24,000 steps/°
#define AXIS1_STEPS_PER_DEGREE      24000.0

#define AXIS1_REVERSE               OFF        // Adjust based on motor wiring
#define AXIS1_POWER_DOWN            OFF        // Keep motor powered
#define AXIS1_SLEW_RATE_DESIRED     4.0        // degrees/second
#define AXIS1_ACCELERATION_TIME     3          // seconds to reach slew rate
#define AXIS1_RAPID_STOP_TIME       2          // seconds for emergency stop

// RA Limits
#define AXIS1_LIMIT_MIN             -180       // degrees
#define AXIS1_LIMIT_MAX             180        // degrees

// RA Encoder (motor-side AMT103-V)
#define AXIS1_ENCODER               AB
#define AXIS1_ENCODER_ORIGIN        0
#define AXIS1_ENCODER_PPR           8192

// =============================================================================
// AXIS 2 (DEC) CONFIGURATION
// =============================================================================
// Motor: NEMA17 1.8°/step + 27:1 planetary gearbox
// Drive: CSF-25-80 harmonic drive (80:1 ratio)
// Total reduction: 200 steps × 16 microsteps × 27 × 80 = 6,912,000 steps/revolution

#define AXIS2_DRIVER_MODEL          TMC5160
#define AXIS2_DRIVER_MICROSTEPS     16
#define AXIS2_DRIVER_MICROSTEPS_GOTO 4
#define AXIS2_DRIVER_IHOLD          600
#define AXIS2_DRIVER_IRUN           1200
#define AXIS2_DRIVER_IGOTO          1500
#define AXIS2_DRIVER_STATUS         ON
#define AXIS2_DRIVER_DECAY          STEALTHCHOP
#define AXIS2_DRIVER_DECAY_GOTO     SPREADCYCLE

// Steps per degree calculation:
// (200 steps/rev × 16 microsteps × 27 gearbox × 80 harmonic) / 360° = 19,200 steps/°
#define AXIS2_STEPS_PER_DEGREE      19200.0

#define AXIS2_REVERSE               OFF
#define AXIS2_POWER_DOWN            OFF
#define AXIS2_SLEW_RATE_DESIRED     4.0
#define AXIS2_ACCELERATION_TIME     3
#define AXIS2_RAPID_STOP_TIME       2

// DEC Limits
#define AXIS2_LIMIT_MIN             -90        // degrees
#define AXIS2_LIMIT_MAX             90         // degrees

// DEC Encoder (motor-side AMT103-V)
#define AXIS2_ENCODER               AB
#define AXIS2_ENCODER_ORIGIN        0
#define AXIS2_ENCODER_PPR           8192

// =============================================================================
// TRACKING
// =============================================================================
#define TRACK_AUTOSTART             ON         // Start tracking automatically
#define TRACK_REFRACTION_TYPE       REFRAC_CALC_FULL
#define TRACK_BACKLASH_RATE         25         // x sidereal for backlash takeup

// =============================================================================
// GOTO BEHAVIOR
// =============================================================================
#define GOTO_FEATURE                ON
#define GOTO_RATE                   4.0        // degrees/second max
#define GOTO_ACCELERATION           2.0        // degrees/second²
#define GOTO_OFFSET_ALIGN           AUTO

// =============================================================================
// PIER SIDE / MERIDIAN FLIP
// =============================================================================
#define PIER_SIDE_PREFERRED         BEST
#define PIER_SIDE_SYNC_CHANGE       OFF
#define AXIS1_PAST_MERIDIAN_LIMIT_E 15         // degrees past meridian (east)
#define AXIS1_PAST_MERIDIAN_LIMIT_W 15         // degrees past meridian (west)

// =============================================================================
// PARK POSITIONS
// =============================================================================
#define PARK_STRICT                 ON
#define PARK_STATUS_PRESERVED       ON

// =============================================================================
// HOMING (with absolute encoders)
// =============================================================================
#define HOME_AUTOMATIC              ON
// AS5600 absolute encoders on output shafts will be configured separately

// =============================================================================
// SITE LOCATION (Central Nevada)
// =============================================================================
#define SITE_LATITUDE_DEFAULT       39.0       // Approximate latitude
#define SITE_LONGITUDE_DEFAULT      -117.0     // Approximate longitude
#define SITE_ELEVATION_DEFAULT      1800       // meters (about 6000 ft)

// =============================================================================
// TIMEZONE
// =============================================================================
#define TIME_ZONE_DEFAULT           -8         // PST

// =============================================================================
// NETWORK (Ethernet on Teensy 4.1)
// =============================================================================
#define SERIAL_IP_MODE              ETHERNET
#define ETHERNET_W5500              OFF        // Teensy 4.1 has native Ethernet
#define ETHERNET_CS_PIN             10
#define ETHERNET_RESET_PIN          9

// IP Configuration (adjust for your network)
#define ETHERNET_IP                 {192, 168, 1, 100}
#define ETHERNET_GATEWAY            {192, 168, 1, 1}
#define ETHERNET_SUBNET             {255, 255, 255, 0}
#define ETHERNET_DNS                {8, 8, 8, 8}
#define ETHERNET_HTTP_PORT          80
#define ETHERNET_CMD_PORT           9999

// =============================================================================
// WEATHER SAFETY (integration hooks)
// =============================================================================
// Weather integration handled by external DGX Spark automation
// Mount will respond to park commands from safety controller

// =============================================================================
// PERIODIC ERROR CORRECTION
// =============================================================================
#define PEC_SENSE_STATE             HIGH
#define PEC_SENSE_ON                OFF        // No PEC sense hardware
#define PEC_BUFFER_SIZE             824        // Steps for one worm revolution
                                               // Adjust based on actual worm gear

// =============================================================================
// ROTATOR (not installed - future expansion)
// =============================================================================
#define ROTATOR                     OFF

// =============================================================================
// FOCUSER (not installed - future expansion)
// =============================================================================
#define FOCUSER1                    OFF
#define FOCUSER2                    OFF

// =============================================================================
// AUXILIARY FEATURES
// =============================================================================
#define LED_STATUS                  ON
#define LED_STATUS_PIN              13         // Built-in Teensy LED
#define BUZZER                      OFF        // Remote site, no neighbors
#define BUZZER_PIN                  OFF

// =============================================================================
// DEBUG OPTIONS
// =============================================================================
#define DEBUG                       OFF        // Set ON for troubleshooting
#define DEBUG_ECHO_COMMANDS         OFF
#define DEBUG_SERVO                 OFF
#define DEBUG_STEPPER               OFF

// =============================================================================
// NOTES FOR NIGHTWATCH BUILD
// =============================================================================
//
// 1. TMC5160 DRIVER WIRING:
//    - Use SPI mode for full parameter control
//    - Watterott TMC5160 v1.3+: Ground CLK pin, cut off socket pin
//    - BigTreeTech TMC5160 v1.2: Only cut CLK pin
//
// 2. ENCODER WIRING:
//    - AMT103-V: A/B quadrature signals to Teensy GPIO
//    - AS5600: I2C bus (future axis-side absolute encoders)
//
// 3. MOTOR CALCULATIONS VERIFIED:
//    - RA tracking: 24000 steps/° × 360° / 86164s = 100.3 steps/s
//    - Well within Teensy/TMC5160 capability
//
// 4. HARMONIC DRIVE NOTES:
//    - CSF-32-100: RA axis, 127 Nm torque rating
//    - CSF-25-80: DEC axis, 70 Nm torque rating
//    - Pre-lubricated, minimal maintenance
//
// 5. NETWORK ACCESS:
//    - Ethernet preferred for reliability
//    - LX200 protocol on port 9999
//    - HTTP web interface on port 80
//    - WiFi backup possible with external module
//
// =============================================================================

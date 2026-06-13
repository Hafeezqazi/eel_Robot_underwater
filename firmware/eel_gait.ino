/*
 * eel_gait.ino  --  ESP32 anguilliform swim controller.
 *
 * Drives 4 waterproof servos -- 3 front body joints + 1 dive plane --
 * through a PCA9685 16-ch PWM driver to produce a travelling body wave
 * (the rear 2 joints are a passive compliant tail, no servo). This is
 * the firmware port of firmware/gait.py -- keep the two in sync.
 *
 *   theta_i(t) = A_i * sin(2*pi*f*t - phi_i) + heading
 *
 * Hardware:
 *   ESP32 dev board (3V3 logic)
 *   PCA9685 servo driver  (I2C: SDA=21, SCL=22), V+ = servo BEC 5-6V
 *   3x waterproof metal-gear servos on channels 0..2 (front driven joints;
 *       the rear 2 joints are a passive compliant tail, no servo)
 *   1x dive-plane servo on channel 5 (bow planes, active depth control)
 *   MS5837 depth sensor (I2C 0x76) for depth-hold; leak sensor on GPIO34
 *   White LED headlight behind the nose window: logic-level MOSFET gate
 *       on GPIO25 (PWM-dimmed; do NOT drive the LED from the pin directly)
 *   Analog FPV camera: powered from the 5V rail, video goes topside on a
 *       spare tether pair (no firmware involvement)
 *   Power: 12 V down the tether -> robot-local bucks (5-6 V servo bus + a
 *       SEPARATE 5 V MCU buck); USB-serial console on a spare pair.
 *       (Do NOT send 5-6 V down the tether -- see analysis/power.py.)
 *
 * Serial protocol (115200 baud), one command per line:
 *   S <0..1>      set speed scale (0 = stop, 1 = full beat freq)
 *   H <-30..30>   manual steering bias in degrees (turn), heading-hold off
 *   Y <deg>       HOLD heading (closed-loop on the IMU yaw)
 *   M             manual steering (heading-hold off)
 *   D <0..2>      engage depth-hold at target depth (metres)
 *   L             level the dive planes (depth-hold off)
 *   W <0..1>      white headlight brightness (0 = off, 1 = full)
 *   X             emergency stop (center all, freq 0; light stays as set)
 *
 * SAFETY: if the leak sensor trips, the gait halts and all servos centre.
 *
 * Toolchain (pin these -- the source is NOT compile-verified in this repo's CI,
 * which only runs the Python pipeline; treat it as "source updated", compile it
 * yourself before trusting it):
 *   - ESP32 Arduino core 2.0.x   (3.x changed the ledc PWM API used here)
 *   - Adafruit PWM Servo Driver Library  (PCA9685)
 *   - BlueRobotics MS5837 Library  (depth/pressure)
 *   - Wire (bundled)
 *   compile: arduino-cli compile --fqbn esp32:esp32:esp32 firmware/eel_gait.ino
 *
 * STATUS: depth-hold + heading-hold are CLOSED-LOOP but BENCH-UNTESTED.
 * Depth-hold is refused unless the MS5837 inits; heading-hold is refused unless
 * the MPU6050 answers; heading is gyro-only and DRIFTS (add a magnetometer for
 * absolute heading). Treat both as experimental until verified on the bench.
 */

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include "MS5837.h"                       // BlueRobotics MS5837 depth/pressure

// ---- geometry / gait constants (mirror cad/params.py + firmware/gait.py) ----
// Only the FRONT 3 joints carry servos; the rear 2 are a passive compliant
// tail that flexes to the body wave on its own (no actuator).
const int   N_DRIVEN        = 3;         // driven servos (front joints)
const int   N_BODY_JOINTS   = 5;         // total joints in the body wave
const float JOINT_TRAVEL    = 28.0f;     // deg, mechanical +/- limit
const float CRUISE_AMP_DEG  = 7.0f;      // deg, peak per-joint cruise amplitude
const float BASE_FREQ_HZ    = 2.00f;     // Hz, cruise tail-beat frequency
const float BODY_LENGTH_M   = 0.500f;

// axial stations of the 3 DRIVEN joints (mm) -> phase lags phi_i (rad)
const float JOINT_Z_MM[N_DRIVEN] = {140, 200, 260};
float       PHI[N_DRIVEN];               // filled in setup()
// amplitude envelope A_i (deg): grows toward the tail (over all 5 joints)
float       AMP[N_DRIVEN];

// ---- servo calibration (per channel; tune on the bench) ----
const int   SERVO_CENTER_US = 1500;      // neutral pulse
const float US_PER_DEG      = 10.0f;     // pulse change per command degree
const int   SERVO_MIN_US    = 1000;
const int   SERVO_MAX_US    = 2000;

// ---- dive planes (4th servo, PCA channel 5) ----
const int   DIVE_CH         = 5;         // PCA9685 channel for the dive servo
const float DIVE_MAX_DEG    = 25.0f;     // +/- plane limit (+ = dive)
const float DEPTH_KP        = 12.0f;     // deg per metre of error
const float DEPTH_KD        = 8.0f;      // deg per (m/s)
// water density for the depth conversion -- MUST match params.py WATER:
//   fresh = 997, salt ~ 1029 kg/m^3 (deeper-reading if set too low)
const float FLUID_DENSITY   = 997.0f;    // kg/m^3 (params.WATER = "fresh")

// ---- IMU heading hold (MPU6050 @ I2C 0x68) ----
const int   MPU_ADDR        = 0x68;
const int   MPU_WHOAMI      = 0x75;      // identity register (reads 0x68)
const float GYRO_LSB        = 131.0f;    // LSB per deg/s (+/-250 dps range)
const float HEAD_KP         = 0.6f;      // joint-bias deg per heading-deg error
const float HEAD_KD         = 4.0f;      // deg per (deg/s)
const float HEAD_MAX        = 18.0f;     // max steering bias (deg)

// ---- pins ----
const int   PIN_LEAK        = 34;        // leak probe (HIGH = water detected)
const int   PIN_LED         = 25;        // headlight MOSFET gate (PWM)
const int   LED_CH          = 0;         // LEDC channel for the headlight
const int   LED_PWM_FREQ    = 5000;      // Hz
const int   LED_PWM_BITS    = 8;         // 0..255 duty
const int   PCA_FREQ_HZ     = 50;        // standard analog-servo frame rate

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);
MS5837  depthSensor;                     // BlueRobotics MS5837-30BA
bool    g_depthOk = false;               // true once the sensor inits OK
bool    g_imuOk   = false;               // true once the MPU6050 answers

float   g_speed   = 0.0f;                // 0..1 speed scale (start stopped)
float   g_heading = 0.0f;                // deg steering bias
bool    g_estop   = false;
uint32_t g_t0     = 0;

float   g_targetDepth = 0.0f;            // m, commanded depth (0 = surface)
bool    g_depthHold   = false;           // depth-hold engaged?
float   g_prevDepthErr = 0.0f;
uint32_t g_prevDepthMs = 0;

float    g_yaw          = 0.0f;          // integrated heading (deg)
float    g_gyroZbias    = 0.0f;          // calibrated gyro-Z zero (raw LSB)
float    g_targetHeading = 0.0f;
bool     g_headingHold  = false;
float    g_prevHeadErr  = 0.0f;
uint32_t g_prevHeadMs   = 0;
uint32_t g_prevHeadCtrlMs = 0;           // separate timer for the heading PD dt

// Cached depth (metres) from the MS5837. The conversion is blocking (~40 ms),
// so we rate-limit the poll rather than read every control cycle. Returns NAN
// if the sensor never initialised -> callers must treat NAN as "no authority".
float readDepth() {
  static uint32_t lastMs = 0;
  static float cached = 0.0f;
  if (!g_depthOk) return NAN;
  uint32_t now = millis();
  if (now - lastMs >= 100) {              // ~10 Hz sensor poll
    depthSensor.read();
    cached = depthSensor.depth();         // m, uses the set fluid density
    lastMs = now;
  }
  return cached;
}

// PD depth controller -> dive-plane angle (deg, + = dive). No authority at
// zero forward speed (planes need flow), and none without a working sensor.
float diveAngleFromDepth() {
  float depth = readDepth();
  if (isnan(depth)) { g_depthHold = false; return 0.0f; }  // no sensor -> level
  uint32_t now = millis();
  float dt = (now - g_prevDepthMs) / 1000.0f;
  if (dt <= 0.0f) dt = 0.02f;
  g_prevDepthMs = now;
  float err = g_targetDepth - depth;            // +err -> go deeper -> dive
  float derr = (err - g_prevDepthErr) / dt;
  g_prevDepthErr = err;
  float ang = DEPTH_KP * err + DEPTH_KD * derr;
  if (ang >  DIVE_MAX_DEG) ang =  DIVE_MAX_DEG;
  if (ang < -DIVE_MAX_DEG) ang = -DIVE_MAX_DEG;
  return ang;
}

// ---- MPU6050 gyro-Z (yaw) -> heading hold ----
float wrap180(float a){ while(a>180.0f)a-=360.0f; while(a<-180.0f)a+=360.0f; return a; }

int16_t readGyroZraw() {
  Wire.beginTransmission(MPU_ADDR); Wire.write(0x47);   // GYRO_ZOUT_H
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 2, true);
  int16_t v = (Wire.read() << 8) | Wire.read();
  return v;
}

void mpuInit() {
  // identity check FIRST -> gate heading-hold on a real, answering IMU
  Wire.beginTransmission(MPU_ADDR); Wire.write(MPU_WHOAMI);
  if (Wire.endTransmission(false) != 0) { g_imuOk = false; return; }
  Wire.requestFrom(MPU_ADDR, 1, true);
  uint8_t who = Wire.available() ? Wire.read() : 0xFF;
  if (who != 0x68) { g_imuOk = false; return; }    // not an MPU6050 -> no IMU
  Wire.beginTransmission(MPU_ADDR); Wire.write(0x6B); Wire.write(0x00); // wake
  Wire.endTransmission(true);
  delay(50);
  long sum = 0; const int N = 400;                 // calibrate zero (hold still)
  for (int i = 0; i < N; i++) { sum += readGyroZraw(); delay(2); }
  g_gyroZbias = sum / (float)N;
  g_prevHeadMs = millis();
  g_imuOk = true;
}

void updateHeading() {
  if (!g_imuOk) return;                             // no IMU -> yaw stays 0
  uint32_t now = millis();
  float dt = (now - g_prevHeadMs) / 1000.0f;
  if (dt <= 0.0f) dt = 0.02f;
  g_prevHeadMs = now;
  float rateZ = (readGyroZraw() - g_gyroZbias) / GYRO_LSB;   // deg/s
  g_yaw += rateZ * dt;                                       // integrate
}

// PD heading controller -> joint steering bias (deg). Gyro-only yaw drifts;
// add a compass (MPU9250/HMC5883) for absolute long-term heading.
float headingBias() {
  uint32_t now = millis();
  float dt = (now - g_prevHeadCtrlMs) / 1000.0f;
  if (dt <= 0.0f) dt = 0.02f;
  g_prevHeadCtrlMs = now;
  float err = wrap180(g_targetHeading - g_yaw);
  float derr = (err - g_prevHeadErr) / dt;       // deg/s (HEAD_KD units); was
  g_prevHeadErr = err;                            // missing /dt -> rate-dependent
  float b = HEAD_KP * err + HEAD_KD * derr;
  if (b >  HEAD_MAX) b =  HEAD_MAX;               // output saturation
  if (b < -HEAD_MAX) b = -HEAD_MAX;
  return b;
}

// map command angle (deg) -> PCA9685 "tick" (12-bit @ PCA_FREQ_HZ)
int angleToTick(float angle_deg) {
  if (angle_deg >  JOINT_TRAVEL) angle_deg =  JOINT_TRAVEL;
  if (angle_deg < -JOINT_TRAVEL) angle_deg = -JOINT_TRAVEL;
  float us = SERVO_CENTER_US + US_PER_DEG * angle_deg;
  if (us < SERVO_MIN_US) us = SERVO_MIN_US;
  if (us > SERVO_MAX_US) us = SERVO_MAX_US;
  // ticks = us / (1e6 / PCA_FREQ_HZ / 4096)
  float us_per_tick = 1000000.0f / (PCA_FREQ_HZ * 4096.0f);
  return (int)(us / us_per_tick + 0.5f);
}

void centerAll() {
  for (int i = 0; i < N_DRIVEN; i++) pwm.setPWM(i, 0, angleToTick(0.0f));
  pwm.setPWM(DIVE_CH, 0, angleToTick(0.0f));     // dive planes level
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LEAK, INPUT);
  ledcSetup(LED_CH, LED_PWM_FREQ, LED_PWM_BITS);   // headlight PWM (core 2.0.x)
  ledcAttachPin(PIN_LED, LED_CH);
  ledcWrite(LED_CH, 0);                  // headlight off at boot
  Wire.begin(21, 22);
  pwm.begin();
  pwm.setPWMFreq(PCA_FREQ_HZ);

  const float k = 2.0f * PI / BODY_LENGTH_M;          // one wave over body
  for (int i = 0; i < N_DRIVEN; i++) {
    PHI[i] = k * (JOINT_Z_MM[i] / 1000.0f);
    // envelope spans all 5 body joints; we drive the front 3 of it
    AMP[i] = CRUISE_AMP_DEG * (0.45f + 0.55f * (i + 1) / (float)N_BODY_JOINTS);
  }
  mpuInit();                              // identity-check + wake + calibrate
  Serial.println(g_imuOk ? "MPU6050 OK" : "MPU6050 FAIL -- heading-hold disabled");
  g_prevHeadCtrlMs = millis();
  // depth sensor: init + report status. Depth-hold is refused unless this is OK
  // (the controller must never act on a fake/zero depth -- that was the old bug)
  depthSensor.setModel(MS5837::MS5837_30BA);
  depthSensor.setFluidDensity(FLUID_DENSITY);    // MUST match params.WATER
  g_depthOk = depthSensor.init();
  Serial.println(g_depthOk ? "MS5837 OK" : "MS5837 FAIL -- depth-hold disabled");
  centerAll();
  g_t0 = millis();
  g_prevDepthMs = millis();
  Serial.println("eel ready: S<spd> H<bias> Y<hdg> M<manual> D<depth> L<level> "
                 "W<light> X<estop>");
}

void readSerial() {
  static char buf[24];
  static uint8_t n = 0;
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      buf[n] = 0;
      if (n > 0) {
        char cmd = buf[0];
        float val = atof(buf + 1);
        if      (cmd == 'S') { g_speed = constrain(val, 0.0f, 1.0f); g_estop = false; }
        else if (cmd == 'H') { g_heading = constrain(val, -30.0f, 30.0f); g_headingHold = false; }
        else if (cmd == 'Y') {                          // hold heading (IMU only)
          if (g_imuOk) { g_targetHeading = val; g_headingHold = true; }
          else Serial.println("heading-hold unavailable -- MPU6050 not detected");
        }
        else if (cmd == 'M') { g_headingHold = false; }                        // manual steering
        else if (cmd == 'D') {                          // depth-hold (sensor only)
          if (g_depthOk) { g_targetDepth = constrain(val, 0.0f, 2.0f); g_depthHold = true; }
          else Serial.println("depth-hold unavailable -- MS5837 not detected");
        }
        else if (cmd == 'L') { g_depthHold = false; }   // level planes, hold off
        else if (cmd == 'W') {                          // headlight brightness
          float b = constrain(val, 0.0f, 1.0f);
          ledcWrite(LED_CH, (int)(b * 255.0f + 0.5f));
        }
        else if (cmd == 'X') { g_estop = true; }
      }
      n = 0;
    } else if (n < sizeof(buf) - 1) {
      buf[n++] = c;
    }
  }
}

void loop() {
  readSerial();
  updateHeading();                        // integrate IMU yaw every cycle

  // safety: leak -> halt. Debounce (need several consecutive HIGH reads) and
  // LATCH (stay halted until reset) so a noisy probe can't flicker the gait.
  // HW note: AC/pulse-bias the probe rather than DC, and put it at the dry
  // bay's LOWEST point (see docs) -- DC on a wet probe corrodes + false-trips.
  static uint8_t leakCount = 0;
  static bool leakLatched = false;
  if (digitalRead(PIN_LEAK) == HIGH) { if (leakCount < 5) leakCount++; }
  else if (leakCount > 0) leakCount--;
  if (leakCount >= 5 && !leakLatched) {
    leakLatched = true;
    Serial.println("!! LEAK -- halting (latched; reset to clear)");
  }
  if (leakLatched) g_estop = true;

  if (g_estop || g_speed <= 0.0f) {
    centerAll();
    delay(20);
    return;
  }

  // closed-loop heading: IMU yaw error -> steering bias (overrides manual)
  float steer = g_headingHold ? headingBias() : g_heading;

  float t = (millis() - g_t0) / 1000.0f;
  float f = BASE_FREQ_HZ * g_speed;
  for (int i = 0; i < N_DRIVEN; i++) {                   // front 3 driven servos
    float ang = AMP[i] * sinf(2.0f * PI * f * t - PHI[i]) + steer;
    pwm.setPWM(i, 0, angleToTick(ang));
  }
  // bow dive planes: depth-hold PID if engaged, else level
  float dive = g_depthHold ? diveAngleFromDepth() : 0.0f;
  pwm.setPWM(DIVE_CH, 0, angleToTick(dive));
  delay(15);                                            // ~66 Hz update
}

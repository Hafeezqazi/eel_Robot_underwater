# Wiring & Pinout — Eel Robot

Pin-level companion to the block diagram in [wiring.drawio](wiring.drawio). Every
pin here matches a constant in [firmware/eel_gait.ino](../firmware/eel_gait.ino) —
if you change a pin, change it in both places.

Controller: **ESP32 dev board**. Servos are driven by a **PCA9685** over I²C (the
ESP32 does not PWM the servos directly). All I²C devices share one bus.

## ESP32 pin map
| ESP32 pin | Net | Goes to | Dir | Notes |
|---|---|---|---|---|
| GPIO21 | `SDA` | PCA9685, MPU6050, MS5837 | I/O | shared I²C data; 4.7 kΩ pull-up to 3V3 |
| GPIO22 | `SCL` | PCA9685, MPU6050, MS5837 | I/O | shared I²C clock; 4.7 kΩ pull-up to 3V3 |
| GPIO34 | `PIN_LEAK` | leak probe | **in** | input-only pin → needs an **external 100 kΩ pull-down** (HIGH = water) |
| GPIO25 | `PIN_LED` | LED MOSFET gate | out | PWM-dimmed headlight; gate a logic-level MOSFET, **never drive the LED off the pin** |
| TX0/RX0 | `UART0` | USB-serial → topside | I/O | console @ **115200**; the tether's data pair |
| VIN (5V) | `5V_MCU` | buck B output | pwr | ESP32's own 5 V feed → onboard 3V3 LDO |
| 3V3 | `3V3` | I²C devices' logic | pwr | logic rail for PCA9685 VCC, IMU, depth sensor |
| GND | `GND` | common | pwr | **single common ground** (servo + logic grounds tied) |

## PCA9685 servo channels
| Channel | Servo | Constant | Travel |
|---|---|---|---|
| CH0 | Joint 1 (seg1) | `JOINT_Z_MM[0]=140` | ±28° mech, ±7° cruise |
| CH1 | Joint 2 (seg2) | `JOINT_Z_MM[1]=200` | ±28° |
| CH2 | Joint 3 (seg3) | `JOINT_Z_MM[2]=260` | ±28° |
| CH5 | Dive planes | `DIVE_CH=5` | ±25° (`DIVE_MAX_DEG`) |
| CH3, CH4 | — | spare | — |

PCA9685: `VCC`=3V3 (logic), `V+`=**servo bus 5–6 V**, frame `PCA_FREQ_HZ=50`,
addr `0x40`. Servo pulse `SERVO_MIN_US..MAX_US = 1000..2000 µs`, centre 1500 µs.

## I²C device addresses
| Device | Addr | Role |
|---|---|---|
| PCA9685 | `0x40` | 16-ch servo PWM |
| MPU6050 | `0x68` (`MPU_ADDR`) | IMU — gyro-Z for heading hold |
| MS5837 | `0x76` | depth / pressure for depth hold |

## Power rails
Tether carries **12 V** (not 5–6 V — see [power.py](../analysis/power.py): thin
wire drops >1 V at peak). Both bucks live **at the robot**, in the dry bay.

| Rail | Source | Feeds | Protection |
|---|---|---|---|
| 12 V tether | topside PSU | buck A, buck B | inline fuse topside |
| 5.5 V servo bus | buck A (12→5.5 V, ≥5 A) | PCA9685 `V+`, all 4 servos, LED | **~4 A fuse** + **1000–2200 µF** bulk cap across the bus |
| 5 V MCU | buck B (12→5 V, ~1 A) | ESP32 `VIN` | **separate** from servo bus (stall spikes must not reset the MCU) |
| 3V3 | ESP32 onboard LDO | I²C logic | — |
| LED | servo bus via MOSFET | headlight | **own small fuse**, gated by GPIO25 |

> The two-buck split is the brownout fix from `power.py`: servos and MCU never
> share a rail, so a 4 A stall spike can't brown out the ESP32.

## Tether conductors (Cat5e or equivalent, 3–5 m)
| Pair | Carries | Gauge note |
|---|---|---|
| 1 + 2 (doubled) | +12 V / GND | use AWG18–20; double up pairs for the power feed |
| 3 | USB-serial (TX/RX) | data |
| 4 | composite video (analog cam) | data |

## Sealing / penetration
All wires enter the **dry head bay** through **one potted gland** in the lid
(marine epoxy). The MS5837 face is **epoxied into the lid sensor port**, gel side
to water. Camera + LED sit **behind the nose window**, inside the dry bay. The 4
servos live in the **flooded** body — buy waterproof servos (or pot them); their
leads run back to the bay gland. See [build_guide.md](build_guide.md) §4, §9.

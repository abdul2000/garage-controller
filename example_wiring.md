# Garage Controller Wiring Guide

## Components Needed

1. Raspberry Pi Zero W (with WiFi)
2. 5V Relay Module (1-channel)
3. Magnetic Door Sensor (Reed Switch)
4. 10kΩ Pull-up Resistor
5. Jumper Wires
6. Breadboard or PCB

## Wiring Connections

### Relay Module (for Door Opener Control)
- VCC → 5V (Pin 2)
- GND → Ground (Pin 6)
- IN → GPIO 18 (Pin 12)

### Door Sensor (Reed Switch)
- One terminal → GPIO 24 (Pin 18)
- Other terminal → Ground (Pin 20)
- 10kΩ resistor between GPIO 24 and 3.3V (Pin 1)

## Raspberry Pi Zero Pinout Reference

```
    3.3V  (1) (2)  5V
   GPIO2  (3) (4)  5V
   GPIO3  (5) (6)  GND
   GPIO4  (7) (8)  GPIO14
     GND  (9) (10) GPIO15
  GPIO17 (11) (12) GPIO18  ← Relay Control
  GPIO27 (13) (14) GND
  GPIO22 (15) (16) GPIO23
    3.3V (17) (18) GPIO24  ← Door Sensor
  GPIO10 (19) (20) GND     ← Sensor Ground
   GPIO9 (21) (22) GPIO25
  GPIO11 (23) (24) GPIO8
     GND (25) (26) GPIO7
   GPIO0 (27) (28) GPIO1
   GPIO5 (29) (30) GND
   GPIO6 (31) (32) GPIO12
  GPIO13 (33) (34) GND
  GPIO19 (35) (36) GPIO16
  GPIO26 (37) (38) GPIO20
     GND (39) (40) GPIO21
```

## Garage Door Opener Connection

Connect the relay's NO (Normally Open) and COM (Common) terminals to your garage door opener's control terminals. This is typically the same connection points where you would connect a wired garage door remote.

**WARNING**: Always disconnect power to your garage door opener before making connections!

## Safety Notes

1. Ensure all connections are secure
2. Test the sensor by manually opening/closing the door
3. Verify the relay activates the door opener
4. Consider adding a manual override switch
5. Use appropriate fuses for protection
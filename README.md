# Shadow Bionic Hand

A gesture-controlled bionic hand using an Arduino, 7 servos, and a webcam. Move your hand in front of the camera and the bionic hand mirrors your movements in real time using MediaPipe hand tracking.

---

## Hardware

- Arduino Uno
- 7 servos (5 finger + 2 wrist)
- Breadboard + jumper wires
- USB webcam
- 5V power supply

### Servo Pin Mapping

| Servo   | Arduino Pin |
|---------|-------------|
| Wrist 1 | 3           |
| Wrist 2 | 4           |
| Thumb   | 11          |
| Index   | 10          |
| Middle  | 6           |
| Ring    | 5           |
| Pinky   | 8           |

---

## Software Requirements

- Python 3.10+
- Arduino IDE

### Python Libraries

```
pip install mediapipe opencv-python pyserial
```

---

## Setup

### 1. Upload Arduino Sketch
- Open `arduino/servo_tester/servo_tester.ino` in Arduino IDE
- Select your board: **Tools → Board → Arduino Uno**
- Select your port: **Tools → Port → COM3** (or your port)
- Click **Upload**

### 2. Run Gesture Control
```
cd python
python gesture_control.py
```
Or specify your COM port manually:
```
python gesture_control.py COM3
```

### 3. Run Servo Tester (optional)
Use this to test individual servos with sliders and preset grips:
```
python servo_tester.py
```

---

## Controls

### Gesture Control
| Key | Action |
|-----|--------|
| `Q` | Quit |
| `P` | Pause / Resume mirroring |
| `C` | Centre all servos |

### Servo Tester
| Control | Action |
|---------|--------|
| Sliders | Move individual servos |
| Sweep | Full range test per servo |
| Fist | Close all fingers |
| Open | Open all fingers |
| Peace | Index + Middle up |
| Point | Index only up |
| Thumbs Up | Thumb up, rest closed |
| Centre All | All servos to 90° |

---

## Notes

- The `hand_landmarker.task` model file (~25MB) is downloaded automatically on first run
- Do not run `gesture_control.py` and `servo_tester.py` at the same time — they share the same COM port
- Close Arduino IDE Serial Monitor before running any Python script

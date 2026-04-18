"""
gesture_control.py
──────────────────
Controls the Shadow Bionic Hand by mirroring your hand gestures.
Compatible with mediapipe 0.10.30+

Requirements:
    pip install mediapipe opencv-python pyserial

Usage:
    python gesture_control.py            # auto-detects port
    python gesture_control.py COM3       # or specify port

Controls:
    Q  →  quit
    P  →  pause/resume mirroring
    C  →  centre all servos
"""

import sys
import time
import os
import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
import serial
import serial.tools.list_ports

# ── Config ────────────────────────────────────────────────────────────
BAUD          = 9600
CAMERA_INDEX  = 0
SEND_INTERVAL = 0.15  # send every 150ms — slow enough to not overflow serial

SERVO_NAMES  = ["Wrist 1", "Wrist 2", "Thumb", "Index", "Middle", "Ring", "Pinky"]
FINGER_TIPS  = [4, 8, 12, 16, 20]
FINGER_BASES = [2, 5,  9, 13, 17]

MODEL_PATH = "hand_landmarker.task"
MODEL_URL  = ("https://storage.googleapis.com/mediapipe-models/"
              "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task")

HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (0,9),(9,10),(10,11),(11,12),
    (0,13),(13,14),(14,15),(15,16),
    (0,17),(17,18),(18,19),(19,20),
    (5,9),(9,13),(13,17)
]


# ── Model download ────────────────────────────────────────────────────

def ensure_model():
    if not os.path.exists(MODEL_PATH):
        print("Downloading hand tracking model (~25MB), please wait...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Model ready!")


# ── Serial helpers ────────────────────────────────────────────────────

def find_arduino_port():
    for p in serial.tools.list_ports.comports():
        if any(kw in p.description.lower()
               for kw in ("arduino", "usb", "acm", "ch340", "cp210")):
            return p.device
    ports = serial.tools.list_ports.comports()
    return ports[0].device if ports else None


def open_serial(port):
    ser = serial.Serial(port, BAUD, timeout=1, write_timeout=1)
    time.sleep(2)
    ser.reset_input_buffer()
    return ser


def send_angles(ser, angles):
    """Send each servo angle one at a time — no threading."""
    try:
        for i, angle in enumerate(angles):
            cmd = f"MOVE {i} {angle}\n"
            ser.write(cmd.encode())
            ser.flush()
            time.sleep(0.02)
    except serial.SerialException as e:
        print(f"Serial error: {e}")


# ── Landmark math ─────────────────────────────────────────────────────

def get_finger_curl(lm, tip_id, base_id, wrist_id=0):
    tip   = lm[tip_id]
    base  = lm[base_id]
    wrist = lm[wrist_id]
    dist_tip  = ((tip.x - wrist.x)**2 + (tip.y - wrist.y)**2) ** 0.5
    dist_base = ((base.x - wrist.x)**2 + (base.y - wrist.y)**2) ** 0.5
    ratio = dist_tip / (dist_base + 1e-6)
    curl  = 1.0 - min(max((ratio - 0.5) / 1.0, 0.0), 1.0)
    return curl


def curl_to_angle(curl):
    return int(curl * 180)


def get_wrist_angles(lm):
    wrist      = lm[0]
    middle_mcp = lm[9]
    index_mcp  = lm[5]
    pinky_mcp  = lm[17]
    pitch  = middle_mcp.y - wrist.y
    wrist1 = max(0, min(180, int(90 + pitch * 300)))
    roll   = index_mcp.x - pinky_mcp.x
    wrist2 = max(0, min(180, int(90 + roll * 150)))
    return wrist1, wrist2


# ── Drawing ───────────────────────────────────────────────────────────

def draw_hand(frame, lm, w, h):
    pts = [(int(p.x * w), int(p.y * h)) for p in lm]
    for a, b in HAND_CONNECTIONS:
        cv2.line(frame, pts[a], pts[b], (0, 200, 255), 2)
    for pt in pts:
        cv2.circle(frame, pt, 4, (0, 255, 128), -1)


# ── Main ──────────────────────────────────────────────────────────────

def main():
    ensure_model()

    port = sys.argv[1] if len(sys.argv) > 1 else find_arduino_port()
    if not port:
        print("Could not find Arduino. Run: python gesture_control.py COM3")
        sys.exit(1)

    print(f"Connecting to Arduino on {port}...")
    try:
        ser = open_serial(port)
        print("Arduino connected!")
    except serial.SerialException as e:
        print(f"Serial error: {e}")
        sys.exit(1)

    base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options      = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=1,
        min_hand_detection_confidence=0.7,
        min_hand_presence_confidence=0.7,
        min_tracking_confidence=0.6
    )
    landmarker = vision.HandLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("Could not open camera. Try changing CAMERA_INDEX in the script.")
        sys.exit(1)

    print("Camera opened!")
    print("─────────────────────────")
    print("  Q → Quit")
    print("  P → Pause / Resume")
    print("  C → Centre all servos")
    print("─────────────────────────")

    paused          = False
    last_send       = time.time()
    current_angles  = [90] * 7
    last_thumb_angle= 90

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame    = cv2.flip(frame, 1)
        h, w, _  = frame.shape
        rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result   = landmarker.detect(mp_image)

        if result.hand_landmarks and not paused:
            lm = result.hand_landmarks[0]
            draw_hand(frame, lm, w, h)

            curls  = [get_finger_curl(lm, tip, base)
                      for tip, base in zip(FINGER_TIPS, FINGER_BASES)]
            w1, w2 = get_wrist_angles(lm)

            thumb_angle = min(180, int(curl_to_angle(curls[0]) * 1.8))
            if thumb_angle > 5:
                last_thumb_angle = thumb_angle

            current_angles = [
                w1, w2,
                last_thumb_angle,
                curl_to_angle(curls[1]),
                curl_to_angle(curls[2]),
                curl_to_angle(curls[3]),
                curl_to_angle(curls[4]),
            ]

            # Send to Arduino on main thread at controlled rate
            now = time.time()
            if now - last_send >= SEND_INTERVAL:
                send_angles(ser, current_angles)
                last_send = time.time()

            # HUD
            colors = [(0,200,255),(0,200,255),(0,255,128),
                      (0,255,128),(0,255,128),(0,255,128),(0,255,128)]
            for i, (name, angle, color) in enumerate(
                    zip(SERVO_NAMES, current_angles, colors)):
                bar_w = int(angle / 180 * 150)
                y     = 30 + i * 30
                cv2.putText(frame, f"{name:<10} {angle:>3}",
                            (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1)
                cv2.rectangle(frame, (175, y-14), (175+bar_w, y-2), color, -1)
                cv2.rectangle(frame, (175, y-14), (325, y-2), (80,80,80), 1)
        else:
            cv2.putText(frame, "No hand detected — show your hand to the camera",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,100,255), 1)

        status = "PAUSED  press P to resume" if paused else "LIVE  mirroring your hand"
        col    = (0, 80, 255) if paused else (0, 255, 80)
        cv2.putText(frame, status, (10, h-15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2)

        cv2.imshow("Shadow Bionic Hand — Gesture Control", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('p'):
            paused = not paused
            print("Paused" if paused else "Resumed")
        elif key == ord('c'):
            current_angles   = [90] * 7
            last_thumb_angle = 90
            send_angles(ser, current_angles)
            print("Centred all servos")

    cap.release()
    cv2.destroyAllWindows()
    ser.close()
    print("Goodbye!")


if __name__ == "__main__":
    main()

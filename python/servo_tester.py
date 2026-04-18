"""
servo_tester.py
───────────────
Interactive GUI to test all servos connected to an Arduino.

Requirements:
    pip install pyserial

Usage:
    python servo_tester.py            # auto-detects port
    python servo_tester.py COM3       # or specify port
    python servo_tester.py /dev/ttyUSB0
"""

import sys
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("pyserial not found. Install with:  pip install pyserial")
    sys.exit(1)

BAUD = 9600
TIMEOUT = 2          # seconds to wait for Arduino response


# ── Serial helpers ────────────────────────────────────────────────────

def find_arduino_port():
    """Return the first USB/ACM serial port found, or None."""
    for p in serial.tools.list_ports.comports():
        if any(kw in p.description.lower() for kw in ("arduino", "usb", "acm", "ch340", "cp210")):
            return p.device
    ports = serial.tools.list_ports.comports()
    return ports[0].device if ports else None


def open_serial(port):
    ser = serial.Serial(port, BAUD, timeout=TIMEOUT)
    time.sleep(2)                       # wait for Arduino reset
    ser.reset_input_buffer()
    return ser


def send_command(ser, cmd: str) -> str:
    ser.write((cmd + "\n").encode())
    line = ser.readline().decode(errors="replace").strip()
    return line


# ── GUI ───────────────────────────────────────────────────────────────

class ServoTesterApp(tk.Tk):
    def __init__(self, port: str):
        super().__init__()
        self.title("Arduino Servo Tester")
        self.resizable(False, False)
        self.configure(bg="#1a1a2e")

        self.ser = None
        self.port = port
        self.num_servos = 0
        self.angles: list[int] = []
        self.sliders: list[tk.Scale] = []
        self.angle_labels: list[tk.Label] = []
        self.sweep_buttons: list[tk.Button] = []

        self._build_header()
        self._connect()

    # ── Layout helpers ────────────────────────────────────────────────

    def _build_header(self):
        hdr = tk.Frame(self, bg="#16213e", pady=10)
        hdr.pack(fill="x")

        tk.Label(hdr, text="⚙  Arduino Servo Tester", font=("Courier", 16, "bold"),
                 fg="#e94560", bg="#16213e").pack(side="left", padx=16)

        self.status_var = tk.StringVar(value="Connecting…")
        tk.Label(hdr, textvariable=self.status_var, font=("Courier", 11),
                 fg="#a8dadc", bg="#16213e").pack(side="right", padx=16)

    def _build_servo_panel(self):
        """Called after we know num_servos."""
        container = tk.Frame(self, bg="#1a1a2e", padx=16, pady=12)
        container.pack(fill="both", expand=True)

        for i in range(self.num_servos):
            self.angles.append(90)
            row = tk.Frame(container, bg="#0f3460", bd=1, relief="flat",
                           padx=12, pady=8)
            row.pack(fill="x", pady=4)

            # Servo label
            tk.Label(row, text=f"Servo {i}", width=9, anchor="w",
                     font=("Courier", 11, "bold"), fg="#e94560", bg="#0f3460").pack(side="left")

            # Angle label
            lbl = tk.Label(row, text="90°", width=5,
                           font=("Courier", 11), fg="#a8dadc", bg="#0f3460")
            lbl.pack(side="left")
            self.angle_labels.append(lbl)

            # Slider
            sl = tk.Scale(row, from_=0, to=180, orient="horizontal", length=320,
                          bg="#0f3460", fg="#ffffff", troughcolor="#16213e",
                          highlightthickness=0, showvalue=False,
                          command=lambda val, idx=i: self._on_slide(idx, val))
            sl.set(90)
            sl.pack(side="left", padx=8)
            self.sliders.append(sl)

            # Sweep button
            sw_btn = tk.Button(row, text="Sweep", width=7,
                               font=("Courier", 10), bg="#e94560", fg="white",
                               activebackground="#c73652", relief="flat", cursor="hand2",
                               command=lambda idx=i: self._sweep(idx))
            sw_btn.pack(side="left", padx=4)
            self.sweep_buttons.append(sw_btn)

        # ── Bottom controls ──
        ctrl = tk.Frame(self, bg="#1a1a2e", pady=8)
        ctrl.pack(fill="x")

        tk.Button(ctrl, text="Centre All", font=("Courier", 11, "bold"),
                  bg="#533483", fg="white", activebackground="#3e2768",
                  relief="flat", padx=16, pady=6, cursor="hand2",
                  command=self._centre_all).pack(side="left", padx=16)

        tk.Button(ctrl, text="Sweep All", font=("Courier", 11, "bold"),
                  bg="#533483", fg="white", activebackground="#3e2768",
                  relief="flat", padx=16, pady=6, cursor="hand2",
                  command=self._sweep_all).pack(side="left")

        self.log_var = tk.StringVar(value="")
        tk.Label(ctrl, textvariable=self.log_var, font=("Courier", 10),
                 fg="#a8dadc", bg="#1a1a2e").pack(side="right", padx=16)

    # ── Actions ───────────────────────────────────────────────────────

    def _connect(self):
        try:
            if not self.port:
                self.port = find_arduino_port()
            if not self.port:
                messagebox.showerror("No Port", "Could not find an Arduino.\n"
                                     "Pass the port as a command-line argument:\n"
                                     "  python servo_tester.py COM3")
                self.destroy()
                return

            self.ser = open_serial(self.port)
            resp = send_command(self.ser, "STATUS")           # → "SERVOS N"

            if resp.startswith("SERVOS"):
                self.num_servos = int(resp.split()[1])
            else:
                self.num_servos = 6                           # fallback default

            self.status_var.set(f"✓ Connected  {self.port}  ({self.num_servos} servos)")
            self._build_servo_panel()

        except serial.SerialException as e:
            messagebox.showerror("Serial Error", str(e))
            self.destroy()

    def _on_slide(self, idx: int, val: str):
        angle = int(float(val))
        self.angles[idx] = angle
        self.angle_labels[idx].config(text=f"{angle}°")
        if self.ser:
            try:
                send_command(self.ser, f"MOVE {idx} {angle}")
                self.log_var.set(f"Servo {idx} → {angle}°")
            except serial.SerialException as e:
                self.log_var.set(f"Error: {e}")

    def _sweep(self, idx: int):
        def task():
            self.sweep_buttons[idx].config(state="disabled")
            self.log_var.set(f"Sweeping servo {idx}…")
            try:
                resp = send_command(self.ser, f"SWEEP {idx}")
                self.log_var.set(resp)
                # reset slider to 90 after sweep
                self.sliders[idx].set(90)
                self.angle_labels[idx].config(text="90°")
            except serial.SerialException as e:
                self.log_var.set(f"Error: {e}")
            finally:
                self.sweep_buttons[idx].config(state="normal")
        threading.Thread(target=task, daemon=True).start()

    def _centre_all(self):
        if self.ser:
            send_command(self.ser, "CENTRE")
            for i in range(self.num_servos):
                self.sliders[i].set(90)
                self.angle_labels[i].config(text="90°")
            self.log_var.set("All servos centred")

    def _sweep_all(self):
        for i in range(self.num_servos):
            self._sweep(i)
            time.sleep(0.1)


# ── Entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    port_arg = sys.argv[1] if len(sys.argv) > 1 else None
    app = ServoTesterApp(port_arg)
    app.mainloop()

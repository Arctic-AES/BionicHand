#include <Servo.h>

// ── Servo pin mapping ─────────────────────────────────────────────────
const int SERVO_PINS[]    = {3, 4, 11, 10, 6, 5, 8};
const char* SERVO_NAMES[] = {"Wrist 1", "Wrist 2", "Thumb", "Index", "Middle", "Ring", "Pinky"};
const int NUM_SERVOS      = sizeof(SERVO_PINS) / sizeof(SERVO_PINS[0]);

Servo servos[NUM_SERVOS];

void setup() {
  Serial.begin(9600);
  for (int i = 0; i < NUM_SERVOS; i++) {
    servos[i].attach(SERVO_PINS[i]);
    servos[i].write(90);
  }
  Serial.println("READY");
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd.startsWith("MOVE ") && !cmd.startsWith("MOVEALL")) {
      int spaceA = cmd.indexOf(' ', 5);
      int idx    = cmd.substring(5, spaceA).toInt();
      int angle  = cmd.substring(spaceA + 1).toInt();
      if (idx >= 0 && idx < NUM_SERVOS && angle >= 0 && angle <= 180) {
        servos[idx].write(angle);
        Serial.println("OK " + String(idx) + " " + String(angle));
      } else {
        Serial.println("ERR bad params");
      }

    } else if (cmd.startsWith("MOVEALL")) {
      String params = cmd.substring(8);
      params.trim();
      int idx = 0;
      while (params.length() > 0 && idx < NUM_SERVOS) {
        int space = params.indexOf(' ');
        int angle;
        if (space == -1) {
          angle = params.toInt();
          params = "";
        } else {
          angle = params.substring(0, space).toInt();
          params = params.substring(space + 1);
        }
        if (angle >= 0 && angle <= 180) servos[idx].write(angle);
delay(50);
idx++;
      }
      Serial.println("OK MOVEALL");

    } else if (cmd.startsWith("SWEEP ")) {
      int idx = cmd.substring(6).toInt();
      if (idx >= 0 && idx < NUM_SERVOS) {
        for (int a = 0; a <= 180; a += 5) { servos[idx].write(a); delay(15); }
        for (int a = 180; a >= 0; a -= 5) { servos[idx].write(a); delay(15); }
        servos[idx].write(90);
        Serial.println("SWEPT " + String(idx));
      }

    } else if (cmd == "CENTRE") {
      for (int i = 0; i < NUM_SERVOS; i++) servos[i].write(90);
      Serial.println("CENTRED");

    } else if (cmd == "FIST") {
      servos[0].write(90); servos[1].write(90);
      for (int i = 2; i < NUM_SERVOS; i++) servos[i].write(180);
      Serial.println("FIST");

    } else if (cmd == "OPEN") {
      for (int i = 0; i < NUM_SERVOS; i++) servos[i].write(0);
      Serial.println("OPEN");

    } else if (cmd == "PEACE") {
      servos[0].write(90); servos[1].write(90);
      servos[2].write(180); servos[3].write(0);
      servos[4].write(0);   servos[5].write(180);
      servos[6].write(180);
      Serial.println("PEACE");

    } else if (cmd == "POINT") {
      servos[0].write(90); servos[1].write(90);
      servos[2].write(180); servos[3].write(0);
      servos[4].write(180); servos[5].write(180);
      servos[6].write(180);
      Serial.println("POINT");

    } else if (cmd == "THUMBSUP") {
      servos[0].write(90); servos[1].write(90);
      servos[2].write(0);   servos[3].write(180);
      servos[4].write(180); servos[5].write(180);
      servos[6].write(180);
      Serial.println("THUMBSUP");

    } else if (cmd == "STATUS") {
      Serial.println("SERVOS " + String(NUM_SERVOS));
    }
  }
}
/*
  E-Waste Sorter — Arduino Servo Controller
  Receives classification commands via Serial from Python script.
  Moves a servo to direct waste into one of 4 bins.
  
  Wiring:
    - Servo signal → Pin 9
    - Servo power  → 5V (or external power for large servos)
    - Servo GND    → GND
  
  Serial commands (from Python):
    "BATTERY\n"  → moves servo to Bin 1 angle
    "PCB\n"      → moves servo to Bin 2 angle
    "PLASTIC\n"  → moves servo to Bin 3 angle
    "METAL\n"    → moves servo to Bin 4 angle
    "NOTHING\n"  → stays in neutral position (blocks ramp)
*/

#include <Servo.h>

Servo sorterServo;

// Pin configuration
const int SERVO_PIN = 9;

// Servo angles for each bin — ADJUST THESE to match your physical setup
// Neutral (90°) is center. Bins 1&2 are counter-clockwise (< 90°), Bins 3&4 are clockwise (> 90°)
const int ANGLE_NEUTRAL = 90;   // Ramp blocked / idle position (center)
const int ANGLE_BATTERY = 150;  // Bin 1 — counter-clockwise (servo goes to higher angle = CCW)
const int ANGLE_PCB     = 120;  // Bin 2 — counter-clockwise
const int ANGLE_PLASTIC = 60;   // Bin 3 — clockwise (servo goes to lower angle = CW)
const int ANGLE_METAL   = 30;   // Bin 4 — clockwise

// How long to hold the position before returning to neutral (ms)
const int HOLD_TIME = 30000;

// Current state
String inputString = "";
bool stringComplete = false;

void setup() {
  Serial.begin(9600);
  sorterServo.attach(SERVO_PIN);
  
  // Start in neutral position
  sorterServo.write(ANGLE_NEUTRAL);
  delay(500);
  
  Serial.println("READY");
}

void loop() {
  // Read serial input
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') {
      stringComplete = true;
    } else {
      inputString += c;
    }
  }
  
  // Process command
  if (stringComplete) {
    inputString.trim();
    inputString.toUpperCase();
    
    int targetAngle = -1;
    
    if (inputString == "BATTERY") {
      targetAngle = ANGLE_BATTERY;
    } else if (inputString == "PCB") {
      targetAngle = ANGLE_PCB;
    } else if (inputString == "PLASTIC") {
      targetAngle = ANGLE_PLASTIC;
    } else if (inputString == "METAL") {
      targetAngle = ANGLE_METAL;
    } else if (inputString == "NOTHING") {
      targetAngle = ANGLE_NEUTRAL;
    }
    
    if (targetAngle >= 0) {
      // Move to bin position
      sorterServo.write(targetAngle);
      Serial.print("MOVED:");
      Serial.println(inputString);
      
      // Hold position to let item slide into bin
      delay(HOLD_TIME);
      
      // Return to neutral (block ramp for next item)
      sorterServo.write(ANGLE_NEUTRAL);
      Serial.println("NEUTRAL");
    } else {
      Serial.print("UNKNOWN:");
      Serial.println(inputString);
    }
    
    // Reset
    inputString = "";
    stringComplete = false;
  }
}

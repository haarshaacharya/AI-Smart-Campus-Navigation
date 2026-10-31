
void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.begin(9600);
}

void loop() {
  if (Serial.available() > 0) {
    char command = Serial.read();

    if (command == 'L') {
      digitalWrite(LED_BUILTIN, HIGH);
    }

    if (command == 'O') {
      digitalWrite(LED_BUILTIN, LOW);
    }
  }
}

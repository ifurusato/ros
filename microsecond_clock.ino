/*
   Create a simple 50ms/20Hz clock, blinking the onboard LED every second.
*/

const int ledPin   =  13;    // the LED pin
const int clockPin =   7;    // the clock output pin to connect to Pi

// Variables will change:
int clockState = LOW;        // clockState used for the timer loop
int ledState   = LOW;        // used to toggle the LED

// use "unsigned long" for variables that hold time
unsigned long previousMicros = 0;  // stores last time clock was updated
unsigned long ticks = 0;           // used to modulo the LED

// 50ms = 50000us; 1000ms = 1000000us
const long interval = 50000;   // 20Hz clock interval (microseconds)

void setup() {
  // set the digital pins as outputs:
  pinMode(ledPin, OUTPUT);
  pinMode(clockPin, OUTPUT);
}


void loop() {

  unsigned long currentMicros = micros();

  if ( currentMicros - previousMicros >= interval ) {
    previousMicros = currentMicros;

    // toggle clock state
    if ( clockState == LOW ) {
      clockState = HIGH;
    } else {
      clockState = LOW;
    }
    digitalWrite(clockPin, clockState);

    ticks += 1;
    if ( ticks % 20 == 0 ) { // blink every 20th tick
      // toggle LED state
      if ( ledState == LOW ) {
        ledState = HIGH;
      } else {
        ledState = LOW;
      }
      digitalWrite(ledPin, ledState);
    }
  }

}

#include <Wire.h>
#include <stdio.h> // required for function sprintf

/*
    Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
    the Raspberry Pi Master to Arduino Slave (pimaster2ardslave) project and is
    released under the MIT License. Please see the LICENSE file included as part
    of this package.

      author:   Murray Altheim
      created:  2020-04-30
      modified: 2020-08-19

    KR01 robot Integrated Front Sensor (IFS) script

    This configures an Arduino-compatible board as a slave to a Raspberry Pi
    master, configured to communicate over I²C on address 0x08. The Arduino
    runs this single script, the Raspberry Pi a Python script. This is a
    radical simplification of previous versions of this script, which permitted
    remote configuration. This more reliable version hard-codes everything as:

      Pins 1-5 are analog input pins (infrared sensors)
      Pins 9-11 are digital pull-up pins (bumper switches)

    On each call, the loop() function reads the values of each of the assigned
    pins into their respective variables. These values are returned when called
    by pin number.

    The setup() function establishes the I²C communication and configures
    two callback functions, one for when the Arduino receives data, and one
    for when it receives a request for data:

      receiveData(): when called this stores the pin number as a byte in a
          variable. This determines which of the available values is set as
          the 'register" value.
      requestData(): when called this responds with the register value.

    Due to the one byte limit, returned values are limited 0-255.
*/

#define SLAVE_I2C_ADDRESS            0x08
#define LOOP_DELAY_MS                  50
#define NULL_VALUE                    255   // returned on error

// CONSTANTS .....................................

// pin types (must match Python enum) ............
const int PIN_INPUT_DIGITAL           = 0;  // default
const int PIN_INPUT_DIGITAL_PULLUP    = 1;  // inverted: low(0) is on
const int PIN_INPUT_ANALOG            = 2;
const int PIN_OUTPUT                  = 3;
const int PIN_UNUSED                  = 4;

const int PORT_SIDE_INFRARED_PIN      =  1;
const int PORT_INFRARED_PIN           =  2;
const int CENTER_INFRARED_PIN         =  3;
const int STBD_INFRARED_PIN           =  4;
const int STBD_SIDE_INFRARED_PIN      =  5;
const int PORT_BUMPER_PIN             =  9;
const int CENTER_BUMPER_PIN           =  10;
const int STBD_BUMPER_PIN             =  11;

// these values should match those in the KR01 configuration
const int PORT_SIDE_TRIGGER_DISTANCE     = 70;
const int PORT_TRIGGER_DISTANCE          = 80;
const int CENTER_TRIGGER_DISTANCE        = 60;
const int STBD_TRIGGER_DISTANCE          = 80;
const int STBD_SIDE_TRIGGER_DISTANCE     = 70;

const int PORT_SIDE_TRIGGER_DISTANCE_FAR = 60;
const int PORT_TRIGGER_DISTANCE_FAR      = 55;
const int CENTER_TRIGGER_DISTANCE_FAR    = 55;
const int STBD_TRIGGER_DISTANCE_FAR      = 55;
const int STBD_SIDE_TRIGGER_DISTANCE_FAR = 60;

long loopCount          = 0;           // number of times loop() has been called
byte stored_byte        = NULL_VALUE;  // placeholder for value
int trigger_blink_time  = 5;            // how long to blink following a trigger

int port_side_ir_value  = 0;
int port_ir_value       = 0;
int center_ir_value     = 0;
int stbd_ir_value       = 0;
int stbd_side_ir_value  = 0;
int port_bumper_value   = 0;
int center_bumper_value = 0;
int stbd_bumper_value   = 0;

boolean isVerbose = false;             // write verbose messages to serial console if true
char buf[100];                         // used by sprintf

// DotStar support ..............................

#include <Adafruit_DotStar.h>

#define NUMPIXELS      1  // there is only one pixel on the board
#define PIXEL          0  // the identifier for that pixel
#define DATAPIN        8  // use these two pin definitions for the ItsyBitsy M4
#define CLOCKPIN       6

Adafruit_DotStar strip(NUMPIXELS, DATAPIN, CLOCKPIN, DOTSTAR_BGR);

uint32_t RED          = strip.Color(255,   0,   0);
uint32_t DARK_RED     = strip.Color( 64,   0,   0);
uint32_t BLOOD_ORANGE = strip.Color( 96,  28,   0);
uint32_t DARK_ORANGE  = strip.Color(195,  82,   0);
uint32_t ORANGE       = strip.Color(228, 128,   0);
uint32_t YELLOW       = strip.Color(255, 255,   0);
uint32_t YELLOW_GREEN = strip.Color( 64, 228,   0);
uint32_t GREEN        = strip.Color(  0, 255,   0);
uint32_t DARK_GREEN   = strip.Color(  0,  64,   0);
uint32_t CYAN         = strip.Color(  0, 255, 255);
uint32_t DARK_CYAN    = strip.Color(  0,  64,  64);
uint32_t BLUE         = strip.Color(  0,   0, 255);
uint32_t DARK_BLUE    = strip.Color(  0,   0,  64);
uint32_t SKY_BLUE     = strip.Color( 30, 102, 186);
uint32_t PURPLE       = strip.Color(180,   0, 255);
uint32_t DARK_PURPLE  = strip.Color( 69,  20, 128);
uint32_t MAGENTA      = strip.Color(255,   0, 255);
uint32_t DARK_MAGENTA = strip.Color( 64,   0,  64);
uint32_t WHITE        = strip.Color(255, 255, 255);
uint32_t LIGHT_GREY   = strip.Color(160, 160, 160);
uint32_t GREY         = strip.Color(128, 128, 128);
uint32_t DARK_GREY    = strip.Color( 64,  64,  64);
uint32_t BLACK        = strip.Color(  0,   0,   0);

// functions ...................................................................

/**
    Required setup function.
*/
void setup() {
  // initialize digital pin LED_BUILTIN as an output.
  pinMode(LED_BUILTIN, OUTPUT);

  // dotstar setup .................
  strip.begin(); // initialize pins for output
  strip.setBrightness(100);
  strip.show();  // turn all LEDs off ASAP
  strip.setPixelColor(PIXEL, RED);
  strip.show();

  // default pin configuration .....
  pinMode(PORT_SIDE_INFRARED_PIN, INPUT);
  pinMode(PORT_INFRARED_PIN, INPUT);
  pinMode(CENTER_INFRARED_PIN, INPUT);
  pinMode(STBD_INFRARED_PIN, INPUT);
  pinMode(STBD_SIDE_INFRARED_PIN, INPUT);
  pinMode(PORT_BUMPER_PIN, INPUT_PULLUP);
  pinMode(CENTER_BUMPER_PIN, INPUT_PULLUP);
  pinMode(STBD_BUMPER_PIN, INPUT_PULLUP);

  Wire.begin(SLAVE_I2C_ADDRESS);
  Wire.onReceive(receiveData);
  Wire.onRequest(requestData);
  ready_blink();
}

/**
    Required loop function.
*/
void loop() {
  long start_ms = millis();
  // ................................
  readSensorValues();
  loopCount += 1;
  if ( loopCount % 600 == 0 ) {
    digitalWrite(LED_BUILTIN, HIGH);
    delay(2);
    digitalWrite(LED_BUILTIN, LOW);
  }
  // ................................
  long end_ms = millis();
  long elapsed_ms = end_ms - start_ms;
  // delay only what remains of intended loop
  long remaining_ms = LOOP_DELAY_MS - elapsed_ms;
  if ( remaining_ms > 0 ) {
    delay(remaining_ms);
  }
}

/**
    Sends the contents of the stored byte over the Wire.
*/
void requestData() {
  Wire.write(stored_byte);
}

/**
    Receives notification that data is available over the Wire,
    reading each byte into a stored value (we keep only the last
    value read).
*/
void receiveData(int byteCount) {
  byte read_byte = NULL_VALUE;
  while ( Wire.available() ) {
    read_byte = Wire.read();
  }
  switch ( read_byte ) {
    case PORT_SIDE_INFRARED_PIN:
      stored_byte = port_side_ir_value;
      break;
    case PORT_INFRARED_PIN:
      stored_byte = port_ir_value;
      break;
    case CENTER_INFRARED_PIN:
      stored_byte = center_ir_value;
      break;
    case STBD_INFRARED_PIN:
      stored_byte = stbd_ir_value;
      break;
    case STBD_SIDE_INFRARED_PIN:
      stored_byte = stbd_side_ir_value;
      break;
    case PORT_BUMPER_PIN:
      stored_byte = port_bumper_value;
      break;
    case CENTER_BUMPER_PIN:
      stored_byte = center_bumper_value;
      break;
    case STBD_BUMPER_PIN:
      stored_byte = stbd_bumper_value;
      break;
    default:
      stored_byte = NULL_VALUE;
      break;
  }
}

void readSensorValues() {
  port_side_ir_value  = constrainAnalogValue(analogRead(PORT_SIDE_INFRARED_PIN));
  if ( port_side_ir_value > PORT_SIDE_TRIGGER_DISTANCE ) {
    blink_color(RED, trigger_blink_time);
  } else if ( port_side_ir_value > PORT_SIDE_TRIGGER_DISTANCE_FAR ) {
    blink_color(DARK_RED, trigger_blink_time);
  }
  port_ir_value = constrainAnalogValue(analogRead(PORT_INFRARED_PIN));
  if ( port_ir_value > PORT_TRIGGER_DISTANCE ) {
    blink_color(MAGENTA, trigger_blink_time);
  } else if ( port_ir_value > PORT_TRIGGER_DISTANCE_FAR ) {
    blink_color(DARK_MAGENTA, trigger_blink_time);
  }
  center_ir_value = constrainAnalogValue(analogRead(CENTER_INFRARED_PIN));
  if ( center_ir_value > CENTER_TRIGGER_DISTANCE ) {
    blink_color(BLUE, trigger_blink_time);
  } else if ( center_ir_value > CENTER_TRIGGER_DISTANCE_FAR ) {
    blink_color(DARK_BLUE, trigger_blink_time);
  }
  stbd_ir_value = constrainAnalogValue(analogRead(STBD_INFRARED_PIN));
  if ( stbd_ir_value > STBD_TRIGGER_DISTANCE ) {
    blink_color(CYAN, trigger_blink_time);
  } else if ( stbd_ir_value > STBD_TRIGGER_DISTANCE_FAR ) {
    blink_color(DARK_CYAN, trigger_blink_time);
  }
  stbd_side_ir_value = constrainAnalogValue(analogRead(STBD_SIDE_INFRARED_PIN));
  if ( stbd_side_ir_value > STBD_SIDE_TRIGGER_DISTANCE ) {
    blink_color(GREEN, trigger_blink_time);
  } else if ( stbd_side_ir_value > STBD_SIDE_TRIGGER_DISTANCE_FAR ) {
    blink_color(DARK_GREEN, trigger_blink_time);
  }
  port_bumper_value = !digitalRead(PORT_BUMPER_PIN);
  if ( port_bumper_value == 1 ) {
    blink_color(RED, trigger_blink_time);
  }
  center_bumper_value = !digitalRead(CENTER_BUMPER_PIN);
  if ( center_bumper_value == 1 ) {
    blink_color(BLUE, trigger_blink_time);
  }
  stbd_bumper_value = !digitalRead(STBD_BUMPER_PIN);
  if ( stbd_bumper_value == 1 ) {
    blink_color(GREEN, trigger_blink_time);
  }
  if ( isVerbose ) {
    sprintf(buf, "[%05ld]: %2d << %2d < %2d > %2d >> %2d", loopCount, port_side_ir_value, port_ir_value, center_ir_value, stbd_ir_value, stbd_side_ir_value );
    Serial.println(buf);
  }
}

/**
    Constrains the analog value between 0 and 254 (255 is considered an error value).
*/
int constrainAnalogValue( int value ) {
  return 254.0 * value / 1023.0;
}

// status displays .............................................................

/**
    A distinctive cyan swell and blink pattern indicating we're ready to go.
*/
void ready_blink() {
  delay(1500);
  for ( int i = 0; i < 255; i++ ) {
    uint32_t color = strip.Color(i, 0, 0);
    strip.setPixelColor(PIXEL, color);
    strip.show();
    delay(5);
  }
  strip.setPixelColor(PIXEL, BLACK);
  strip.show();
  delay(250);
  blink_color(RED, 250);
  blink_color(RED, 250);
  strip.setPixelColor(PIXEL, RED);
  strip.show();
  delay(250);
  for ( int i = 255; i > 0; i-- ) {
    uint32_t color = strip.Color(i, 0, 0);
    strip.setPixelColor(PIXEL, color);
    strip.show();
    delay(3);
  }
  blink_color(ORANGE, 200);
  blink_color(DARK_ORANGE, 300);
  blink_color(BLOOD_ORANGE, 400);
  blink_color(RED, 999);
  strip.setPixelColor(PIXEL, BLACK);
  strip.show();
}

/**
    Blink the color to indicate a reset.
*/
void reset_blink() {
  int count = 4;
  for ( int i = 0; i < count; i++ ) {
    blink_color(MAGENTA, 125);
  }
}

/**
    Blink the color for the specified number of milliseconds.
*/
void blink_color( uint32_t color, int ms ) {
  strip.setPixelColor(PIXEL, color);
  strip.show();
  delay(ms);
  strip.setPixelColor(PIXEL, BLACK);
  strip.show();
  delay(ms);
}

// EOF

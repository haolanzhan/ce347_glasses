#include <ArduinoBLE.h>
#include <camera.h>

#ifdef ARDUINO_NICLA_VISION
  #include "gc2145.h"
  GC2145 galaxyCore;
  Camera cam(galaxyCore);
  #define IMAGE_MODE CAMERA_RGB565
#elif defined(ARDUINO_PORTENTA_H7_M7)
  #include "hm0360.h"
  HM0360 himax;
  Camera cam(himax);
  #define IMAGE_MODE CAMERA_GRAYSCALE
#elif defined(ARDUINO_GIGA)
  #include "ov767x.h"
  // uncomment the correct camera in use
  OV7670 ov767x;
  // OV7675 ov767x;
  Camera cam(ov767x);
  #define IMAGE_MODE CAMERA_RGB565
#else
#error "This board is unsupported."
#endif

// Define the service and characteristic UUIDs
#define SERVICE_UUID "0000180a-0000-1000-8000-00805f9b34fb"
#define CHARACTERISTIC_UUID "00002a50-0000-1000-8000-00805f9b34fb"

BLEService imageService(SERVICE_UUID);
//characteristic with read/notify properties, and 512 bytes maximum size
BLECharacteristic imageDataCharacteristic(CHARACTERISTIC_UUID, BLERead | BLENotify, 0, 512);

const int buttonPin = 2; // Replace with the input pin you are using
int buttonState = 0;  // variable for reading the pushbutton status
int write_state = 0; // state of BLE characteristic write 

//framebuffer for camera 
FrameBuffer fb;
unsigned long lastUpdate = 0;


//Essentially blink forever if error
void blinkLED(uint32_t count = 0xFFFFFFFF)
{
  pinMode(LED_BUILTIN, OUTPUT);
  while (count--) {
    digitalWrite(LED_BUILTIN, LOW);  // turn the LED on (HIGH is the voltage level)
    delay(50);                       // wait for a second
    digitalWrite(LED_BUILTIN, HIGH); // turn the LED off by making the voltage LOW
    delay(50);                       // wait for a second
  }
}

void setup() {
  Serial.begin(9600);
  while (!Serial);

  Serial.println("Begin initialization ... ");

  // Start BLE
  if (!BLE.begin()) {
    Serial.println("Starting Bluetooth® Low Energy module failed!");
    blinkLED(); //blink forever
    while (1); //just in case
  }

  // Set up the image service
  BLE.setLocalName("NiclaVision");
  BLE.setDeviceName("NiclaVision");
  BLE.setAdvertisedService(imageService);

  // Add the image data characteristic to the service
  imageService.addCharacteristic(imageDataCharacteristic);

  // add service
  BLE.addService(imageService);

  //sanity checks
  Serial.print("Max characteristic value size = ");
  Serial.println(imageDataCharacteristic.valueSize());
  Serial.print("Current characteristic length = ");
  Serial.println(imageDataCharacteristic.valueLength());

  // Advertise the image service
  Serial.println("Start advertising ... ");
  BLE.advertise();

  // Set up the button pin
  pinMode(buttonPin, INPUT_PULLUP);

    // Init the cam QVGA, 30FPS
  if (!cam.begin(CAMERA_R320x240, IMAGE_MODE, 30)) {
    Serial.println("Camera failed to initialize!");
    blinkLED(); //blink forever
    while(1); //just in case
  }

  Serial.println("BLE, camera, and button initialized ... ");
  blinkLED(5); //visible signal to end of init - might require this delay for camera to fully initialized (assumed from the example code)
}

void loop() {

  BLEDevice central = BLE.central();

  // Wait for a connection
  while (!BLE.connected()) {
    Serial.println("Still awaiting connection ... ");
    delay(500);
  }

  if (central) {
      // print the central's MAC address:
      Serial.print("Image service connected to central device: ");
      Serial.println(central.address());

      while (central.connected()){

        while (!imageDataCharacteristic.subscribed())
        {
          Serial.println("Waiting for BLE central device to subscribe ... ");
        }
        Serial.println("BLE central has subscribed to the image characteristic");

        // Check for button press
        buttonState = digitalRead(buttonPin);

        if (buttonState == LOW) {
          // Take a picture and store it in the framebuffer
          cam.grabFrame(fb, 3000);

          //error check
          if (fb.isAllocated())
          {
            Serial.print("Framebuffer allocated with size: ");
            Serial.println(fb.getBufferSize());
          } else
          {
            Serial.println("Framebuffer is not allocated");
            blinkLED(); //blink forever
            while(1); //just in case
          }

          uint8_t *imageData = fb.getBuffer();
          uint32_t imageDataSize = fb.getBufferSize();

          // Stream the image data via BLE
          size_t offset = 0;
          while (offset < imageDataSize) {
            size_t chunkSize = min(imageDataSize - offset, 512);
            write_state = imageDataCharacteristic.writeValue(imageData + offset, chunkSize);
            
            if (write_state == 1)
            {
              Serial.print("Successful write of chunk at offset");
              Serial.println(offset);
            } else
            {
              Serial.print("Failed to write chunk at offset");
              Serial.println(offset);
            }

            offset += chunkSize;
          }
        }

        // Poll for BLE events
        BLE.poll(); //might not need
      }

      // when the central disconnects, print it out:
      Serial.print(F("Disconnected from central: "));
      Serial.println(central.address());
  }
}

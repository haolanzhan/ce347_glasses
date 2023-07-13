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

// Define the service, characteristic, and descriptor UUIDs
#define SERVICE_UUID "0000180a-0000-1000-8000-00805f9b34fb"
#define CHARACTERISTIC_UUID "00002a50-0000-1000-8000-00805f9b34fb" //image data
#define CHARACTERISTIC_RESPONSE_UUID "a6e4c57a-ab93-4547-aced-156fe2597e8d" //response 

#define PACKAGE_SIZE 128 //512

// Create the BLE service, characteristics, and descriptors using the above UUIDs
BLEService imageService(SERVICE_UUID);
//characteristic with read/notify properties, and PACKAGE_SIZE bytes maximum size
BLECharacteristic imageDataCharacteristic(CHARACTERISTIC_UUID, BLERead | BLENotify, PACKAGE_SIZE);
//characteristic with read/write properties, and size of 1 byte
BLEByteCharacteristic imageResponseCharacteristic(CHARACTERISTIC_RESPONSE_UUID, BLERead | BLEWrite);

const int buttonPin = 0; // Replace with the input pin you are using
int buttonState = 0;  // variable for reading the pushbutton status
int write_state = 0; // state of BLE characteristic write 

//framebuffer for camera 
FrameBuffer fb(320,240,2); //320 by 240 pixels, 2 bytes per pixel 
unsigned long lastUpdate = 0;

//Essentially blink forever if error, or blink the input number of times. 
void blinkLED(uint32_t count = 0xFFFFFFFF)
{
  pinMode(LED_BUILTIN, OUTPUT);
  while (count--) {
    digitalWrite(LED_BUILTIN, LOW);  // turn the LED on (HIGH is the voltage level)
    delay(100);                       // wait for a second
    digitalWrite(LED_BUILTIN, HIGH); // turn the LED off by making the voltage LOW
    delay(100);                       // wait for a second
  }
}

void setup() {
  //Serial.begin(9600);
  //while (!Serial);

  //Serial.println("Begin initialization ... ");

  // Start BLE
  if (!BLE.begin()) {
    //Serial.println("Starting Bluetooth® Low Energy module failed!");
    blinkLED(); //blink forever
    while (1); //just in case
  }

  // Set up the image service
  BLE.setLocalName("NiclaVision");
  //BLE.setDeviceName("NiclaVision");
  BLE.setAdvertisedService(imageService);

  // Add the image data and response characteristic to the service
  imageService.addCharacteristic(imageDataCharacteristic);
  imageService.addCharacteristic(imageResponseCharacteristic);

  // add service
  BLE.addService(imageService);

  // set the initial value for the characeristic:
  imageResponseCharacteristic.writeValue(0);

  //sanity checks
  //Serial.print("Max characteristic value size (bytes): ");
  //Serial.println(imageDataCharacteristic.valueSize());
  //Serial.print("Current characteristic length (bytes): ");
  //Serial.println(imageDataCharacteristic.valueLength());

  // Advertise the image service
  //Serial.println("Start advertising ... ");
  BLE.advertise();

  // Set up the button pin
  pinMode(buttonPin, INPUT_PULLUP);

  // Init the cam QVGA, 30FPS
  if (!cam.begin(CAMERA_R320x240, IMAGE_MODE, 30)) {
    //Serial.println("Camera failed to initialize!");
    blinkLED(); //blink forever
    while(1); //just in case
  }

  // check the frame buffer 
  if (fb.isAllocated())
  {
    //Serial.print("Framebuffer allocated with size (bytes): ");
    //Serial.println(fb.getBufferSize());
  } else
  {
    //Serial.println("Framebuffer is not allocated");
    blinkLED(); //blink forever
    while(1); //just in case
  }

  //Serial.println("BLE, camera, framebuffer, and button initialized - entering main loop ... ");
  blinkLED(5); //visible signal to end of init - might require this delay for camera to fully initialized (assumed from the example code)
}

void loop() {

  BLEDevice central = BLE.central();

  if (central) { //we are connected
      // print the central's MAC address:
      //Serial.print("Image service connected to central device: ");
      //Serial.println(central.address());

      // just so that serial monitor is not being spammed while waiting for a button press
      int counter = 0;

      while (central.connected()){

        if (imageDataCharacteristic.subscribed())
        {
           if (counter == 0)
           {
             //Serial.println("BLE central has subscribed to the image characteristic, waiting for button press ... ");  
           }

          // Check for button press
          buttonState = digitalRead(buttonPin);
          //Serial.println(buttonState);

          if (/*counter == 0*/buttonState == LOW) {
            // Take a picture and store it in the framebuffer
            //Serial.println("Taking a picture ... ");
            blinkLED(1);

            if (cam.grabFrame(fb, 3000) != 0)
            {
              //Serial.print("Error taking picture ...");
              blinkLED(); //blink forever
              while(1); //just in case
            }

            uint8_t *imageData = fb.getBuffer();
            uint32_t imageDataSize = fb.getBufferSize();
            //Serial.print("Image data size is: ");
            //Serial.println(imageDataSize);

            //uncomment to view raw bytes data of the image in the serial monitor
            // Serial.write(imageData, imageDataSize); 

            // Stream the image data via BLE
            size_t offset = 0;
            while (offset < imageDataSize) {
              size_t chunkSize = min(imageDataSize - offset, PACKAGE_SIZE);
              //Serial.print("Chunk size (bytes): ");
              //Serial.println(chunkSize);
              write_state = imageDataCharacteristic.writeValue(imageData + offset, chunkSize);

              //debugging purpose: printing out raw data for each chunk
              //Serial.println(" "); //linebreak
              //Serial.write(imageData + offset, chunkSize); 
              //Serial.println(" "); //linebreak

              if (write_state == 1)
              {
                //Serial.print("Successful write of chunk at offset: ");
                //Serial.println(offset);
                //Serial.print("Current characteristic length (bytes): ");
                //Serial.println(imageDataCharacteristic.valueLength());
              } else
              {
                //Serial.print("Failed to write chunk at offset");
                //Serial.println(offset);
              }

              offset += chunkSize;
            }

            //Serial.println("Image sent ...");
            counter = 0;

          } else 
          {
            //Serial.println("Waiting for button press ... ");
            //blinkLED(5); //we have already taken one photo
            counter++;
          }

        } else
        {
          //Serial.println("Still awaiting subscripton ... ");
          blinkLED(5); //we are still awaiting for subscription
        }

        // Poll for BLE events
        BLE.poll(); //might not need
      }

      // when the central disconnects, print it out:
      //Serial.println("Disconnected from central: ");
      //Serial.println(central.address());
      blinkLED(3);
  } else
  {
    //Serial.println("Still awaiting connection ... ");
    blinkLED(3); //we are still awaiting for conection
    delay(1000);
  }
}

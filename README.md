# ce347_glasses
Project for CE347-II


Haolan - BLE central device python script set up to read values from a BLE device - working on expanding this to image transfer

George - Working on image detection and image summarization  

Will -  Look into frame design, longer camera ribbon cable, future PCB design, and high-level software organization. 

---------------------------------------------------------------------------------------------------------------------  

Setup instruction:  
1) Download Arduino IDE 2 from https://www.arduino.cc/en/software. 
2) Follow this tutorial (https://docs.arduino.cc/software/ide-v1/tutorials/getting-started/cores/arduino-mbed_nicla) to download the Mbed OS Nicla core, which requries Arduino IDE 2.  
3) Update the bootloader: go to "File > Examples > STM32H747_System > STM32H747_manageBootloader" and upload this sketch to your board. After the sketch is uploaded, follow the instructions in the Serial Monitor.  
4) Download OpenMV from https://openmv.io/pages/download.  
5) Follow the tutorial on this page to set up OpenMV: https://docs.arduino.cc/tutorials/nicla-vision/getting-started

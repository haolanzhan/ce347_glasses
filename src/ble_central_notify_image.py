import asyncio
from bleak import BleakScanner, BleakClient, BleakError
import io
from PIL import Image

# ------------------------------------------------ global variables and definitions ------------------------------------------------
# Define the resolution of the image (QVGA)
IMG_WIDTH = 320
IMG_HEIGHT = 240

# Define the max number of bytes in a packet
MAX_PACKET_SIZE = 128 #512

# number of bytes expected to receive per image (received in RGB565 format)
IMG_BYTES = IMG_WIDTH * IMG_HEIGHT * 2

# number of bytes for RGB888 version of received image
RGB888_IMG_BYTES = IMG_WIDTH * IMG_HEIGHT * 3

# Define the number of packets in an image (division rounds down to the nearest int)
NUM_PACKETS = IMG_BYTES // MAX_PACKET_SIZE

# offset into the framebuffers
OFFSET = 0 
OFFSET_RGB888 = 0

# number of packets received
PACKETS_RECEIVED = 0

# number of images received
NUM_IMAGES = 0

# list of asynch low priority tasks
TASK_DICT = {}

#framebuffer for storing image
framebuffer = bytearray(IMG_BYTES) # RGB565 format
new_framebuffer = bytearray(RGB888_IMG_BYTES) # RGB888 format

# Masks needed to convert RGB565 to RGB888
MASK0 = 0xf8
MASK1_HIGH = 0x07
MASK1_LOW = 0xe0
MASK2 = 0x1f

# Define the UUID of the service and characteristic we are interested in (from arduino sript)
SERVICE_UUID = "0000180a-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UUID = "00002a50-0000-1000-8000-00805f9b34fb"

# ------------------------------------------------ Main BLE functions ------------------------------------------------
async def scan():
    while True:
        devices = await BleakScanner.discover()

        # scan all connectable BLE devices and connect to Nicla Vision if found 
        for d in devices:
            print(f"Device found: {d.name}, address: {d.address}")
            if d.name != None:
                if "Arduino" in d.name:
                    print("Nicla Vision Found ... ")
                    await connect_and_read(d.address) # main loop of the program. Asynch function can be used with await so that we can execute other things while waiting for a result if needed
        
        print("Device not found\n");

async def connect_and_read(device_address):
    global framebuffer, new_framebuffer, OFFSET, OFFSET_RGB888, IMG_BYTES, IMG_WIDTH, IMG_HEIGHT, PACKETS_RECEIVED, NUM_IMAGES, TASK_DICT

    try:
        async with BleakClient(device_address) as client:
            await client.connect()
            print(f"\nConnected (or reconnected to) to: {device_address}")

            # Target and connect to the specified service and characteristic - add in later
            # service = await client.get_service(SERVICE_UUID)
            # characteristic = await service.get_characteristic(CHARACTERISTIC_UUID)

            #loop thru all services and subscribe to all services with the notify feature 
            services = client.services
            for service in services:
                print(f"\n-------------------------------------------------------------------------")
                print(f"This service: {service}")
                characteristics = service.characteristics
                for characteristic in characteristics:
                    print(f"\nThis characterestic: {characteristic} with properties: {characteristic.properties}")

                    if "notify" in characteristic.properties:
                        print(f"Subscribing to characteristic {characteristic.uuid} ...")
                        await client.start_notify(characteristic.handle, notification_handler)

                    if "write" in characteristic.properties:
                        value = await client.read_gatt_char(characteristic.handle)
                        print(f"Above Characteristic available to read with value: {value}")
            
            # Loop to keep receiving images without disconnecting - main loop of the program
            while client.is_connected: 

                # Wait for all packets of the image to be received
                while OFFSET < IMG_BYTES:
                    # print(f"Image still not complete. At Offset: {OFFSET}\n")
                    await asyncio.sleep(0.1)

                print("Received image ...")

                # wait for all threads to be complete (Pixel format conversion)
                await asyncio.wait(TASK_DICT.values(), return_when=asyncio.ALL_COMPLETED)
                print("All threads completed ... \n")

                # convert framebuffer pixel format to RGB888 for Pillow - legacy 
                # rgb565_to_rbg888(framebuffer)

                # Convert the framebuffer to bytes
                framebuffer_bytes = bytes(new_framebuffer)
                print(f"Framebuffer type: {type(framebuffer_bytes)}")
                print(f"Framebuffer lenth: {len(framebuffer_bytes)}")
                
                #convert the framebuffer into an image
                print("Processing image ... ")
                image = Image.frombytes("RGB", (IMG_WIDTH, IMG_HEIGHT), framebuffer_bytes, "raw")

                # Save the image to a file
                print("Saving image ... ")
                img_number_str = str(NUM_IMAGES)
                image.save(f"received_image_{img_number_str}.jpg")

                # show the image
                # image.show()

                #reset variables
                print("Resetting variables ... ")
                OFFSET = 0
                OFFSET_RGB888 = 0
                PACKETS_RECEIVED = 0
                TASK_DICT.clear()
                NUM_IMAGES = NUM_IMAGES + 1

            # unused but here just in case
            print("Disconnecting client ... ")
            await client.disconnect()

    except BleakError as e:
        print(e)

# called upon each received BLE packet - the notify feature allows the automatic receival of new data once it is posted by the peripheral device
def notification_handler(sender, data):
    global framebuffer, OFFSET, PACKETS_RECEIVED, NUM_PACKETS, IMG_BYTES, TASK_DICT

    # ------ for debugging -------
    #print(f"Characteristic {sender}\nHolds value of size: {len(data)}")
    #print(f"Data Changed to: {data.hex()}")
    #print(f"Type of data: {type(data)}")

    # keep track of the window of data 
    framebuffer_start = OFFSET 
    framebuffer_end = OFFSET + len(data)
    OFFSET = framebuffer_end
    PACKETS_RECEIVED = PACKETS_RECEIVED + 1 
    #print(f"Packets received: {PACKETS_RECEIVED}\n")

    # start a background thread to populate the initial framebuffer (RGB 565) from the new data, and 
    # convert the pixel format of the received pacakge in a new framebuffer (RGB888)
    task = asyncio.create_task(convert_pixel_format(framebuffer_start, framebuffer_end, data))
    TASK_DICT[framebuffer_start] = task
    # print(f"Started Task with ID: {framebuffer_start} ... \n")

    if (PACKETS_RECEIVED == NUM_PACKETS) and (OFFSET == IMG_BYTES):
        print("Received complete image ... \n")

# ------------------------------------------------ helper functions ------------------------------------------------
# need to convert every 2 bytes of RRRR RGGG GGGB BBBB into 3 bytes of RRRR RRRR GGGG GGGG BBBB BBBB
# this function converts the original bytes between the given bounds of the initial framebuffer (RGB565), and populates the new framebuffer (RGB888)
async def convert_pixel_format(framebuffer_start, framebuffer_end, data):
    global framebuffer, new_framebuffer, OFFSET_RGB888
    
    #buffer the initial data first. TODO: possible to get rid of the initial framebuffer in entirety and populate the new_framebuffer directly from incoming data
    framebuffer[framebuffer_start:framebuffer_end] = data 

    buff_index = framebuffer_start

    while (buff_index < framebuffer_end):

        # isolate the red green and blue bits from the incoming RGB565 pixel data
        red = (framebuffer[buff_index] & MASK0) >> 3
        green = ((framebuffer[buff_index] & MASK1_HIGH) << 3) | ((framebuffer[buff_index+1] & MASK1_LOW) >> 5)
        blue = (framebuffer[buff_index + 1] & MASK2)

        # map the pixel data from 5 or 6 bit spaces to an 8 bit space
        new_framebuffer[OFFSET_RGB888 + 0] = (red << 3) | (red >> 2)
        new_framebuffer[OFFSET_RGB888 + 1] = (green << 2) | (green >> 4)
        new_framebuffer[OFFSET_RGB888 + 2] = (blue << 3) | (blue >> 2)

        buff_index = buff_index + 2
        OFFSET_RGB888 = OFFSET_RGB888 + 3
        
    #print(f"Finished Task with ID: {framebuffer_start} ...")

# ------------------------------------------------ Main Asynchio Functions ------------------------------------------------
async def run():
    await scan()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())


# ------------------------------------------------ legacy/unused ------------------------------------------------
async def test_backgroun_thread(framebuffer_start, framebuffer_end):
    sum = 0
    for i in range(100000):
        sum = sum + 1
    print(f"Finished Task with ID: {framebuffer_start} ... \n")

# need to convert every 2 bytes of RRRR RGGG GGGB BBBB into 3 bytes of RRRR RRRR GGGG GGGG BBBB BBBB
# legacy function
def rgb565_to_rbg888(framebuffer):
    global RGB888_IMG_BYTES, IMG_BYTES, new_framebuffer
    
    buff_index = 0
    new_buff_index = 0

    while ((buff_index < IMG_BYTES) and (new_buff_index < RGB888_IMG_BYTES)):

        # isolate the red green and blue bits from the incoming RGB565 pixel data
        red = (framebuffer[buff_index] & MASK0) >> 3
        green = ((framebuffer[buff_index] & MASK1_HIGH) << 3) | ((framebuffer[buff_index+1] & MASK1_LOW) >> 5)
        blue = (framebuffer[buff_index + 1] & MASK2)

        # map the pixel data from 5 or 6 bit spaces to an 8 bit space
        new_framebuffer[new_buff_index + 0] = (red << 3) | (red >> 2)
        new_framebuffer[new_buff_index + 1] = (green << 2) | (green >> 4)
        new_framebuffer[new_buff_index + 2] = (blue << 3) | (blue >> 2)

        # #print out a couple pixels to see
        # if (buff_index <= 4):
        #     bin_pixel_data0 = bin(framebuffer[buff_index])
        #     bin_pixel_data1 = bin(framebuffer[buff_index + 1])

        #     new_bin_pixel_data0 = bin(new_framebuffer[new_buff_index])
        #     new_bin_pixel_data1 = bin(new_framebuffer[new_buff_index + 1])
        #     new_bin_pixel_data2 = bin(new_framebuffer[new_buff_index + 2])

        #     print(f"Received byte at {buff_index}: {bin_pixel_data0}")
        #     print(f"Received byte at {buff_index + 1}: {bin_pixel_data1}")

        #     print(f"New byte at {new_buff_index}: {new_bin_pixel_data0}")
        #     print(f"New byte at {new_buff_index + 1}: {new_bin_pixel_data1}")
        #     print(f"New byte at {new_buff_index + 2}: {new_bin_pixel_data2}")

        buff_index = buff_index + 2
        new_buff_index = new_buff_index + 3

# ------------------------------------------------ notes ------------------------------------------------
    #need to see if arduino write is blocking. if not have to figure out when the last byte is sent, and set a flag characteristic
    #or maybe arduino write is instantanious for BLE peripheral, and the delay happens when Central is reading
    #in above case, follow this software architecture:
        # Peripheral: 
            # 1) write 512 (or 256) bytes into the image transfer characteristic. 
            # 2) Read data_read flag 
            # 3) If flag is 1, overrite the characteristic with the next package and reset the flag. Otherwise re-loop
        # Central:
            # 1) Automatically read new packet on notify 
            # 2) Write the data_read characteristic once all bytes have been processed. Assuming the data read here is blocking? this way avoid another notify intterupt handler from happening 


# Use a control characterisitc - when Central finish writing a chunk, we 
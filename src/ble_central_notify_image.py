import asyncio
from bleak import BleakScanner, BleakClient, BleakError
import io
from PIL import Image

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

# offset into the framebuffer 
OFFSET = 0 

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

async def scan():
    while True:
        devices = await BleakScanner.discover()

        # scan all connectable BLE devices and connect to Nicla Vision if found 
        for d in devices:
            print(f"Device found: {d.name}, address: {d.address}")
            if d.name != None:
                if "Arduino" in d.name:
                    print("Nicla Vision Found ... ")
                    await connect_and_read(d.address)
        
        print("Device not found\n");

async def connect_and_read(device_address):
    global framebuffer, new_framebuffer, OFFSET, IMG_BYTES, IMG_WIDTH, IMG_HEIGHT, PACKETS_RECEIVED, NUM_IMAGES, TASK_DICT

    try:
        async with BleakClient(device_address) as client:
            await client.connect()
            print(f"\nConnected (or reconnected to) to: {device_address}")

            # Target and connect to the specified service and characteristic - add in later
            # service = await client.get_service(SERVICE_UUID)
            # characteristic = await service.get_characteristic(CHARACTERISTIC_UUID)

            #loop thru all services
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
            
            # Loop to keep receiving images without disconnecting
            while client.is_connected: 

                # Wait for all packets of the image to be received
                while OFFSET < IMG_BYTES:
                    print(f"Image still not complete. At Offset: {OFFSET}\n")
                    await asyncio.sleep(0.1)

                print("Received image ...")

                # wait for all threads to be complete 
                # await asyncio.wait(TASK_DICT.values(), return_when=asyncio.ALL_COMPLETED)
                # print("All Threads Completed ... \n")

                # convert framebuffer pixel format to RGB888 for Pillow
                rgb565_to_rbg888(framebuffer)

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
                PACKETS_RECEIVED = 0
                TASK_DICT.clear()
                NUM_IMAGES = NUM_IMAGES + 1

            print("Disconnecting client ... ")
            await client.disconnect()

    except BleakError as e:
        print(e)

def notification_handler(sender, data):
    global framebuffer, OFFSET, PACKETS_RECEIVED, NUM_PACKETS, IMG_BYTES, TASK_DICT

    #print(f"Characteristic {sender}\nHolds value of size: {len(data)}")
    #print(f"Data Changed to: {data.hex()}")
    #print(f"Type of data: {type(data)}")

    framebuffer_start = OFFSET 
    framebuffer_end = OFFSET + len(data)
    framebuffer[framebuffer_start:framebuffer_end] = data 
    OFFSET = framebuffer_end
    PACKETS_RECEIVED = PACKETS_RECEIVED + 1 

    #print(f"Packets received: {PACKETS_RECEIVED}\n")
    
    # start a task to conver the pixel format in the background 
    # task = asyncio.create_task(convert_pixel_format(framebuffer_start))
    # TASK_DICT[framebuffer_start] = task
    # print(f"Started Task with ID: {framebuffer_start} ... \n")

    if (PACKETS_RECEIVED == NUM_PACKETS) and (OFFSET == IMG_BYTES):
        print("Received complete image ... \n")

#need to convert every 2 bytes of RRRR RGGG GGGB BBBB into 3 bytes of RRRR RRRR GGGG GGGG BBBB BBBB
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

async def test_backgroun_thread(framebuffer_start):
    sum = 0
    for i in range(100000):
        sum = sum + 1
    print(f"Finished Task with ID: {framebuffer_start} ... \n")

async def convert_pixel_format(framebuffer_start, framebuffer_end):
    print(f"Finished Task with ID: {framebuffer_start} ... \n")
        
async def run():
    await scan()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())


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
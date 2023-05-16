import asyncio
from bleak import BleakScanner, BleakClient, BleakError
import io
from PIL import Image

# Define the resolution of the image (QVGA)
IMG_WIDTH = 320
IMG_HEIGHT = 240

# Define the max number of bytes in a packet
MAX_PACKET_SIZE = 512

# number of bytes expected to receive per image
IMG_BYTES = IMG_WIDTH * IMG_HEIGHT * 2

# Define the number of packets in an image (division rounds down to the nearest int)
NUM_PACKETS = IMG_BYTES // MAX_PACKET_SIZE

# offset into the framebuffer 
OFFSET = 0 

# number of packets received
PACKETS_RECEIVED = 0

#framebuffer for storing image
framebuffer = bytearray(IMG_BYTES)

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
                    print("Nicla Vision Found")
                    await connect_and_read(d.address)
        
        print("Device not found\n");

async def connect_and_read(device_address):
    global framebuffer, OFFSET, IMG_BYTES, IMG_WIDTH, IMG_HEIGHT

    try:
        async with BleakClient(device_address) as client:
            await client.connect()
            print(f"\nConnected (or reconnected to) to {device_address}")

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
                    print(f"\nThis characterestic: {characteristic} with properties {characteristic.properties}")

                    if "notify" in characteristic.properties:
                        print(f"Subscribing to characteristic {characteristic.uuid} ...")
                        await client.start_notify(characteristic.handle, notification_handler)
            
            #awaiting for notifications for 10 minutes - should keep reconnecting, re-subscribe, and wait for notifications
            #await asyncio.sleep(600)

            # Wait for all packets of the image to be received
            while OFFSET < IMG_BYTES:
                await asyncio.sleep(0.1)
            
            #convert the framebuffer into an image
            image = Image.frombytes("RGB;16", (IMG_WIDTH, IMG_HEIGHT), framebuffer)

            # Save the image to a file
            image.save("received_image.jpg")

            # show the image
            image.show()

            print("Image received ... Disconnecting client ...")
            await client.disconnect()
            #probably should reset variables here to receive a new image 

    except BleakError as e:
        print(e)

def notification_handler(sender, data):
    global framebuffer, OFFSET, PACKETS_RECEIVED, NUM_PACKETS, IMG_BYTES

    #print(f"Characteristic {sender}\n Holds value of size: {len(data)}")
    #print(f"Data Changed to: {data.hex()}")

    framebuffer_start = OFFSET 
    framebuffer_end = OFFSET + len(data)
    framebuffer[framebuffer_start:framebuffer_end] = data 
    OFFSET = framebuffer_end
    PACKETS_RECEIVED = PACKETS_RECEIVED + 1 

    if (PACKETS_RECEIVED == NUM_PACKETS) and (OFFSET == IMG_BYTES):
        print("received complete image")

async def run():
    await scan()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
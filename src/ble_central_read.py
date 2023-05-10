import asyncio
from bleak import BleakScanner, BleakClient

async def scan():
    devices = await BleakScanner.discover()
    for d in devices:
        print("Device found: ", d)

async def connect_and_read(address):
    async with BleakClient(address) as client:
        await client.connect()
        print(f"\nConnected to device with address: {address}\n")
        services = client.services

        for service in services:
            print(f"\n-------------------------------------------------------------------------")
            print(f"This service: {service}")
            characteristics = service.characteristics
            for characteristic in characteristics:
                print(f"\nThis characterestic: {characteristic} with properties {characteristic.properties}")

                if "read" in characteristic.properties: 
                    value = await client.read_gatt_char(characteristic.handle)
                    print(f"Above Characteristic available to read with value: {value}")
            
        print("Finished listing services and characterestics. Disconnecting from device")
        await client.disconnect()

async def run():
    await scan()
    device_address = input("Enter address of device to connect to: ")
    await connect_and_read(device_address)

loop = asyncio.get_event_loop()
loop.run_until_complete(run())




################## Scanner for devices ##################
# import asyncio
# from bleak import BleakScanner

# async def main():
#     devices = await BleakScanner.discover()
#     for d in devices:
#         print(d)

# asyncio.run(main())

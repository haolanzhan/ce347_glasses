import asyncio
from bleak import BleakScanner, BleakClient

async def scan():
    while True:
        devices = await BleakScanner.discover()
        for d in devices:
            print(f"Device found: {d.name}, address: {d.address}")
            if d.name != None:
                if "haolanzhan (2)" in d.name:
                    await connect_and_read(d.address)

async def connect_and_read(device_address):
    async with BleakClient(device_address) as client:
        await client.connect()
        print(f"\nConnected (or reconnected to) to {device_address}")
        services = client.services

        for service in services:
            print(f"\n-------------------------------------------------------------------------")
            print(f"This service: {service}")
            characteristics = service.characteristics
            for characteristic in characteristics:
                print(f"\nThis characterestic: {characteristic} with properties {characteristic.properties}")

                if "notify" in characteristic.properties:
                    print(f"Subscribing to characteristic {characteristic.uuid}...")
                    await client.start_notify(characteristic.handle, notification_handler)
        await asyncio.sleep(60)
        print("Waiting too long for change ... Disconnecting client ...")
        await client.disconnect()

def notification_handler(sender, data):
    print(f"Characteristic {sender} value changed: {data.hex()}")

async def run():
    await scan()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
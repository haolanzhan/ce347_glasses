import uuid

def generate_ble_characteristic_uuid():
    # Generate a random UUID
    new_uuid = uuid.uuid4()

    # Modify specific bits to indicate a BLE Characteristic UUID
    # The 16th bit (counting from the right, starting from 0) is modified
    modified_uuid = new_uuid.int & ~(0x1 << 16) | (0x1 << 16)

    # Convert the modified UUID to a string representation
    ble_characteristic_uuid = uuid.UUID(int=modified_uuid).__str__()

    return ble_characteristic_uuid

# Generate a new BLE Characteristic UUID
new_ble_characteristic_uuid = generate_ble_characteristic_uuid()

print("New BLE Characteristic UUID:", new_ble_characteristic_uuid)
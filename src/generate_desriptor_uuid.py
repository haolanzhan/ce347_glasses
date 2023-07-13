import uuid

def generate_descriptor_uuid():
    # Generate a random UUID
    new_uuid = uuid.uuid4()

    # Convert the UUID to a string representation
    descriptor_uuid = new_uuid.__str__()

    return descriptor_uuid

# Generate a new descriptor UUID
new_descriptor_uuid = generate_descriptor_uuid()

print("New Descriptor UUID:", new_descriptor_uuid)
import os

import qrcode
from qrcode.image.pil import PilImage


# Subscription URL encoded into the QR Code.
SUBSCRIPTION_URL = (
    "https://raw.githubusercontent.com/"
    "AhmadJeddi/V2RayCFGDumper/main/sub.txt"
)


# Create output directory if it does not exist.
os.makedirs("images", exist_ok=True)


# Build QR Code from the subscription URL.
qr = qrcode.QRCode(
    version=1,
    box_size=10,
    border=4,
)

qr.add_data(SUBSCRIPTION_URL)
qr.make(fit=True)


# Generate QR image with a standard black and white style.
image: PilImage = qr.make_image(
    fill_color="black",
    back_color="white",
)


# Save QR Code for README documentation.
image.save(
    "images/subscription-qrcode.png"
)


print("QR Code generated successfully.")
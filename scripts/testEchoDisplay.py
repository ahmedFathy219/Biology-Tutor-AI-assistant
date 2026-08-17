import time

import board
import digitalio

from PIL import Image, ImageDraw, ImageFont

from adafruit_rgb_display import st7735
from adafruit_rgb_display.rgb import DummyPin


print("[TFT Test] Starting...")


# ============================================================
# SPI
# ============================================================

spi = board.SPI()


# ============================================================
# GPIO
# ============================================================

# CS -> GPIO5 / physical pin 29
cs = digitalio.DigitalInOut(
    board.D5
)

# A0 / DC -> GPIO25 / physical pin 22
dc = digitalio.DigitalInOut(
    board.D25
)

# RESET -> GPIO24 / physical pin 18
reset = digitalio.DigitalInOut(
    board.D24
)

# LED is connected directly to 3.3V,
# so we do not control the backlight through GPIO.
backlight = DummyPin()


# ============================================================
# Display
# ============================================================

display = st7735.ST7735S(
    spi,
    dc=dc,
    cs=cs,
    bl=backlight,
    rst=reset,
    rotation=0,
    baudrate=16000000,
)


print(
    f"[TFT Test] Display detected: "
    f"{display.width}x{display.height}"
)


# ============================================================
# Test 1 - Red screen
# ============================================================

image = Image.new(
    "RGB",
    (
        display.width,
        display.height,
    ),
    "red",
)

display.image(image)

print("[TFT Test] RED")
time.sleep(2)


# ============================================================
# Test 2 - Green screen
# ============================================================

image = Image.new(
    "RGB",
    (
        display.width,
        display.height,
    ),
    "green",
)

display.image(image)

print("[TFT Test] GREEN")
time.sleep(2)


# ============================================================
# Test 3 - Blue screen
# ============================================================

image = Image.new(
    "RGB",
    (
        display.width,
        display.height,
    ),
    "blue",
)

display.image(image)

print("[TFT Test] BLUE")
time.sleep(2)


# ============================================================
# Test 4 - Text
# ============================================================

image = Image.new(
    "RGB",
    (
        display.width,
        display.height,
    ),
    "black",
)

draw = ImageDraw.Draw(image)


try:

    font = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        16,
    )

    small_font = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        11,
    )

except Exception:

    font = ImageFont.load_default()
    small_font = ImageFont.load_default()


draw.text(
    (35, 25),
    "ECHO",
    font=font,
    fill="cyan",
)

draw.text(
    (15, 65),
    "TFT WORKING",
    font=small_font,
    fill="white",
)

draw.rectangle(
    (
        5,
        5,
        display.width - 6,
        display.height - 6,
    ),
    outline="yellow",
    width=2,
)


display.image(image)

print("[TFT Test] Text screen displayed.")


# Keep image visible
try:

    while True:
        time.sleep(1)

except KeyboardInterrupt:

    print("\n[TFT Test] Closing...")


finally:

    # Clear TFT
    image = Image.new(
        "RGB",
        (
            display.width,
            display.height,
        ),
        "black",
    )

    display.image(image)

    cs.deinit()
    dc.deinit()
    reset.deinit()

    print("[TFT Test] Finished.")
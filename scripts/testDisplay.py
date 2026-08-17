import time

import board
import digitalio

from PIL import Image
from PIL import ImageDraw

from adafruit_rgb_display import st7735


# --------------------------------------------------
# GPIO configuration
# --------------------------------------------------

CS_PIN = board.CE0
DC_PIN = board.D25
RESET_PIN = board.D24
BACKLIGHT_PIN = board.D18


# --------------------------------------------------
# SPI
# --------------------------------------------------

spi = board.SPI()


# --------------------------------------------------
# Control pins
# --------------------------------------------------

cs = digitalio.DigitalInOut(
    CS_PIN
)

dc = digitalio.DigitalInOut(
    DC_PIN
)

reset = digitalio.DigitalInOut(
    RESET_PIN
)

backlight = digitalio.DigitalInOut(
    BACKLIGHT_PIN
)


# --------------------------------------------------
# ST7735S display
# --------------------------------------------------

display = st7735.ST7735S(
    spi,
    cs=cs,
    dc=dc,
    rst=reset,
    bl=backlight,

    width=128,
    height=160,

    # Rotate the physical screen into landscape.
    rotation=90,

    baudrate=16000000,
)


print(
    f"[TFT Test] Display size: "
    f"{display.width}x{display.height}"
)


# --------------------------------------------------
# Create screen image
# --------------------------------------------------

image = Image.new(
    "RGB",
    (
        display.width,
        display.height,
    ),
    "black",
)

draw = ImageDraw.Draw(
    image
)


# --------------------------------------------------
# Test UI
# --------------------------------------------------

draw.rectangle(
    (
        0,
        0,
        display.width - 1,
        display.height - 1,
    ),
    outline="white",
)


draw.text(
    (10, 12),
    "ECHO",
    fill="cyan",
)


draw.text(
    (10, 45),
    "TFT Hardware",
    fill="white",
)


draw.text(
    (10, 65),
    "is working!",
    fill="white",
)


draw.text(
    (10, 100),
    "ST7735S",
    fill="yellow",
)


# --------------------------------------------------
# Send image to TFT
# --------------------------------------------------

display.image(
    image
)


print(
    "[TFT Test] Image sent successfully."
)


try:

    while True:
        time.sleep(1)

except KeyboardInterrupt:

    print(
        "\n[TFT Test] Finished."
    )
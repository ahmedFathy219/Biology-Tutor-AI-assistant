# src/alerts/buzzer.py

from __future__ import annotations

import os
from typing import Any, Optional


def _read_bool(name: str, default: bool) -> bool:
    """
    Read a Boolean value from an environment variable.
    """

    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


class BuzzerController:
    """
    Controls the attention-alert buzzer.

    When enabled=False, the class runs in simulation mode.
    This allows the project to run without Raspberry Pi GPIO
    hardware or a connected buzzer.
    """

    def __init__(
        self,
        enabled: bool = False,
        pin: int = 17,
        active_high: bool = True,
    ) -> None:
        self.enabled = enabled
        self.pin = pin
        self.active_high = active_high

        self._buzzer: Optional[Any] = None

        if not self.enabled:
            print(
                "[Buzzer] Simulation mode enabled. "
                "No GPIO hardware will be accessed."
            )
            return

        try:
            # Imported only when hardware mode is enabled.
            # Therefore Windows and hardware-free tests can
            # still run without installing gpiozero.
            from gpiozero import Buzzer

            self._buzzer = Buzzer(
                self.pin,
                active_high=self.active_high,
                initial_value=False,
            )

            print(
                f"[Buzzer] Hardware initialized on "
                f"BCM GPIO {self.pin}."
            )

        except ImportError as error:
            raise RuntimeError(
                "Buzzer hardware mode is enabled, but gpiozero "
                "is not installed. Install gpiozero and lgpio "
                "on the Raspberry Pi."
            ) from error

        except Exception as error:
            raise RuntimeError(
                f"Could not initialize the buzzer on "
                f"BCM GPIO {self.pin}: {error}"
            ) from error

    def alert(self) -> bool:
        """
        Start repeated beeping until stop() is called.
        """

        # --------------------------------------------------
        # Laptop / simulation
        # --------------------------------------------------

        if self._buzzer is None:

            print(
                "[Buzzer Simulation] "
                "Repeating distraction alert started."
            )

            return True


        # --------------------------------------------------
        # Raspberry Pi
        # --------------------------------------------------

        self._buzzer.beep(
            on_time=1.0,
            off_time=0.5,
            n=None,
            background=True,
        )

        print(
            "[Buzzer] Repeating distraction alert started."
        )

        return True

    def stop(self) -> None:
        """
        Stop the repeating buzzer alert.

        On a laptop, there is no physical buzzer,
        so this safely does nothing.
        """

        # --------------------------------------------------
        # Laptop / simulation mode
        # --------------------------------------------------

        if self._buzzer is None:

            print(
                "[Buzzer Simulation] "
                "Distraction alert stopped."
            )

            return


        # --------------------------------------------------
        # Raspberry Pi hardware mode
        # --------------------------------------------------

        self._buzzer.off()

        print(
            "[Buzzer] Distraction alert stopped."
        )
    def close(self) -> None:
        """
        Release the buzzer GPIO resource.

        Safe to call on both laptop and Raspberry Pi.
        """

        # Laptop / simulation
        if self._buzzer is None:

            print(
                "[Buzzer Simulation] "
                "Buzzer controller closed."
            )

            return


        # Raspberry Pi
        self._buzzer.off()
        self._buzzer.close()

        print(
            "[Buzzer] GPIO resource released."
        )


def getBuzzerController() -> BuzzerController:
    """
    Create a buzzer controller using .env settings.
    """

    enabled = _read_bool(
        "BUZZER_ENABLED",
        False,
    )

    active_high = _read_bool(
        "BUZZER_ACTIVE_HIGH",
        True,
    )

    pin = int(
        os.getenv(
            "BUZZER_PIN",
            "17",
        )
    )

    return BuzzerController(
        enabled=enabled,
        pin=pin,
        active_high=active_high,
    )
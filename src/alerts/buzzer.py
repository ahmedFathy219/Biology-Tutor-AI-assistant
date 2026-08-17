# src/alerts/buzzer.py

from __future__ import annotations

import os
import time
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
        cooldown_seconds: float = 10.0,
    ) -> None:
        self.enabled = enabled
        self.pin = pin
        self.active_high = active_high
        self.cooldown_seconds = cooldown_seconds

        self._buzzer: Optional[Any] = None
        self._last_alert_time: Optional[float] = None

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
        Produce three short beeps.

        Returns True if an alert was started.
        Returns False if the cooldown is still active.
        """

        current_time = time.monotonic()

        if self._last_alert_time is not None:
            elapsed = current_time - self._last_alert_time

            if elapsed < self.cooldown_seconds:
                return False

        self._last_alert_time = current_time

        if self._buzzer is None:
            print(
                "[Buzzer Simulation] "
                "BEEP! BEEP! BEEP! Student is distracted."
            )
            return True

        # background=True prevents the buzzer pattern from
        # stopping the camera-processing loop.
        self._buzzer.beep(
            on_time=0.70,
            off_time=0.30,
            n=3,
            background=True,
        )

        print("[Buzzer] Distraction alert activated.")

        return True

    def stop(self) -> None:
        """
        Stop any currently playing buzzer alert.
        """

        if self._buzzer is not None:
            self._buzzer.off()

    def close(self) -> None:
        """
        Turn off the buzzer and release its GPIO resource.
        """

        if self._buzzer is not None:
            self._buzzer.off()
            self._buzzer.close()

            print("[Buzzer] GPIO resource released.")


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

    cooldown_seconds = float(
        os.getenv(
            "BUZZER_COOLDOWN_SECONDS",
            "10.0",
        )
    )

    return BuzzerController(
        enabled=enabled,
        pin=pin,
        active_high=active_high,
        cooldown_seconds=cooldown_seconds,
    )
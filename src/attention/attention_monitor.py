# src/attention/attention_monitor.py

from __future__ import annotations

import os
import threading
import time
from typing import Callable, Optional

import cv2

from alerts import getBuzzerController

from .attention_tracker import (
    AttentionState,
    AttentionTracker,
)

from .head_pose import (
    HeadPose,
    HeadPoseEstimator,
)


def _readBool(name: str, default: bool) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


class AttentionMonitor:
    """
    Runs the camera and attention tracking continuously
    in a background thread while Echo runs.
    """

    def __init__(
        self,
        enabled: bool = True,
        camera_index: int = 0,
        show_window: bool = True,
        target_fps: float = 10.0,
        frame_width: int = 640,
        frame_height: int = 480,
    ) -> None:
        self.camera = None
        self.enabled = enabled
        self.camera_index = camera_index
        self.show_window = show_window

        self.target_fps = max(
            1.0,
            target_fps,
        )

        self.frame_width = frame_width
        self.frame_height = frame_height

        self.stop_event = threading.Event()

        self.thread: Optional[
            threading.Thread
        ] = None

        self.buzzer = getBuzzerController()

        self.state_callback: Optional[
            Callable[[AttentionState], None]
        ] = None

    # --------------------------------------------------
    # Start monitoring
    # --------------------------------------------------

    def setStateCallback(
        self,
        callback: Callable[[AttentionState], None],
    ) -> None:
        """
        Register a function that is called whenever
        the student's attention state changes.
        """
    
        self.state_callback = callback

    def start(self) -> None:

        if not self.enabled:
            print(
                "[Attention] Attention monitoring disabled."
            )
            return

        if (
            self.thread is not None
            and self.thread.is_alive()
        ):
            return

        self.stop_event.clear()

        self.thread = threading.Thread(
            target=self._run,
            name="AttentionMonitor",
            daemon=True,
        )

        self.thread.start()

        print(
            "[Attention] Attention monitor started."
        )

    # --------------------------------------------------
    # Main camera loop
    # --------------------------------------------------

    def _run(self) -> None:

        print(
            f"[Attention] Opening camera "
            f"{self.camera_index}..."
        )

        camera = cv2.VideoCapture(
            self.camera_index
        )

        if not camera.isOpened():
            print(
                "[Attention] ERROR: "
                "Could not open camera."
            )
            return

                # Try to prevent infinite blocking (if supported)
        if hasattr(cv2, "CAP_PROP_READ_TIMEOUT_MSEC"):
            try:
                camera.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 1000)
            except Exception:
                pass

        camera.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            self.frame_width,
        )

        camera.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            self.frame_height,
        )

        print(
            "[Attention] Camera opened successfully."
        )

        pose_estimator = HeadPoseEstimator()
        tracker = AttentionTracker()

        previous_state: Optional[
            AttentionState
        ] = None

        frame_delay = 1.0 / self.target_fps

        try:

            while not self.stop_event.is_set():

                start_time = time.monotonic()

                success, frame = camera.read()
                # If stop was requested while read() was blocking,
                # break out immediately once we get a frame.
                if self.stop_event.is_set():
                    break
                if not success:
                    print(
                        "[Attention] "
                        "Could not read camera frame."
                    )

                    time.sleep(0.1)
                    continue

                # -------------------------------------
                # Head pose estimation
                # -------------------------------------

                pose = pose_estimator.estimate(
                    frame
                )

                # -------------------------------------
                # Attention decision
                # -------------------------------------

                state = tracker.update(
                    pose
                )

                # -------------------------------------
                # State change
                # -------------------------------------

                if state != previous_state:
                
                    print(
                        "[Attention] State: "
                        f"{state.value}"
                    )
                
                    # ------------------------------------------------
                    # Buzzer
                    # ------------------------------------------------
                
                    # ------------------------------------------------
                    # Buzzer
                    # ------------------------------------------------

                    inattentive_states = {
                        AttentionState.DISTRACTED,
                        AttentionState.NO_FACE,
                    }

                    is_inattentive = (
                        state in inattentive_states
                    )

                    was_inattentive = (
                        previous_state in inattentive_states
                    )


                    # Student JUST became inattentive.
                    if (
                        is_inattentive
                        and not was_inattentive
                    ):

                        self.buzzer.alert()


                    # Student JUST became focused again.
                    elif (
                        not is_inattentive
                        and was_inattentive
                    ):

                        self.buzzer.stop()
                
                
                    # ------------------------------------------------
                    # Notify main.py about the new attention state
                    # ------------------------------------------------
                
                    if self.state_callback is not None:
                
                        try:
                
                            self.state_callback(
                                state
                            )
                
                        except Exception as error:
                
                            print(
                                "[Attention] State callback error: "
                                f"{error}"
                            )
                
                
                    previous_state = state

                # -------------------------------------
                # Camera display
                # -------------------------------------

                if self.show_window:

                    self._drawInfo(
                        frame,
                        pose,
                        state,
                    )

                    cv2.imshow(
                        "Echo - Attention Monitor",
                        frame,
                    )

                    # Required for OpenCV window updates.
                    cv2.waitKey(1)

                # -------------------------------------
                # Limit processing FPS
                # -------------------------------------

                elapsed = (
                    time.monotonic()
                    - start_time
                )

                sleep_time = (
                    frame_delay - elapsed
                )

                if sleep_time > 0:
                    time.sleep(
                        sleep_time
                    )

        except Exception as error:

            print(
                "[Attention] Error: "
                f"{error}"
            )

        finally:

            print(
                "[Attention] "
                "Releasing camera..."
            )

            self.buzzer.stop()

            try:
                camera.release()
            except:
                pass

            if self.camera is camera:
                self.camera = None
            
            pose_estimator.close()

            if self.show_window:
                cv2.destroyAllWindows()

    # --------------------------------------------------
    # Display information
    # --------------------------------------------------

    def _drawInfo(
        self,
        frame,
        pose: Optional[HeadPose],
        state: AttentionState,
    ) -> None:

        if pose is None:

            pose_text = (
                "No face detected"
            )

        else:

            pose_text = (
                f"Yaw: {pose.yaw:.1f}   "
                f"Pitch: {pose.pitch:.1f}   "
                f"Roll: {pose.roll:.1f}"
            )

        state_text = (
            f"State: {state.value}"
        )

        cv2.putText(
            frame,
            pose_text,
            (20, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
        )

        cv2.putText(
            frame,
            state_text,
            (20, 65),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
        )

    # --------------------------------------------------
    # Stop monitoring
    # --------------------------------------------------

    def stop(self) -> None:

        if not self.enabled:
            return

        print(
            "[Attention] "
            "Stopping attention monitor..."
        )

        self.stop_event.set()
        if self.camera is not None:
            try:
                self.camera.release()
            except Exception as error:
                print(f"[Attention] Error releasing camera from stop(): {error}")
        if (
            self.thread is not None
            and self.thread.is_alive()
        ):
            self.thread.join(
                timeout=5.0
            )

        self.buzzer.stop()

        print(
            "[Attention] "
            "Attention monitor stopped."
        )

    def close(self) -> None:
        """
        Permanently close the attention monitor
        and release buzzer hardware.

        Only call this when Echo itself is exiting.
        """

        self.stop()

        self.buzzer.close()

        print(
            "[Attention] "
            "Attention monitor closed."
        )


# ------------------------------------------------------
# Factory
# ------------------------------------------------------

def getAttentionMonitor() -> AttentionMonitor:

    enabled = _readBool(
        "ATTENTION_ENABLED",
        True,
    )

    show_window = _readBool(
        "ATTENTION_SHOW_WINDOW",
        False,
    )

    camera_index = int(
        os.getenv(
            "ATTENTION_CAMERA_INDEX",
            "0",
        )
    )

    target_fps = float(
        os.getenv(
            "ATTENTION_TARGET_FPS",
            "10",
        )
    )

    frame_width = int(
        os.getenv(
            "ATTENTION_FRAME_WIDTH",
            "640",
        )
    )

    frame_height = int(
        os.getenv(
            "ATTENTION_FRAME_HEIGHT",
            "480",
        )
    )

    return AttentionMonitor(
        enabled=enabled,
        camera_index=camera_index,
        show_window=show_window,
        target_fps=target_fps,
        frame_width=frame_width,
        frame_height=frame_height,
    )
# src/attention/attention_tracker.py

import time
from enum import Enum
from typing import Optional

from .attention_config import (
    DISTRACTION_TIME,
    MAX_PITCH_UP,
    MAX_YAW,
    MAX_ROLL,
    ROLL_TIME,  
    NO_FACE_TIME,
)

from .head_pose import HeadPose


class AttentionState(Enum):
    FOCUSED = "focused"
    DISTRACTED = "distracted"
    NO_FACE = "no_face"


class AttentionTracker:
    """
    Determine attention state using head pose over time.
    """

    def __init__(self) -> None:
        self.looking_away_since: Optional[float] = None
        self.no_face_since: Optional[float] = None
        self.head_tilt_since: Optional[float] = None

        self.current_state = AttentionState.FOCUSED

    def update(
        self,
        pose: Optional[HeadPose],
    ) -> AttentionState:
        """
        Update the student's attention state.

        This method should be called once for each processed frame.
        """

        now = time.monotonic()

        # ----------------------------------------
        # No face detected
        # ----------------------------------------

        if pose is None:
            self.looking_away_since = None
            self.head_tilt_since = None

            if self.no_face_since is None:
                self.no_face_since = now

            no_face_duration = (
                now - self.no_face_since
            )

            if no_face_duration >= NO_FACE_TIME:
                self.current_state = (
                    AttentionState.NO_FACE
                )

            return self.current_state

        # A face is visible again.
        self.no_face_since = None

        # ----------------------------------------
        # Looking away / distraction
        # ----------------------------------------

        if abs(pose.roll)> MAX_ROLL:
            if self.head_tilt_since is None:
                self.head_tilt_since = now
        
            head_tilt_duration = (
                now - self.head_tilt_since
            )
        
            if head_tilt_duration>= ROLL_TIME:
                self.current_state = (
                    AttentionState.DISTRACTED
            )
        
            return self.current_state
        
        else:
            self.head_tilt_since = None

        looking_away = (
            abs(pose.yaw) > MAX_YAW
            or pose.pitch > MAX_PITCH_UP
        )

        if looking_away:
            if self.looking_away_since is None:
                self.looking_away_since = now

            looking_away_duration = (
                now - self.looking_away_since
            )

            if (
                looking_away_duration
                >= DISTRACTION_TIME
            ):
                self.current_state = (
                    AttentionState.DISTRACTED
                )

                return self.current_state

        else:
            self.looking_away_since = None

        # Nothing abnormal persisted long enough.
        self.current_state = AttentionState.FOCUSED

        return self.current_state

        
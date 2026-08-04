# src/attention/head_pose.py

from dataclasses import dataclass
from typing import Optional
import math

import cv2
import mediapipe as mp
import numpy as np


@dataclass
class HeadPose:
    """
    Head orientation in degrees.

    yaw:
        Turning left or right.

    pitch:
        Looking up or down.

    roll:
        Tilting toward the left or right shoulder.
    """

    yaw: float
    pitch: float
    roll: float


class HeadPoseEstimator:
    """
    Detect facial landmarks and estimate head orientation.
    """

    def __init__(self) -> None:
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def estimate(
        self,
        frame: np.ndarray,
    ) -> Optional[HeadPose]:

        height, width = frame.shape[:2]

        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB,
        )

        results = self.face_mesh.process(rgb_frame)

        if not results.multi_face_landmarks:
            return None

        landmarks = results.multi_face_landmarks[0].landmark

        # MediaPipe facial landmark indexes
        nose_id = 1
        chin_id = 152
        left_eye_id = 33
        right_eye_id = 263
        left_mouth_id = 61
        right_mouth_id = 291

        landmark_ids = [
            nose_id,
            chin_id,
            left_eye_id,
            right_eye_id,
            left_mouth_id,
            right_mouth_id,
        ]

        image_points = []

        for landmark_id in landmark_ids:
            landmark = landmarks[landmark_id]

            image_points.append(
                [
                    landmark.x * width,
                    landmark.y * height,
                ]
            )

        image_points = np.array(
            image_points,
            dtype=np.float64,
        )

        # Approximate coordinates on a generic 3D face.
        model_points = np.array(
            [
                [0.0, 0.0, 0.0],          # Nose
                [0.0, -63.6, -12.5],     # Chin
                [-43.3, 32.7, -26.0],    # Left eye
                [43.3, 32.7, -26.0],     # Right eye
                [-28.9, -28.9, -24.1],   # Left mouth
                [28.9, -28.9, -24.1],    # Right mouth
            ],
            dtype=np.float64,
        )

        focal_length = float(width)

        camera_matrix = np.array(
            [
                [focal_length, 0.0, width / 2.0],
                [0.0, focal_length, height / 2.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )

        distortion_coefficients = np.zeros(
            (4, 1),
            dtype=np.float64,
        )

        success, rotation_vector, _ = cv2.solvePnP(
            model_points,
            image_points,
            camera_matrix,
            distortion_coefficients,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )

        if not success:
            return None

        rotation_matrix, _ = cv2.Rodrigues(
            rotation_vector
        )

        angles, *_ = cv2.RQDecomp3x3(
            rotation_matrix
        )

        pitch = float(angles[0])
        yaw = float(angles[1])

        # -------------------------------------------------
        # Calculate roll directly from the eye-corner line
        # -------------------------------------------------

        left_eye = landmarks[left_eye_id]
        right_eye = landmarks[right_eye_id]

        left_eye_x = left_eye.x * width
        left_eye_y = left_eye.y * height

        right_eye_x = right_eye.x * width
        right_eye_y = right_eye.y * height

        delta_x = right_eye_x - left_eye_x
        delta_y = right_eye_y - left_eye_y

        # Negative because image Y coordinates increase downward.
        roll = -math.degrees(
            math.atan2(delta_y, delta_x)
        )

        return HeadPose(
            yaw=yaw,
            pitch=pitch,
            roll=roll,
        )

    def close(self) -> None:
        self.face_mesh.close()
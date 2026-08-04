# src/attention/head_pose.py

from dataclasses import dataclass
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np


@dataclass
class HeadPose:
    """
    Orientation of the student's head.

    yaw:
        Left / right rotation.

    pitch:
        Up / down rotation.

    roll:
        Sideways head tilt.
    """

    yaw: float
    pitch: float
    roll: float


class HeadPoseEstimator:
    """
    Detect facial landmarks and calculate head orientation.
    """

    def __init__(self) -> None:
        self.mp_face_mesh = mp.solutions.face_mesh

        self.face_mesh = self.mp_face_mesh.FaceMesh(
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
        """
        Estimate head pose from one camera frame.

        Returns:
            HeadPose if a face is found.
            None if no face is detected.
        """

        height, width = frame.shape[:2]

        # OpenCV uses BGR.
        # MediaPipe expects RGB.
        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB,
        )

        results = self.face_mesh.process(rgb_frame)

        if not results.multi_face_landmarks:
            return None

        landmarks = results.multi_face_landmarks[0].landmark

        # Important facial landmarks.
        #
        # These points represent:
        # nose tip
        # chin
        # left eye corner
        # right eye corner
        # left mouth corner
        # right mouth corner

        landmark_ids = [
            1,
            152,
            33,
            263,
            61,
            291,
        ]

        image_points = []

        for landmark_id in landmark_ids:
            landmark = landmarks[landmark_id]

            x = landmark.x * width
            y = landmark.y * height

            image_points.append([x, y])

        image_points = np.array(
            image_points,
            dtype=np.float64,
        )

        # Approximate 3D coordinates of corresponding
        # points on a generic human face.
        model_points = np.array(
            [
                [0.0, 0.0, 0.0],          # nose
                [0.0, -63.6, -12.5],     # chin
                [-43.3, 32.7, -26.0],    # left eye
                [43.3, 32.7, -26.0],     # right eye
                [-28.9, -28.9, -24.1],   # left mouth
                [28.9, -28.9, -24.1],    # right mouth
            ],
            dtype=np.float64,
        )

        # Approximate camera focal length.
        focal_length = width

        camera_matrix = np.array(
            [
                [focal_length, 0, width / 2],
                [0, focal_length, height / 2],
                [0, 0, 1],
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
        roll = float(angles[2])

        return HeadPose(
            yaw=yaw,
            pitch=pitch,
            roll=roll,
        )

    def close(self) -> None:
        """
        Release MediaPipe resources.
        """

        self.face_mesh.close()
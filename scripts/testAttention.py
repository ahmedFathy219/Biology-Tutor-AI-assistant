import sys
import time
from pathlib import Path

import cv2


sys.path.append(
    str(
        Path(__file__).resolve().parents[1]
        / "src"
    )
)


from attention import (
    AttentionState,
    AttentionTracker,
    HeadPoseEstimator,
)


def main() -> None:
    print("[Attention Test] Initializing...")

    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        raise RuntimeError(
            "Could not open the camera."
        )

    pose_estimator = HeadPoseEstimator()
    tracker = AttentionTracker()

    previous_state = None

    try:
        while True:
            success, frame = camera.read()

            if not success:
                print(
                    "[Attention Test] "
                    "Could not read camera frame."
                )
                break

            pose = pose_estimator.estimate(frame)

            state = tracker.update(pose)

            if pose is not None:
                information = (
                    f"Yaw: {pose.yaw:.1f}  "
                    f"Pitch: {pose.pitch:.1f}  "
                    f"Roll: {pose.roll:.1f}"
                )

                cv2.putText(
                    frame,
                    information,
                    (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                )

            else:
                cv2.putText(
                    frame,
                    "No face detected",
                    (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                )

            state_text = (
                f"State: {state.value}"
            )

            cv2.putText(
                frame,
                state_text,
                (20, 65),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )

            if state != previous_state:
                print(
                    f"[Attention] State changed: "
                    f"{state.value}"
                )

                previous_state = state

            cv2.imshow(
                "Study Buddy - Attention Test",
                frame,
            )

            key = cv2.waitKey(1)

            if key == ord("q"):
                break

            # Approximately 10 FPS.
            time.sleep(0.1)

    finally:
        camera.release()
        pose_estimator.close()

        cv2.destroyAllWindows()

        print("[Attention Test] Stopped.")


if __name__ == "__main__":
    main()
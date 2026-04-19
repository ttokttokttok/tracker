import sys
import time

import cv2

from orchestrator import Pipeline


def main():
    # Accept label as CLI arg or prompt the user
    if len(sys.argv) > 1:
        label = " ".join(sys.argv[1:])
    else:
        label = input("What object do you want to track? (e.g. can, cup, bottle): ").strip()
        if not label:
            label = "object"

    print(f"\nTracking target: '{label}'")
    pipeline = Pipeline(session_id="demo_001", log_file="session.log")
    pipeline.begin_enrollment(label)

    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Error: could not open camera.")
        sys.exit(1)

    # Give the camera a moment to warm up (common on Mac)
    print("Warming up camera...")
    for _ in range(10):
        cap.read()
    time.sleep(0.5)

    # Verify we can actually get frames
    ret, test_frame = cap.read()
    if not ret or test_frame is None:
        print("Error: camera opened but cannot read frames.")
        print("Make sure no other app is using the camera, and that Terminal has camera permission.")
        print("  System Settings -> Privacy & Security -> Camera -> enable Terminal")
        cap.release()
        sys.exit(1)

    print("=== ENROLLMENT ===")
    print("Point the camera at the object and move it around slowly.")
    print("Press Q to quit.\n")

    while not pipeline.enrollment_guide.is_enrollment_complete():
        ret, frame = cap.read()
        if not ret or frame is None:
            print("Warning: dropped frame, retrying...")
            time.sleep(0.05)
            continue

        if cv2.waitKey(1) & 0xFF == ord("q"):
            cap.release()
            cv2.destroyAllWindows()
            return

        feedback = pipeline.process_enrollment_frame(frame)
        label_text = f"[{feedback.progress_count}/{feedback.target_count}] {feedback.suggested_next_action}"
        print(label_text)

        # Draw the last known enrollment bbox so you can see what was captured
        refs = pipeline.reference_memory.get_references()
        if refs:
            rx, ry, rw, rh = refs[-1].bbox
            cv2.rectangle(frame, (rx, ry), (rx + rw, ry + rh), (0, 255, 100), 2)
            cv2.putText(frame, "enrolled", (rx, ry - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 100), 1)

        color = (0, 200, 255) if not feedback.accepted_frame else (0, 255, 100)
        cv2.putText(frame, label_text, (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(frame, feedback.reason, (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
        cv2.imshow("Tracker", frame)

    pipeline.finish_enrollment()
    print("\n=== TRACKING ===")
    print("Enrollment complete. Tracking started. Press Q to quit.\n")

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.05)
            continue

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        result = pipeline.process_tracking_frame(frame)
        x, y, w, h = result.smoothed_bbox

        if result.state == "tracking":
            color = (0, 255, 0)
        elif result.state == "weak":
            color = (0, 165, 255)
        else:
            color = (0, 0, 255)

        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        status = f"{result.state}  conf={result.confidence:.2f}"
        cv2.putText(frame, status, (x, max(y - 10, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
        cv2.imshow("Tracker", frame)
        print(f"bbox={result.smoothed_bbox}  conf={result.confidence:.2f}  state={result.state}")

    cap.release()
    cv2.destroyAllWindows()
    print("\nDone. Session log saved to session.log")


if __name__ == "__main__":
    main()

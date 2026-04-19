"""
app.py — PhysicalAI Tracker UI

Flow:
  Step 1 SCENE    → camera preview opens
  Step 2 DESCRIBE → user types intent in chat; Claude API parses it
  Step 3 ENROLL   → system guides user to show object from multiple angles
  Step 4 TRACK    → live bbox overlay; Record button saves a clip

Requires:
  pip install anthropic pillow opencv-python ultralytics
  export ANTHROPIC_API_KEY=sk-...
"""

from __future__ import annotations

import os
import threading
import time
import tkinter as tk
from tkinter import scrolledtext, ttk

import cv2
import numpy as np
from PIL import Image, ImageTk

from orchestrator import Pipeline

# ── colours ──────────────────────────────────────────────────────────────────
BG       = "#0d0d1a"
PANEL    = "#12122a"
ACCENT   = "#4cc9f0"
GREEN    = "#7bed9f"
YELLOW   = "#ffd166"
PINK     = "#f72585"
GREY     = "#2a2a4a"
TEXT     = "#e0e0f0"
DIM      = "#555577"

STEP_COLORS = {
    "SCENE":    ACCENT,
    "DESCRIBE": "#f8c8d4",
    "ENROLL":   YELLOW,
    "TRACK":    GREEN,
}


class TrackerApp(tk.Tk):
    STATE_IDLE       = "idle"
    STATE_PARSING    = "parsing"
    STATE_ENROLLMENT = "enrollment"
    STATE_TRACKING   = "tracking"
    STATE_RECORDING  = "recording"

    def __init__(self) -> None:
        super().__init__()
        self.title("PhysicalAI Tracker")
        self.configure(bg=BG)
        self.resizable(True, True)

        self.state      = self.STATE_IDLE
        self.pipeline   = None
        self.label      = ""
        self.cap        = cv2.VideoCapture(1)
        self.recording_frames: list[np.ndarray] = []
        self.recording_track_data: list[dict] = []
        self._photo_ref = None

        # live analysis state
        from collections import deque
        self._trajectory: deque = deque(maxlen=60)   # (cx, cy) of tracked object
        self._all_detections: list[dict] = []
        self._action: str = "—"
        self._speed: float = 0.0
        self._direction: str = "—"

        self._build_ui()
        self._warmup_camera()
        self._set_step("SCENE")
        self._chat_append("system",
            "Welcome to PhysicalAI Tracker.\n\n"
            "Step 1 is live — your camera is running.\n\n"
            "Step 2: Describe what you want to track. "
            "For example:\n"
            "  - track a hand picking up a can\n"
            "  - follow the red cup\n"
            "  - track the water bottle on the desk\n\n"
            "Type below and press Enter or ->"
        )
        self._camera_loop()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=0)   # right sidebar fixed width
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)

        # ── camera panel ──────────────────────────────────────────────────────
        cam_outer = tk.Frame(self, bg=PANEL, padx=2, pady=2)
        cam_outer.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=(10, 5))

        cam_header = tk.Frame(cam_outer, bg=PANEL)
        cam_header.pack(fill=tk.X, padx=8, pady=(6, 2))
        tk.Label(cam_header, text="● SCENE", bg=PANEL, fg=ACCENT,
                 font=("Helvetica", 10, "bold")).pack(side=tk.LEFT)
        self.scene_status = tk.Label(cam_header, text="LIVE", bg=PANEL, fg=GREEN,
                                     font=("Helvetica", 9, "bold"))
        self.scene_status.pack(side=tk.RIGHT)

        self.canvas = tk.Canvas(cam_outer, bg="#05050f", highlightthickness=0,
                                width=700, height=480)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # ── right sidebar ─────────────────────────────────────────────────────
        sidebar = tk.Frame(self, bg=BG, width=300)
        sidebar.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=(10, 5))
        sidebar.pack_propagate(False)

        # -- chat section --
        chat_outer = tk.Frame(sidebar, bg=PANEL, padx=2, pady=2)
        chat_outer.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        tk.Label(chat_outer, text="DESCRIBE TARGET", bg=PANEL, fg=ACCENT,
                 font=("Helvetica", 9, "bold")).pack(anchor=tk.W, padx=8, pady=(6, 2))

        self.chat_box = scrolledtext.ScrolledText(
            chat_outer, bg="#08081a", fg=TEXT, font=("Helvetica", 10),
            wrap=tk.WORD, state=tk.DISABLED, relief=tk.FLAT,
            selectbackground=GREY, width=28,
        )
        self.chat_box.pack(fill=tk.BOTH, expand=True, padx=4)
        self.chat_box.tag_config("system", foreground=ACCENT)
        self.chat_box.tag_config("user",   foreground="#f8c8d4")
        self.chat_box.tag_config("bold",   font=("Helvetica", 10, "bold"))

        input_row = tk.Frame(chat_outer, bg=PANEL)
        input_row.pack(fill=tk.X, padx=4, pady=6)

        self.input_var = tk.StringVar()
        self.entry = tk.Entry(input_row, textvariable=self.input_var,
                              bg=GREY, fg=TEXT, font=("Helvetica", 10),
                              relief=tk.FLAT, insertbackground=TEXT)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 4))
        self.entry.bind("<Return>", lambda _: self._send())

        self.send_btn = tk.Button(input_row, text="->", bg=ACCENT, fg=BG,
                                  font=("Helvetica", 12, "bold"), relief=tk.FLAT,
                                  command=self._send, padx=8, pady=1,
                                  activebackground="#7ddff7")
        self.send_btn.pack(side=tk.RIGHT)

        # -- detections section --
        det_outer = tk.Frame(sidebar, bg=PANEL, padx=2, pady=2)
        det_outer.pack(fill=tk.X, pady=(0, 6))

        tk.Label(det_outer, text="DETECTIONS", bg=PANEL, fg=YELLOW,
                 font=("Helvetica", 9, "bold")).pack(anchor=tk.W, padx=8, pady=(6, 4))

        self._det_frame = tk.Frame(det_outer, bg=PANEL)
        self._det_frame.pack(fill=tk.X, padx=6, pady=(0, 6))

        # placeholder
        self._det_placeholder = tk.Label(self._det_frame, text="No detections yet",
                                         bg=PANEL, fg=DIM, font=("Helvetica", 9))
        self._det_placeholder.pack(anchor=tk.W)

        # -- action section --
        act_outer = tk.Frame(sidebar, bg=PANEL, padx=2, pady=2)
        act_outer.pack(fill=tk.X, pady=(0, 6))

        tk.Label(act_outer, text="ACTION", bg=PANEL, fg=PINK,
                 font=("Helvetica", 9, "bold")).pack(anchor=tk.W, padx=8, pady=(6, 2))

        self._action_var = tk.StringVar(value="—")
        self._action_lbl = tk.Label(act_outer, textvariable=self._action_var,
                                    bg=PANEL, fg=TEXT, font=("Helvetica", 12, "bold"),
                                    wraplength=260, justify=tk.LEFT)
        self._action_lbl.pack(anchor=tk.W, padx=8, pady=(0, 6))

        # -- movement section --
        mov_outer = tk.Frame(sidebar, bg=PANEL, padx=2, pady=2)
        mov_outer.pack(fill=tk.X, pady=(0, 6))

        tk.Label(mov_outer, text="MOVEMENT", bg=PANEL, fg=GREEN,
                 font=("Helvetica", 9, "bold")).pack(anchor=tk.W, padx=8, pady=(6, 2))

        self._traj_canvas = tk.Canvas(mov_outer, bg="#05050f", height=90,
                                      highlightthickness=0)
        self._traj_canvas.pack(fill=tk.X, padx=6, pady=2)

        mov_stats = tk.Frame(mov_outer, bg=PANEL)
        mov_stats.pack(fill=tk.X, padx=8, pady=(2, 6))

        self._speed_var = tk.StringVar(value="Speed: —")
        self._dir_var   = tk.StringVar(value="Dir: —")
        tk.Label(mov_stats, textvariable=self._speed_var, bg=PANEL, fg=GREEN,
                 font=("Helvetica", 9)).pack(side=tk.LEFT, padx=(0, 12))
        tk.Label(mov_stats, textvariable=self._dir_var, bg=PANEL, fg=GREEN,
                 font=("Helvetica", 9)).pack(side=tk.LEFT)

        # ── bottom status bar ─────────────────────────────────────────────────
        bar = tk.Frame(self, bg=PANEL, height=58)
        bar.grid(row=1, column=0, columnspan=2, sticky="ew",
                 padx=10, pady=(0, 10))
        bar.pack_propagate(False)

        # step pills
        steps_frame = tk.Frame(bar, bg=PANEL)
        steps_frame.pack(side=tk.LEFT, fill=tk.Y, padx=12, pady=10)
        self._step_labels: dict[str, tk.Label] = {}
        for i, name in enumerate(("SCENE", "DESCRIBE", "ENROLL", "TRACK"), 1):
            pill = tk.Frame(steps_frame, bg=GREY, padx=10, pady=3)
            pill.pack(side=tk.LEFT, padx=4)
            lbl = tk.Label(pill, text=f"{i}  {name}", bg=GREY, fg=DIM,
                           font=("Helvetica", 9, "bold"))
            lbl.pack()
            self._step_labels[name] = lbl

        # progress
        prog_frame = tk.Frame(bar, bg=PANEL)
        prog_frame.pack(side=tk.LEFT, padx=8, fill=tk.Y)
        self.progress_var = tk.DoubleVar(value=0)
        style = ttk.Style()
        style.theme_use("default")
        style.configure("green.Horizontal.TProgressbar",
                        troughcolor=GREY, background=GREEN, thickness=8)
        self.prog_bar = ttk.Progressbar(prog_frame, variable=self.progress_var,
                                         maximum=5, length=160, mode="determinate",
                                         style="green.Horizontal.TProgressbar")
        self.prog_bar.pack(pady=(16, 2))
        self.prog_label = tk.Label(prog_frame, text="", bg=PANEL, fg=GREEN,
                                   font=("Helvetica", 8))
        self.prog_label.pack()

        # status text
        self.status_var = tk.StringVar(value="Camera ready")
        tk.Label(bar, textvariable=self.status_var, bg=PANEL, fg=DIM,
                 font=("Helvetica", 9), wraplength=220, justify=tk.LEFT
                 ).pack(side=tk.LEFT, padx=8)

        # record button
        self.rec_btn = tk.Button(bar, text="REC", bg=PINK, fg="white",
                                 font=("Helvetica", 11, "bold"), relief=tk.FLAT,
                                 command=self._toggle_record, padx=18,
                                 state=tk.DISABLED,
                                 activebackground="#c91070", disabledforeground="#884466")
        self.rec_btn.pack(side=tk.RIGHT, padx=12, pady=10)

    # ── step indicator ────────────────────────────────────────────────────────

    def _set_step(self, active: str) -> None:
        for name, lbl in self._step_labels.items():
            if name == active:
                lbl.configure(fg=STEP_COLORS.get(name, TEXT),
                               bg=PANEL if name != active else GREY)
            else:
                lbl.configure(fg=DIM)

    # ── chat helpers ──────────────────────────────────────────────────────────

    def _chat_append(self, role: str, text: str) -> None:
        self.chat_box.configure(state=tk.NORMAL)
        prefix = "System\n" if role == "system" else "You\n"
        self.chat_box.insert(tk.END, prefix, (role, "bold"))
        self.chat_box.insert(tk.END, text + "\n\n", role)
        self.chat_box.see(tk.END)
        self.chat_box.configure(state=tk.DISABLED)

    # ── send / parse ──────────────────────────────────────────────────────────

    def _send(self) -> None:
        text = self.input_var.get().strip()
        if not text or self.state != self.STATE_IDLE:
            return
        self.input_var.set("")
        self._chat_append("user", text)
        self.state = self.STATE_PARSING
        self.send_btn.configure(state=tk.DISABLED)
        self._set_step("DESCRIBE")
        self.status_var.set("Parsing your intent with Claude…")
        threading.Thread(target=self._parse_thread, args=(text,), daemon=True).start()

    def _parse_thread(self, text: str) -> None:
        label, reply = _call_claude(text)
        self.after(0, self._on_parsed, label, reply)

    def _on_parsed(self, label: str, reply: str) -> None:
        self.label = label
        self._chat_append("system",
            f"{reply}\n\n"
            f"Starting enrollment for: '{label}'\n"
            "Point the camera at the object and move it slowly — "
            "I'll collect 3–5 reference views automatically."
        )
        self._set_step("ENROLL")
        self.status_var.set(f"Enrolling '{label}' — show it from different angles")
        self.pipeline = Pipeline(
            session_id=f"s{int(time.time())}",
            log_file="session.log",
        )
        self.pipeline.begin_enrollment(label)
        self.state = self.STATE_ENROLLMENT

    # ── record ────────────────────────────────────────────────────────────────

    def _toggle_record(self) -> None:
        if self.state == self.STATE_TRACKING:
            self.state = self.STATE_RECORDING
            self.rec_btn.configure(text="⏹  STOP", bg="#555555")
            self.recording_frames.clear()
            self.recording_track_data.clear()
            self.status_var.set("Recording…")
        elif self.state == self.STATE_RECORDING:
            self._save_recording()
            self.state = self.STATE_TRACKING
            self.rec_btn.configure(text="⏺  RECORD", bg=PINK)
            self.status_var.set(f"Tracking '{self.label}' — press Record to save")

    def _save_recording(self) -> None:
        import json, zipfile, tempfile, shutil

        if not self.recording_frames:
            return

        ts = int(time.time())
        name = f"recording_{ts}"
        zip_path = f"{name}.zip"
        tmp_dir = tempfile.mkdtemp(prefix="tracker_rec_")

        try:
            # 1. Write MP4
            mp4_path = os.path.join(tmp_dir, "video.mp4")
            h, w = self.recording_frames[0].shape[:2]
            out = cv2.VideoWriter(mp4_path, cv2.VideoWriter_fourcc(*"mp4v"), 20, (w, h))
            for frame in self.recording_frames:
                out.write(frame)
            out.release()

            # 2. Write tracking JSON
            json_path = os.path.join(tmp_dir, "tracking.json")
            payload = {
                "session_id": name,
                "label": self.label,
                "recorded_at": ts,
                "frame_count": len(self.recording_frames),
                "fps": 20,
                "frames": self.recording_track_data,
            }
            with open(json_path, "w") as f:
                json.dump(payload, f, indent=2)

            # 3. Copy session log if present
            if os.path.exists("session.log"):
                shutil.copy("session.log", os.path.join(tmp_dir, "session.log"))

            # 4. Zip everything
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for fname in os.listdir(tmp_dir):
                    zf.write(os.path.join(tmp_dir, fname), fname)

        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        self._chat_append("system",
            f"Saved: {zip_path}\n"
            f"  video.mp4  |  tracking.json ({len(self.recording_track_data)} frames)  |  session.log"
        )
        self.status_var.set(f"Saved {zip_path}")

    # ── camera loop ───────────────────────────────────────────────────────────

    def _warmup_camera(self) -> None:
        for _ in range(10):
            self.cap.read()

    def _camera_loop(self) -> None:
        ret, frame = self.cap.read()
        if ret and frame is not None:
            display = frame.copy()

            if self.state == self.STATE_ENROLLMENT and self.pipeline:
                self._draw_enrollment(frame, display)

            elif self.state in (self.STATE_TRACKING, self.STATE_RECORDING) and self.pipeline:
                self._draw_tracking(frame, display)
                if self.state == self.STATE_RECORDING:
                    self.recording_frames.append(frame.copy())
                    if self.pipeline and self.pipeline.overlay_handoff.get_latest_bbox():
                        tr = self.pipeline.overlay_handoff.get_latest_bbox()
                        self.recording_track_data.append({
                            "frame_index": len(self.recording_frames) - 1,
                            "timestamp": tr.timestamp,
                            "bbox": tr.smoothed_bbox,
                            "confidence": tr.confidence,
                            "state": tr.state,
                            "label": self.label,
                        })
                    # REC indicator
                    cv2.circle(display, (display.shape[1] - 22, 22), 9, (0, 0, 220), -1)
                    cv2.putText(display, "REC", (display.shape[1] - 56, 28),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 220), 2)

            self._show_frame(display)

        self.after(30, self._camera_loop)

    def _draw_enrollment(self, frame: np.ndarray, display: np.ndarray) -> None:
        feedback = self.pipeline.process_enrollment_frame(frame)
        prog  = feedback.progress_count
        total = feedback.target_count
        hint  = feedback.suggested_next_action.upper()

        # enrolled bbox
        refs = self.pipeline.reference_memory.get_references()
        if refs:
            rx, ry, rw, rh = refs[-1].bbox
            cv2.rectangle(display, (rx, ry), (rx + rw, ry + rh), (100, 255, 100), 2)
            cv2.putText(display, "enrolled", (rx, max(ry - 8, 14)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 1)

        # overlay text
        cv2.putText(display, f"ENROLL — {hint}", (12, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 210, 0), 2)
        cv2.putText(display, f"References: {prog} / {total}", (12, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

        # in-frame progress bar
        bw = int((prog / total) * 320)
        cv2.rectangle(display, (12, 72), (332, 84), (40, 40, 40), -1)
        cv2.rectangle(display, (12, 72), (12 + bw, 84), (100, 255, 100), -1)

        self.progress_var.set(prog)
        self.prog_label.configure(text=f"{prog}/{total} refs")

        if self.pipeline.enrollment_guide.is_enrollment_complete():
            self.pipeline.finish_enrollment()
            self.state = self.STATE_TRACKING
            self.rec_btn.configure(state=tk.NORMAL)
            self.send_btn.configure(state=tk.NORMAL)
            self._set_step("TRACK")
            self.status_var.set(f"Tracking '{self.label}'  — press ⏺ RECORD to save a clip")
            self._chat_append("system",
                f"Enrollment complete ✓\n\n"
                f"Now tracking '{self.label}'. "
                "Press ⏺ RECORD to capture a clip. "
                "You can describe a new target anytime."
            )

    def _draw_tracking(self, frame: np.ndarray, display: np.ndarray) -> None:
        result = self.pipeline.process_tracking_frame(frame)
        x, y, w, h = result.smoothed_bbox

        color = (
            (100, 255, 100) if result.state == "tracking" and w > 0 else
            (0, 165, 255)   if result.state == "weak"     and w > 0 else
            (80, 80, 200)
        )

        if w > 4 and h > 4:
            cv2.rectangle(display, (x, y), (x + w, y + h), color, 2)
            d = min(20, w // 4, h // 4)
            for cx2, cy2, sx, sy in ((x,y,1,1),(x+w,y,-1,1),(x,y+h,1,-1),(x+w,y+h,-1,-1)):
                cv2.line(display, (cx2, cy2), (cx2 + sx*d, cy2), color, 3)
                cv2.line(display, (cx2, cy2), (cx2, cy2 + sy*d), color, 3)
            label_txt = f"{self.label}  {result.confidence:.0%}"
            cv2.putText(display, label_txt, (x + 4, max(y - 10, 18)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

        state_text = {"tracking": "TRACKING", "weak": "WEAK SIGNAL", "lost": "SEARCHING"}.get(
            result.state, result.state.upper())
        cv2.putText(display, state_text, (12, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)

        # update trajectory
        if w > 4 and h > 4:
            self._trajectory.append((x + w // 2, y + h // 2))

        # run detect_all for sidebar (every frame, YOLO is already loaded)
        grounding = getattr(self.pipeline, '_remote_grounding', None)
        if grounding and hasattr(grounding, 'detect_all'):
            self._all_detections = grounding.detect_all(frame)

        # update all three sidebar panels
        self._update_detections_panel()
        self._update_action_panel(result)
        self._update_movement_panel()

    # ── sidebar panel updates ─────────────────────────────────────────────────

    def _update_detections_panel(self) -> None:
        for w in self._det_frame.winfo_children():
            w.destroy()

        if not self._all_detections:
            tk.Label(self._det_frame, text="No detections", bg=PANEL, fg=DIM,
                     font=("Helvetica", 9)).pack(anchor=tk.W)
            return

        row = tk.Frame(self._det_frame, bg=PANEL)
        row.pack(fill=tk.X)

        PILL_COLORS = {
            "bottle": ("#4cc9f0", "#0d0d1a"),
            "cup":    ("#4cc9f0", "#0d0d1a"),
            "person": ("#f72585", "#ffffff"),
            "hand":   ("#f72585", "#ffffff"),
        }

        for i, det in enumerate(self._all_detections[:6]):
            lbl = det["label"]
            conf = det["confidence"]
            is_target = lbl in (self.label, "bottle" if self.label == "can" else "")
            bg, fg = PILL_COLORS.get(lbl, ("#2a2a4a", "#e0e0f0"))
            if is_target:
                bg = GREEN; fg = "#0d0d1a"

            pill = tk.Frame(row, bg=bg, padx=6, pady=2)
            pill.pack(side=tk.LEFT, padx=2, pady=2)
            tk.Label(pill, text=f"{lbl} {conf:.0%}", bg=bg, fg=fg,
                     font=("Helvetica", 8, "bold")).pack()

    def _update_action_panel(self, result) -> None:
        dets = {d["label"]: d for d in self._all_detections}
        has_person = "person" in dets
        has_target = any(d["label"] in ("bottle", "cup", self.label) for d in self._all_detections)
        obj_moving = self._speed > 8

        action = "Observing scene"
        color  = DIM

        if result.state == "lost":
            action = "Searching for object..."
            color  = "#888888"
        elif has_person and has_target:
            # Check spatial proximity
            person_bbox = dets["person"]["bbox"]
            target_det  = next((d for d in self._all_detections
                                if d["label"] in ("bottle", "cup", self.label)), None)
            if target_det:
                px = person_bbox[0] + person_bbox[2] // 2
                tx = target_det["bbox"][0] + target_det["bbox"][2] // 2
                dist = abs(px - tx)
                frame_w = 1280
                if dist < frame_w * 0.10:
                    action = "Hand picking up object"
                    color  = PINK
                elif dist < frame_w * 0.25:
                    action = "Hand approaching object"
                    color  = YELLOW
                else:
                    action = "Hand + object in scene"
                    color  = ACCENT
        elif has_target and obj_moving:
            action = f"Object moving ({self._direction})"
            color  = GREEN
        elif has_target:
            action = "Object stationary"
            color  = GREEN
        elif has_person:
            action = "Person detected, no object"
            color  = YELLOW

        self._action_var.set(action)
        self._action_lbl.configure(fg=color)

    def _update_movement_panel(self) -> None:
        c = self._traj_canvas
        c.delete("all")
        W = max(c.winfo_width(), 260)
        H = 90

        pts = list(self._trajectory)
        if len(pts) < 2:
            c.create_text(W // 2, H // 2, text="No movement data",
                          fill=DIM, font=("Helvetica", 8))
            self._speed_var.set("Speed: —")
            self._dir_var.set("Dir: —")
            return

        # Normalize to canvas size
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        mn_x, mx_x = min(xs), max(xs)
        mn_y, mx_y = min(ys), max(ys)
        rng_x = max(mx_x - mn_x, 1); rng_y = max(mx_y - mn_y, 1)
        pad = 10

        def norm(px, py):
            nx = pad + int((px - mn_x) / rng_x * (W - 2*pad))
            ny = pad + int((py - mn_y) / rng_y * (H - 2*pad))
            return nx, ny

        # Draw trajectory line with fade
        for i in range(1, len(pts)):
            alpha = int(80 + 175 * (i / len(pts)))
            col = f"#{alpha:02x}ff{alpha:02x}"
            x0, y0 = norm(*pts[i-1])
            x1, y1 = norm(*pts[i])
            c.create_line(x0, y0, x1, y1, fill=col, width=2)

        # Dot at current position
        cx2, cy2 = norm(*pts[-1])
        c.create_oval(cx2-4, cy2-4, cx2+4, cy2+4, fill=GREEN, outline="")

        # Compute speed (px/frame over last 5 frames)
        recent = pts[-6:]
        dx = recent[-1][0] - recent[0][0]
        dy = recent[-1][1] - recent[0][1]
        speed = (dx**2 + dy**2) ** 0.5 / max(len(recent)-1, 1)
        self._speed = speed

        # Direction
        if abs(dx) < 3 and abs(dy) < 3:
            direction = "stationary"
        else:
            h_part = ("right" if dx > 0 else "left") if abs(dx) > 3 else ""
            v_part = ("down"  if dy > 0 else "up")   if abs(dy) > 3 else ""
            direction = f"{v_part}-{h_part}".strip("-") or "stationary"
        self._direction = direction

        self._speed_var.set(f"Speed: {speed:.1f} px/f")
        self._dir_var.set(f"Dir: {direction}")

    def _show_frame(self, frame: np.ndarray) -> None:
        cw = max(self.canvas.winfo_width(), 640)
        ch = max(self.canvas.winfo_height(), 480)
        h, w = frame.shape[:2]
        scale = min(cw / w, ch / h)
        nw, nh = int(w * scale), int(h * scale)
        resized = cv2.resize(frame, (nw, nh))
        rgb     = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        img     = Image.fromarray(rgb)
        photo   = ImageTk.PhotoImage(img)
        self.canvas.create_image(cw // 2, ch // 2, image=photo, anchor=tk.CENTER)
        self._photo_ref = photo

    # ── cleanup ───────────────────────────────────────────────────────────────

    def on_close(self) -> None:
        if self.state == self.STATE_RECORDING:
            self._save_recording()
        self.cap.release()
        self.destroy()


# ── Claude API intent parser ──────────────────────────────────────────────────

# IonRouter option (ionrouter.io/playground) — routes to best available model
# automatically; swap in by replacing the block below with:
#
# import requests
# def _call_claude(text: str) -> tuple[str, str]:
#     api_key = os.environ.get("IONROUTER_API_KEY", "")
#     if not api_key:
#         label = _naive_extract(text)
#         return label, "(IonRouter API key not set — set IONROUTER_API_KEY)\nExtracted: '{label}'"
#     resp = requests.post(
#         "https://ionrouter.io/v1/chat/completions",
#         headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
#         json={
#             "messages": [
#                 {"role": "system", "content": SYSTEM_PROMPT},
#                 {"role": "user",   "content": text},
#             ]
#         },
#         timeout=10,
#     )
#     raw = resp.json()["choices"][0]["message"]["content"].strip()
#     label, reply = _naive_extract(text), raw
#     for line in raw.splitlines():
#         if line.upper().startswith("OBJECT:"): label = line.split(":",1)[1].strip().lower()
#         elif line.upper().startswith("REPLY:"): reply = line.split(":",1)[1].strip()
#     return label, reply

def _call_claude(text: str) -> tuple[str, str]:
    """
    Returns (label, human_reply).
    Falls back gracefully if OPENAI_API_KEY is not set.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        label = _naive_extract(text)
        return label, (
            f"(OpenAI API not configured — set OPENAI_API_KEY to enable smart parsing.)\n"
            f"Extracted target: '{label}'"
        )

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-5.4-mini",
            max_completion_tokens=300,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a computer-vision assistant helping configure an object tracker.\n"
                        "The tracker uses YOLO, which detects these common classes best: "
                        "bottle, cup, bowl, laptop, phone, book, chair, person, hand, backpack.\n\n"
                        "From the user's description, extract:\n"
                        "1. The single best YOLO-detectable object label (lowercase, one word).\n"
                        "   If the user says 'can', map to 'bottle'. "
                        "   If they say 'hand', use 'hand'. "
                        "   Pick the object that YOLO can most reliably detect.\n"
                        "2. A one-sentence confirmation to show the user.\n\n"
                        "Respond in exactly this format:\n"
                        "OBJECT: <label>\n"
                        "REPLY: <one sentence>"
                    ),
                },
                {"role": "user", "content": text},
            ],
        )
        raw = response.choices[0].message.content.strip()
        label, reply = _naive_extract(text), raw

        for line in raw.splitlines():
            if line.upper().startswith("OBJECT:"):
                label = line.split(":", 1)[1].strip().lower()
            elif line.upper().startswith("REPLY:"):
                reply = line.split(":", 1)[1].strip()

        return label, reply

    except Exception as exc:
        label = _naive_extract(text)
        return label, f"(OpenAI error: {exc})\nFalling back to: '{label}'"


def _naive_extract(text: str) -> str:
    """Last-resort: grab last meaningful word as label."""
    stopwords = {"a", "an", "the", "this", "that", "to", "of", "on", "at", "and", "track", "follow"}
    words = [w.strip(".,!?") for w in text.lower().split() if w.strip(".,!?") not in stopwords]
    return words[-1] if words else "object"


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = TrackerApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.geometry("1100x640")
    app.mainloop()

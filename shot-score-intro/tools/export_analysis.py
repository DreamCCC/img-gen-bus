"""原样调用 video_detect 的 analyze_video_file，同时导出画动态图层要用的逐帧数据。

不修改 video_detect 的代码：通过包装 MediaPipe Pose、ShotDetector 和 cv2 绘制调用，
记录每帧 33 个骨骼点、球心、命中帧和投篮内部状态（下蹲帧、出手帧、随手结束帧）。

用法（要在沙箱外运行，cv2 / mediapipe 在沙箱里会段错误）：
  /Users/mmeng/mgs-code/video_detect/basketball_env/bin/python tools/export_analysis.py \
      <视频> data/analysis.json --hoop 2700,449,3046,593
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

VD = Path("/Users/mmeng/mgs-code/video_detect")
sys.path.insert(0, str(VD))

from analysis import pipeline  # noqa: E402

REC: dict = {"pose": [], "ball": {}, "ball_box": {}, "make_frames": [], "writes": 0}


class PoseRecorder:
    def __init__(self, pose, w, h):
        self.pose, self.w, self.h = pose, w, h

    def process(self, rgb):
        res = self.pose.process(rgb)
        if res.pose_landmarks:
            pts = [[round(l.x * self.w, 1), round(l.y * self.h, 1), round(l.visibility, 3)] for l in res.pose_landmarks.landmark]
        else:
            pts = None
        REC["pose"].append(pts)
        return res

    def close(self):
        self.pose.close()


class Cv2Proxy:
    """转发 cv2，只截获球心圆点、球框和写帧（不写 4K 标注视频，省时间）。"""

    def __init__(self, real):
        self._real = real

    def __getattr__(self, name):
        return getattr(self._real, name)

    def circle(self, img, center, radius, color, thickness=None, *a, **k):
        if radius == 4 and tuple(color) == (0, 255, 255):
            REC["ball"][REC["writes"]] = [int(center[0]), int(center[1])]
        return self._real.circle(img, center, radius, color, thickness if thickness is not None else 1, *a, **k)

    def rectangle(self, img, p1, p2, color, thickness=None, *a, **k):
        if tuple(color) == (0, 255, 0) and thickness == 2:
            REC["ball_box"][REC["writes"]] = [int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1])]
        return self._real.rectangle(img, p1, p2, color, thickness if thickness is not None else 1, *a, **k)

    def VideoWriter(self, *a, **k):
        class _W:
            def isOpened(self_inner):
                return True

            def write(self_inner, frame):
                REC["writes"] += 1

            def release(self_inner):
                pass

        return _W()


class RecShotDetector(pipeline.ShotDetector):
    instance = None

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        RecShotDetector.instance = self

    def mark_make(self, frame_idx=None):
        REC["make_frames"].append(frame_idx)
        return super().mark_make(frame_idx)


def to_py(o):
    if isinstance(o, dict):
        return {str(k): to_py(v) for k, v in o.items() if k not in ("image", "keyframes")}
    if isinstance(o, (list, tuple)):
        return [to_py(v) for v in o]
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("--hoop", help="x1,y1,x2,y2")
    ap.add_argument("--weights", default=str(VD / "yolov8n.pt"))
    args = ap.parse_args()

    import cv2

    cap = cv2.VideoCapture(args.video)
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    mp_pose, pose, drawing, styles = pipeline._load_mediapipe_objects()
    pipeline._mp_cache["pose"] = (mp_pose, PoseRecorder(pose, w, h), drawing, styles)
    pipeline.cv2 = Cv2Proxy(cv2)
    pipeline.ShotDetector = RecShotDetector

    hoop = tuple(int(v) for v in args.hoop.split(",")) if args.hoop else None
    cfg = pipeline.AnalysisConfig(
        enable_make=True,
        hoop_roi=hoop,
        yolo_conf=0.1,
        yolo_imgsz=1024,
        multi_ball=False,
        arm_side="right",
        yolo_weights=args.weights,
        lenient_make=True,
        use_hand_distance=True,
    )
    res = pipeline.analyze_video_file(args.video, cfg)

    det = RecShotDetector.instance
    shots = []
    for s in det.shots:
        shots.append(to_py({k: v for k, v in s.items() if k not in ("keyframes", "annotations")}))

    out = {
        "video": os.path.abspath(args.video),
        "config": to_py(cfg.__dict__),
        "fps": res.fps,
        "width": res.frame_width,
        "height": res.frame_height,
        "n_frames": REC["writes"],
        "score": res.score,
        "make_count": res.make_count,
        "make_frames": REC["make_frames"],
        "shot_metrics": to_py(res.shot_metrics),
        "shots": shots,
        "feedback": res.feedback,
        "warnings": res.warnings,
        "frame_history": to_py(res.frame_history),
        "pose": REC["pose"],
        "ball": {str(k): v for k, v in REC["ball"].items()},
        "ball_box": {str(k): v for k, v in REC["ball_box"].items()},
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False))
    print("score", res.score, "makes", res.make_count, "frames", REC["writes"])
    for m in res.shot_metrics:
        print(json.dumps(to_py({k: v for k, v in m.items()}), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

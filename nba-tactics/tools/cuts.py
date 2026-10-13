"""找镜头切换点：相邻帧的 HSV 直方图距离超过阈值就算一刀。

用法：python cuts.py in.mp4 [--from 0] [--to 60] [--th 0.45]
"""
import argparse

import cv2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--from", dest="t0", type=float, default=0)
    ap.add_argument("--to", dest="t1", type=float, default=1e9)
    ap.add_argument("--th", type=float, default=0.45)
    a = ap.parse_args()
    cap = cv2.VideoCapture(a.src)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.set(cv2.CAP_PROP_POS_MSEC, a.t0 * 1000)
    k, prev = int(round(a.t0 * fps)), None
    while True:
        ok, f = cap.read()
        if not ok or k / fps > a.t1:
            break
        hsv = cv2.cvtColor(cv2.resize(f, (160, 90)), cv2.COLOR_BGR2HSV)
        h = cv2.normalize(cv2.calcHist([hsv], [0, 1], None, [32, 16], [0, 180, 0, 256]), None).flatten()
        if prev is not None:
            d = cv2.compareHist(prev, h, cv2.HISTCMP_BHATTACHARYYA)
            if d > a.th:
                print(f"{k / fps:8.3f}s  frame {k:6d}  d={d:.2f}")
        prev, k = h, k + 1


if __name__ == "__main__":
    main()

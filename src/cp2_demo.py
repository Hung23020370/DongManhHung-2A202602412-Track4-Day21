"""CP2: test tay hàm chiếu + ảnh overlay LiDAR ở 3 khoảng cách (gần / vừa / xa).

Chạy từ gốc repo:
    python -m src.cp2_demo
Kết quả: results/figures/cp2_overlay_3_distances.png
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from starter.datasets import load_frame
from starter.projection import (cam_to_image, draw_box2d, overlay_points,
                                project_velo_to_image, velo_to_cam)

OUT = Path("results/figures/cp2_overlay_3_distances.png")
# (frame, khoảng cách mục tiêu của xe Car không bị che/cắt, nhãn ASCII vì cv2 không vẽ được dấu)
TARGETS = [("000025", 10.7, "near"), ("000011", 27.1, "mid"), ("000007", 60.7, "far")]


def hand_test() -> None:
    """Điểm LiDAR (10, 0, 0) của synthetic/000000 phải cho z_cam ~ 9.73, (u, v) ~ (614, 175)."""
    fr = load_frame("data/synthetic", "000000")
    pc = velo_to_cam(np.array([[10.0, 0.0, 0.0]]), fr["calib"])
    uv, _, mask = cam_to_image(pc, fr["calib"].P2, fr["image"].shape)
    print(f"[hand test] z_cam={pc[0, 2]:.3f} (kỳ vọng ~9.73), uv={uv.round(1).tolist()} (kỳ vọng ~[614, 175]), mask={mask.tolist()}")
    bad = np.array([[np.nan, 0, 0], [np.inf, 1, 1], [-10.0, 0, 0], [10.0, 0, 0]])  # NaN, Inf, sau camera, hợp lệ
    _, _, m = cam_to_image(velo_to_cam(bad, fr["calib"]), fr["calib"].P2, fr["image"].shape)
    print(f"[hand test] mask NaN/Inf/sau camera/hợp lệ = {m.tolist()} (kỳ vọng [F, F, F, T])")


def crop_around(img: np.ndarray, bbox, margin: float = 0.6, min_w: int = 300) -> np.ndarray:
    x1, y1, x2, y2 = bbox
    w, h = x2 - x1, y2 - y1
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    half_w = max(w * (0.5 + margin), min_w / 2)
    half_h = half_w * 0.6
    H, W = img.shape[:2]
    xa, xb = int(max(0, cx - half_w)), int(min(W, cx + half_w))
    ya, yb = int(max(0, cy - half_h)), int(min(H, cy + half_h))
    c = img[ya:yb, xa:xb]
    return cv2.resize(c, (600, int(600 * c.shape[0] / c.shape[1])), interpolation=cv2.INTER_CUBIC)


def main() -> None:
    hand_test()
    panels = []
    for frame, target, name in TARGETS:
        fr = load_frame("data/kitti_mini", frame)
        cars = [o for o in fr["labels"] if o.type == "Car" and o.truncated == 0 and o.occluded == 0]
        obj = min(cars, key=lambda o: abs(np.hypot(o.location[0], o.location[2]) - target))
        dist = float(np.hypot(obj.location[0], obj.location[2]))
        uv, depth, _ = project_velo_to_image(fr["points"], fr["calib"], fr["image"].shape)
        vis = overlay_points(fr["image"], uv, depth, radius=1)
        vis = draw_box2d(vis, obj.bbox, label=None)
        panel = crop_around(vis, obj.bbox)
        cv2.rectangle(panel, (0, 0), (600, 28), (0, 0, 0), -1)
        cv2.putText(panel, f"{name}: frame {frame}, Car {dist:.1f} m", (8, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        panels.append(panel)
        print(f"[panel] {name}: frame={frame} car_dist={dist:.1f} m bbox={obj.bbox.round(0).astype(int).tolist()}")
    h = min(p.shape[0] for p in panels)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT), np.hstack([p[:h] for p in panels]))
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()

"""CP4: failure case. Cùng lệch yaw 1°, nhưng metric "điểm trong 2D box" chỉ phát hiện được với xe xa.

Ảnh: hàng trên = xe gần, hàng dưới = xe xa; trái = calib gốc, phải = yaw 1°.
Điểm của xe (trong 3D box GT) tô đỏ, các điểm khác tô xanh nhạt, 2D box GT màu xanh lá.
    python -m src.failure_case
"""
from __future__ import annotations

import cv2
import numpy as np
import pandas as pd

from src.yaw_sweep import outside_pct, points_in_box3d
from starter.datasets import load_frame
from starter.projection import cam_to_image, perturb_extrinsic, velo_to_cam

OUT = "results/figures/fail_01_yaw1deg_near_vs_far.png"
YAW = 1.0


def pick(df: pd.DataFrame, target: float) -> pd.Series:
    d = df.drop_duplicates(["frame", "obj_idx"]).copy()
    d["gap"] = (d.distance_m - target).abs()
    return d.sort_values("gap").iloc[0]


def render(fr, obj, sel, calib, title):
    pts = fr["points"][:, :3]
    uv, _, mask = cam_to_image(velo_to_cam(pts, calib), calib.P2, fr["image"].shape)
    img = fr["image"].copy()
    others = np.zeros(len(pts), bool); others[sel] = True
    car_in_img = mask & others
    cam = velo_to_cam(pts, calib)
    uv_all, _, m_all = cam_to_image(cam, calib.P2, fr["image"].shape)
    full = np.full((len(pts), 2), -1.0); full[m_all] = uv_all
    for (u, v), is_car in zip(full[m_all], others[m_all]):
        cv2.circle(img, (int(u), int(v)), 2 if is_car else 1, (0, 0, 255) if is_car else (255, 200, 120), -1)
    x1, y1, x2, y2 = obj.bbox.astype(int)
    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    hw = max((x2 - x1) * 1.2, 90); hh = hw * 0.6
    H, W = img.shape[:2]
    xa, xb, ya, yb = int(max(0, cx - hw)), int(min(W, cx + hw)), int(max(0, cy - hh)), int(min(H, cy + hh))
    crop = cv2.resize(img[ya:yb, xa:xb], (560, int(560 * (yb - ya) / (xb - xa))), interpolation=cv2.INTER_CUBIC)
    cv2.rectangle(crop, (0, 0), (560, 26), (0, 0, 0), -1)
    cv2.putText(crop, title, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return crop


def main() -> None:
    df = pd.read_csv("results/yaw_perturb_per_object.csv", dtype={"frame": str})
    rows = []
    for label, target in [("NEAR", 9.5), ("FAR", 48.0)]:
        r = pick(df, target)
        fr = load_frame("data/kitti_mini", r.frame)
        obj = fr["labels"][int(r.obj_idx)]
        pts = fr["points"][:, :3]
        sel = points_in_box3d(velo_to_cam(pts, fr["calib"]), obj)
        c0, c1 = fr["calib"], perturb_extrinsic(fr["calib"], yaw_deg=YAW)
        o0, o1 = outside_pct(pts[sel], c0, obj.bbox, fr["image"].shape), outside_pct(pts[sel], c1, obj.bbox, fr["image"].shape)
        # dịch pixel theo trục u của từng điểm (không lọc theo ảnh để so cùng tập điểm)
        def u_of(c):
            pc = velo_to_cam(pts[sel], c); h = np.hstack([pc, np.ones((len(pc), 1))]) @ c.P2.T; return h[:, 0] / h[:, 2]
        shift = float(np.median(np.abs(u_of(c1) - u_of(c0))))
        w = float(obj.bbox[2] - obj.bbox[0])
        print(f"{label}: frame={r.frame} dist={r.distance_m:.1f} m n_pts={int(sel.sum())} bbox_w={w:.0f}px "
              f"median_shift={shift:.1f}px shift/width={100*shift/w:.1f}% outside: {o0:.1f}% -> {o1:.1f}%")
        left = render(fr, obj, sel, c0, f"{label} {r.distance_m:.1f} m (f{r.frame}) yaw 0: outside {o0:.1f}%")
        right = render(fr, obj, sel, c1, f"yaw {YAW:g}: outside {o1:.1f}% (shift {shift:.1f}px, box {w:.0f}px)")
        rows.append(np.hstack([left, right[:left.shape[0]] if right.shape[0] >= left.shape[0] else cv2.copyMakeBorder(right, 0, left.shape[0] - right.shape[0], 0, 0, cv2.BORDER_CONSTANT)]))
    W = max(r.shape[1] for r in rows)
    rows = [cv2.copyMakeBorder(r, 0, 0, 0, W - r.shape[1], cv2.BORDER_CONSTANT) for r in rows]
    cv2.imwrite(OUT, np.vstack(rows)); print("->", OUT)


if __name__ == "__main__":
    main()

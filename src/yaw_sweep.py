"""CP3: sweep lệch yaw LiDAR, đo % điểm của xe chiếu ra ngoài 2D box GT.

Với mỗi xe `Car` không bị che/cắt (truncated=0, occluded=0):
  1. Lấy điểm LiDAR nằm trong 3D box GT (xét trong camera frame, calib gốc) -> "điểm của xe".
  2. Với mỗi mức yaw, chiếu các điểm đó bằng calib đã perturb (starter.projection.perturb_extrinsic).
  3. outside_pct = % điểm của xe KHÔNG rơi vào 2D box GT (kể cả rơi ra ngoài ảnh).
Không có phép ngẫu nhiên nào: kết quả hoàn toàn xác định (seed chỉ ghi để cố định cấu hình).

    python -m src.yaw_sweep
    python -m src.yaw_sweep --help
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from starter.datasets import list_frames, load_frame
from starter.projection import cam_to_image, perturb_extrinsic, velo_to_cam

BINS = [("<15m", 0, 15), ("15-30m", 15, 30), (">=30m", 30, 1e9)]


def points_in_box3d(pts_cam: np.ndarray, obj) -> np.ndarray:
    """Mask điểm (N,3, camera frame) nằm trong box 3D KITTI (location = tâm đáy)."""
    h, w, l = obj.dimensions
    rel = pts_cam - obj.location
    c, s = np.cos(obj.rotation_y), np.sin(obj.rotation_y)
    # R_y(ry) đưa box -> camera, nên đưa điểm về hệ của box bằng R_y^T
    x = c * rel[:, 0] - s * rel[:, 2]
    z = s * rel[:, 0] + c * rel[:, 2]
    y = rel[:, 1]
    with np.errstate(invalid="ignore"):
        return np.isfinite(pts_cam).all(axis=1) & (np.abs(x) <= l / 2) & (np.abs(z) <= w / 2) & (y <= 0) & (y >= -h)


def outside_pct(pts_velo: np.ndarray, calib, bbox, image_shape) -> float:
    uv, _, _ = cam_to_image(velo_to_cam(pts_velo, calib), calib.P2, image_shape)
    x1, y1, x2, y2 = bbox
    inside = ((uv[:, 0] >= x1) & (uv[:, 0] <= x2) & (uv[:, 1] >= y1) & (uv[:, 1] <= y2)).sum()
    return 100.0 * (1 - inside / len(pts_velo))


def run(data_root: str, yaws: list[float], min_points: int) -> pd.DataFrame:
    rows = []
    for frame in list_frames(data_root):
        fr = load_frame(data_root, frame)
        pts = fr["points"][:, :3]
        pts_cam0 = velo_to_cam(pts, fr["calib"])
        for k, obj in enumerate(fr["labels"]):
            if obj.type != "Car" or obj.truncated != 0 or obj.occluded != 0:
                continue
            sel = points_in_box3d(pts_cam0, obj)
            if sel.sum() < min_points:
                continue
            dist = float(np.hypot(obj.location[0], obj.location[2]))
            width_px = float(obj.bbox[2] - obj.bbox[0])
            for yaw in yaws:
                calib = perturb_extrinsic(fr["calib"], yaw_deg=yaw)
                rows.append(dict(frame=frame, obj_idx=k, distance_m=round(dist, 2), bbox_w_px=round(width_px, 1),
                                 n_pts=int(sel.sum()), yaw_deg=yaw,
                                 outside_pct=outside_pct(pts[sel], calib, obj.bbox, fr["image"].shape)))
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="Sweep yaw LiDAR và đo % điểm của xe rơi ngoài 2D box GT")
    ap.add_argument("--data-root", default="data/kitti_mini")
    ap.add_argument("--yaws", type=float, nargs="+", default=[-3, -2, -1, -0.5, 0, 0.5, 1, 2, 3])
    ap.add_argument("--min-points", type=int, default=10, help="bỏ xe có ít điểm hơn ngưỡng này")
    ap.add_argument("--seed", type=int, default=0, help="chỉ để ghi cấu hình (thí nghiệm không ngẫu nhiên)")
    ap.add_argument("--out-prefix", default="results/yaw_perturb")
    args = ap.parse_args()

    np.random.seed(args.seed)
    df = run(args.data_root, args.yaws, args.min_points)
    df["abs_yaw_deg"] = df.yaw_deg.abs()
    df["dist_bin"] = pd.cut(df.distance_m, [b[1] for b in BINS] + [1e9], labels=[b[0] for b in BINS], right=False)
    base = df[df.yaw_deg == 0].set_index(["frame", "obj_idx"]).outside_pct
    df["delta_vs_yaw0_pct"] = df.outside_pct - df.set_index(["frame", "obj_idx"]).index.map(base).values
    out = Path(args.out_prefix)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.round(3).to_csv(f"{out}_per_object.csv", index=False)

    n_obj = df.groupby("dist_bin", observed=True).apply(lambda g: len(g[["frame", "obj_idx"]].drop_duplicates()))
    summ = (df.groupby(["dist_bin", "abs_yaw_deg"], observed=True)
              .agg(n_rows=("outside_pct", "size"), outside_pct_mean=("outside_pct", "mean"),
                   outside_pct_median=("outside_pct", "median"), delta_mean=("delta_vs_yaw0_pct", "mean")).reset_index())
    summ.insert(2, "n_objects", summ.dist_bin.map(n_obj).astype(int))   # n_rows = n_objects x số dấu yaw (+/-)
    summ.round(3).to_csv(f"{out}_sweep.csv", index=False)
    Path(f"{out}_config.json").write_text(json.dumps(dict(
        data_root=args.data_root, yaws_deg=args.yaws, min_points=args.min_points, seed=args.seed,
        object_filter="Car, truncated==0, occluded==0", points="inside GT 3D box (camera frame, original calib)",
        metric="% of car points NOT inside GT 2D bbox after projection (outside image counts as outside)",
        perturbation="perturb_extrinsic(yaw_deg) rotation about LiDAR z axis", n_objects=int(df[["frame", "obj_idx"]].drop_duplicates().shape[0])),
        indent=2, ensure_ascii=False))

    # --- biểu đồ ---
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for name, *_ in BINS:
        s = summ[summ.dist_bin == name]
        ax[0].plot(s.abs_yaw_deg, s.outside_pct_mean, "o-", label=f"{name} (n={int(s.n_objects.iloc[0])})")
    ax[0].axhline(10, color="gray", ls="--", lw=1); ax[0].set_xlabel("|yaw| (độ)"); ax[0].set_ylabel("% điểm của xe ngoài 2D box")
    ax[0].set_title("Trung bình theo nhóm khoảng cách"); ax[0].legend()
    d1 = df[df.abs_yaw_deg == 1.0].groupby(["frame", "obj_idx"]).agg(d=("distance_m", "first"), o=("outside_pct", "mean"))
    ax[1].scatter(d1.d, d1.o, s=18); ax[1].axhline(10, color="gray", ls="--", lw=1)
    ax[1].axvline(15, color="gray", ls=":", lw=1); ax[1].axvline(30, color="gray", ls=":", lw=1)
    ax[1].set_xlabel("khoảng cách xe (m)"); ax[1].set_ylabel("% điểm ngoài 2D box tại |yaw| = 1°"); ax[1].set_title("Từng xe, |yaw| = 1°")
    fig.tight_layout(); fig_path = Path("results/figures/yaw_sweep_outside_pct.png"); fig_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_path, dpi=130)
    print(summ.round(2).to_string(index=False)); print("objects:", int(df[["frame", "obj_idx"]].drop_duplicates().shape[0]), "->", fig_path)


if __name__ == "__main__":
    main()

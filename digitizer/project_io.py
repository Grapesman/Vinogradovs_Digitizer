from __future__ import annotations

import json
from pathlib import Path

from .models import AxisScale, CurveConfig, CurveData, DepthCalibration, ProjectData


def save_project(path: str | Path, project: ProjectData) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(project.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _legacy_scale_for_curve(cfg: CurveConfig, index: int) -> AxisScale:
    rx, ry, rw, rh = cfg.roi
    return AxisScale(
        id=f"legacy_scale_{index + 1}",
        name=f"Шкала {index + 1}",
        unit=cfg.unit,
        value_min=cfg.x_min,
        value_max=cfg.x_max,
        x1=rx,
        x2=rx + rw,
        scale_type=cfg.scale_type,
        roi=cfg.roi,
    )


def load_project(path: str | Path) -> ProjectData:
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))

    depth = DepthCalibration(**raw["depth"]) if raw.get("depth") else None

    scales: list[AxisScale] = []
    for item in raw.get("scales", []):
        d = dict(item)
        d["roi"] = tuple(d.get("roi", (0, 0, 0, 0)))
        scales.append(AxisScale(**d))

    curves: list[CurveData] = []
    for idx, item in enumerate(raw.get("curves", [])):
        cfg_raw = dict(item.get("config", {}))
        cfg_raw["roi"] = tuple(cfg_raw.get("roi", (0, 0, 0, 0)))
        cfg_raw["color_bgr"] = tuple(cfg_raw.get("color_bgr", (255, 0, 0)))
        cfg_raw["color_samples_bgr"] = [
            tuple(c) for c in cfg_raw.get("color_samples_bgr", [])
        ]
        cfg_raw["sample_points_xy"] = [
            tuple(p) for p in cfg_raw.get("sample_points_xy", [])
        ]
        if cfg_raw.get("seed_xy") is not None:
            cfg_raw["seed_xy"] = tuple(cfg_raw["seed_xy"])
        cfg_raw.setdefault("scale_id", "")
        cfg_raw.setdefault("smooth_window", 11)
        cfg_raw.setdefault("remove_grid", True)
        cfg_raw.setdefault("grid_strength", 1.0)
        cfg_raw.setdefault("x_min", 0.0)
        cfg_raw.setdefault("x_max", 1.0)
        cfg_raw.setdefault("scale_type", "linear")
        cfg = CurveConfig(**cfg_raw)

        # v2.0 projects had scale calibration embedded in each curve.
        if not cfg.scale_id:
            legacy = _legacy_scale_for_curve(cfg, idx)
            # Reuse an equivalent scale if one was already generated.
            match = next(
                (
                    s for s in scales
                    if s.roi == legacy.roi
                    and s.value_min == legacy.value_min
                    and s.value_max == legacy.value_max
                    and s.scale_type == legacy.scale_type
                    and s.unit == legacy.unit
                ),
                None,
            )
            if match is None:
                scales.append(legacy)
                cfg.scale_id = legacy.id
            else:
                cfg.scale_id = match.id

        curves.append(
            CurveData(
                config=cfg,
                points_xy=[tuple(p) for p in item.get("points_xy", [])],
                points_hv=[tuple(p) for p in item.get("points_hv", [])],
                quality={str(k): float(v) for k, v in item.get("quality", {}).items()},
            )
        )

    def resolve_file(value: str) -> str:
        if not value:
            return ""
        p = Path(value)
        if not p.is_absolute():
            p = (path.parent / p).resolve()
        return str(p)

    return ProjectData(
        image_path=resolve_file(raw.get("image_path", "")),
        source_image_path=resolve_file(raw.get("source_image_path", "")),
        depth=depth,
        scales=scales,
        curves=curves,
        depth_step=float(raw.get("depth_step", 0.1)),
        version=str(raw.get("version", "1.0")),
    )

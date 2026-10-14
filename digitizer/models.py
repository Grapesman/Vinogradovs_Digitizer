from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal, Optional

ScaleType = Literal["linear", "log"]


@dataclass
class DepthCalibration:
    y1: float
    h1: float
    y2: float
    h2: float

    def is_valid(self) -> bool:
        return abs(self.y2 - self.y1) > 1e-9 and self.h1 != self.h2


@dataclass
class AxisScale:
    """Horizontal value scale calibrated independently of a curve ROI."""

    id: str
    name: str
    unit: str = ""
    value_min: float = 0.0
    value_max: float = 1.0
    x1: float = 0.0
    x2: float = 1.0
    scale_type: ScaleType = "linear"
    roi: tuple[float, float, float, float] = (0, 0, 0, 0)
    division: Optional[float] = None

    def is_valid(self) -> bool:
        if abs(self.x2 - self.x1) <= 1e-9 or self.value_min == self.value_max:
            return False
        if self.scale_type == "log" and (self.value_min <= 0 or self.value_max <= 0):
            return False
        return True


@dataclass
class CurveConfig:
    name: str
    unit: str = ""
    # scale_id is the primary calibration reference in v2.1+.
    scale_id: str = ""
    roi: tuple[float, float, float, float] = (0, 0, 0, 0)  # x, y, w, h
    color_bgr: tuple[int, int, int] = (255, 0, 0)  # legacy / first sample
    color_samples_bgr: list[tuple[int, int, int]] = field(default_factory=list)
    sample_points_xy: list[tuple[float, float]] = field(default_factory=list)
    color_tolerance: float = 28.0
    # Conservative per-curve LAB/HSV classifier. Distinguish nearby colours
    # using competing palettes and mark uncertain pixels rather than guessing.
    precise_color: bool = True
    competitor_margin: float = 7.0
    hue_tolerance: int = 10   # OpenCV hue units (0–179); used for saturated ink
    seed_xy: Optional[tuple[float, float]] = None
    max_jump_px: float = 24.0
    max_gap_rows: int = 10
    smooth_window: int = 9
    remove_grid: bool = True
    grid_strength: float = 1.1
    # Legacy inline scale fields kept so v2.0 projects/tests remain readable.
    x_min: float = 0.0
    x_max: float = 1.0
    scale_type: ScaleType = "linear"

    def effective_colors(self) -> list[tuple[int, int, int]]:
        colors = [tuple(map(int, c)) for c in self.color_samples_bgr if len(c) == 3]
        return colors or [tuple(map(int, self.color_bgr))]


@dataclass
class CurveData:
    config: CurveConfig
    points_xy: list[tuple[float, float]] = field(default_factory=list)
    points_hv: list[tuple[float, float]] = field(default_factory=list)
    quality: dict[str, float] = field(default_factory=dict)


@dataclass
class ProjectData:
    image_path: str = ""
    source_image_path: str = ""
    depth: Optional[DepthCalibration] = None
    scales: list[AxisScale] = field(default_factory=list)
    curves: list[CurveData] = field(default_factory=list)
    depth_step: float = 0.1
    version: str = "2.3"

    def to_dict(self) -> dict:
        return asdict(self)

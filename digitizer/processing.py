from __future__ import annotations

import math
from dataclasses import replace
from typing import Iterable, Sequence

import cv2
import numpy as np

from .models import AxisScale, CurveConfig, DepthCalibration


def rotate_image_90(image: np.ndarray, clockwise: bool = True) -> np.ndarray:
    flag = cv2.ROTATE_90_CLOCKWISE if clockwise else cv2.ROTATE_90_COUNTERCLOCKWISE
    return cv2.rotate(image, flag)


def auto_deskew(image: np.ndarray, max_abs_angle: float = 12.0) -> tuple[np.ndarray, float]:
    """Estimate small chart/page rotation from long lines and rotate back."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    min_len = max(80, int(min(image.shape[:2]) * 0.18))
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 1800.0, threshold=90,
        minLineLength=min_len, maxLineGap=12,
    )
    if lines is None:
        return image.copy(), 0.0

    deviations: list[float] = []
    weights: list[float] = []
    for x1, y1, x2, y2 in lines[:, 0, :]:
        dx, dy = float(x2 - x1), float(y2 - y1)
        length = math.hypot(dx, dy)
        if length < min_len:
            continue
        angle = math.degrees(math.atan2(dy, dx))
        folded = ((angle + 45.0) % 90.0) - 45.0
        if abs(folded) <= max_abs_angle:
            deviations.append(folded)
            weights.append(length)

    if not deviations:
        return image.copy(), 0.0

    angle = float(np.average(np.asarray(deviations), weights=np.asarray(weights)))
    if abs(angle) < 0.05:
        return image.copy(), 0.0

    h, w = image.shape[:2]
    center = (w / 2.0, h / 2.0)
    m = cv2.getRotationMatrix2D(center, angle, 1.0)
    cos, sin = abs(m[0, 0]), abs(m[0, 1])
    new_w = int(h * sin + w * cos)
    new_h = int(h * cos + w * sin)
    m[0, 2] += new_w / 2.0 - center[0]
    m[1, 2] += new_h / 2.0 - center[1]
    rotated = cv2.warpAffine(
        image, m, (new_w, new_h), flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255),
    )
    return rotated, angle


def order_quad_points(points: Sequence[tuple[float, float]]) -> np.ndarray:
    if len(points) != 4:
        raise ValueError("Для перспективы нужно ровно 4 точки")
    pts = np.asarray(points, dtype=np.float32)
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).reshape(-1)
    rect[0] = pts[np.argmin(s)]      # top-left
    rect[2] = pts[np.argmax(s)]      # bottom-right
    rect[1] = pts[np.argmin(d)]      # top-right
    rect[3] = pts[np.argmax(d)]      # bottom-left
    return rect


def perspective_warp(image: np.ndarray, points: Sequence[tuple[float, float]]) -> np.ndarray:
    """Rectify a quadrilateral selected clockwise or in arbitrary order."""
    rect = order_quad_points(points)
    tl, tr, br, bl = rect
    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_w = max(2, int(round(max(width_a, width_b))))
    max_h = max(2, int(round(max(height_a, height_b))))
    dst = np.array(
        [[0, 0], [max_w - 1, 0], [max_w - 1, max_h - 1], [0, max_h - 1]],
        dtype=np.float32,
    )
    m = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(
        image, m, (max_w, max_h), flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255),
    )


def pixel_y_to_depth(y: np.ndarray | float, cal: DepthCalibration) -> np.ndarray | float:
    if not cal.is_valid():
        raise ValueError("Некорректная калибровка глубины")
    return cal.h1 + (np.asarray(y) - cal.y1) * (cal.h2 - cal.h1) / (cal.y2 - cal.y1)


def pixel_x_to_value(
    x: np.ndarray | float, calibration: AxisScale | CurveConfig
) -> np.ndarray | float:
    """Convert image X to value using an independent scale or legacy curve calibration."""
    if isinstance(calibration, AxisScale):
        if not calibration.is_valid():
            raise ValueError("Некорректная калибровка шкалы")
        x1, x2 = float(calibration.x1), float(calibration.x2)
        v1, v2 = float(calibration.value_min), float(calibration.value_max)
        scale_type = calibration.scale_type
    else:
        rx, _ry, rw, _rh = calibration.roi
        if rw <= 0:
            raise ValueError("Ширина ROI должна быть больше нуля")
        x1, x2 = float(rx), float(rx + rw)
        v1, v2 = float(calibration.x_min), float(calibration.x_max)
        scale_type = calibration.scale_type

    frac = (np.asarray(x, dtype=float) - x1) / (x2 - x1)
    # Do not extrapolate wildly outside the calibrated plotting track.
    frac = np.clip(frac, 0.0, 1.0)
    if scale_type == "linear":
        return v1 + frac * (v2 - v1)
    if v1 <= 0 or v2 <= 0:
        raise ValueError("Для логарифмической шкалы минимальное и максимальное значения должны быть > 0")
    log_min = math.log10(v1)
    log_max = math.log10(v2)
    return np.power(10.0, log_min + frac * (log_max - log_min))


def _safe_roi(image: np.ndarray, roi: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    x, y, w, h = [int(round(v)) for v in roi]
    x = int(np.clip(x, 0, max(0, image.shape[1] - 1)))
    y = int(np.clip(y, 0, max(0, image.shape[0] - 1)))
    w = max(1, min(w, image.shape[1] - x))
    h = max(1, min(h, image.shape[0] - y))
    return x, y, w, h


def build_grid_mask(roi_bgr: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """Detect long horizontal/vertical grid strokes in a chart crop.

    The mask is intentionally conservative: only long line-like structures are
    returned, so handwriting/curves are less likely to be removed.
    """
    if roi_bgr.size == 0:
        return np.zeros(roi_bgr.shape[:2], dtype=np.uint8)
    gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
    # Adaptive threshold tolerates uneven phone-photo lighting.
    inv = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV,
        31, 10,
    )
    h, w = gray.shape
    s = float(np.clip(strength, 0.35, 3.0))
    # Long kernels target chart grid/separators rather than locally vertical
    # portions of the measured curve. Increasing strength shortens the kernels.
    hk = max(18, int((w * 0.12) / s))
    vk = max(24, int((h * 0.12) / s))
    horiz = cv2.morphologyEx(inv, cv2.MORPH_OPEN, np.ones((1, hk), np.uint8))
    vert = cv2.morphologyEx(inv, cv2.MORPH_OPEN, np.ones((vk, 1), np.uint8))
    grid = cv2.bitwise_or(horiz, vert)
    # Slight dilation removes anti-aliased fringe around grid strokes.
    grid = cv2.dilate(grid, np.ones((2, 2), np.uint8), iterations=1)
    return grid


def detect_vertical_track_lines(
    image_bgr: np.ndarray,
    y0: int | None = None,
    y1: int | None = None,
    min_separation_px: int = 24,
    max_lines: int = 24,
) -> list[int]:
    """Find likely vertical track separators using dark-pixel projection.

    Returns x coordinates sorted left-to-right. It is designed as a visual aid,
    not as an irreversible automatic crop decision.
    """
    h, w = image_bgr.shape[:2]
    y0 = int(np.clip(0 if y0 is None else y0, 0, h - 1))
    y1 = int(np.clip(h if y1 is None else y1, y0 + 1, h))
    crop = image_bgr[y0:y1]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    # Dark strokes and edges both contribute to separator score.
    dark = (gray < np.percentile(gray, 38)).astype(np.float32)
    edges = cv2.Canny(gray, 40, 120).astype(np.float32) / 255.0
    score = 0.65 * dark.mean(axis=0) + 0.35 * edges.mean(axis=0)
    score = np.convolve(score, np.ones(5) / 5.0, mode="same")

    threshold = max(float(np.percentile(score, 92)), float(score.mean() + score.std()))
    idx = np.flatnonzero(score >= threshold)
    if idx.size == 0:
        return []

    groups = np.split(idx, np.where(np.diff(idx) > 2)[0] + 1)
    candidates: list[tuple[float, int]] = []
    for g in groups:
        if g.size == 0:
            continue
        x = int(round(float(np.average(g, weights=score[g] + 1e-6))))
        candidates.append((float(score[g].max()), x))
    candidates.sort(reverse=True)

    chosen: list[int] = []
    for _, x in candidates:
        if all(abs(x - prev) >= min_separation_px for prev in chosen):
            chosen.append(x)
        if len(chosen) >= max_lines:
            break
    return sorted(chosen)


def estimate_scale_division(
    image_bgr: np.ndarray, scale: AxisScale
) -> tuple[float | None, list[int]]:
    """Estimate a major vertical-grid division for a calibrated linear scale.

    The calibration itself always comes from the user-selected endpoints. Grid
    detection is only a diagnostic and a convenient estimate of the printed
    division price.
    """
    if not scale.is_valid() or scale.scale_type != "linear":
        return None, []
    if scale.roi[2] <= 2 or scale.roi[3] <= 2:
        return None, []
    x, y, w, h = _safe_roi(image_bgr, scale.roi)
    crop = image_bgr[y:y + h, x:x + w]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    inv = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 9
    )
    kernel_h = max(12, int(h * 0.35))
    vert = cv2.morphologyEx(inv, cv2.MORPH_OPEN, np.ones((kernel_h, 1), np.uint8))
    score = vert.mean(axis=0)
    threshold = max(18.0, float(np.percentile(score, 86)))
    idx = np.flatnonzero(score >= threshold)
    if idx.size == 0:
        return None, []
    groups = np.split(idx, np.where(np.diff(idx) > 2)[0] + 1)
    centers = [int(round(float(g.mean()))) for g in groups if g.size]
    # Remove near-duplicates and require useful spacing.
    filtered: list[int] = []
    for cx in centers:
        if not filtered or cx - filtered[-1] >= 5:
            filtered.append(cx)
    if len(filtered) < 2:
        return None, [x + c for c in filtered]
    global_x = np.asarray([x + c for c in filtered], dtype=float)
    values = np.asarray(pixel_x_to_value(global_x, scale), dtype=float)
    diffs = np.abs(np.diff(values))
    diffs = diffs[diffs > 1e-12]
    if diffs.size == 0:
        return None, [int(v) for v in global_x]
    division = float(np.median(diffs))
    return division, [int(v) for v in global_x]


def _runs_to_centers(xs: np.ndarray) -> np.ndarray:
    if xs.size == 0:
        return np.empty(0, dtype=float)
    split_idx = np.where(np.diff(xs) > 1)[0] + 1
    groups = np.split(xs, split_idx)
    return np.asarray([float(g.mean()) for g in groups if g.size], dtype=float)


def sample_ink_color_at(
    image_bgr: np.ndarray, x: int, y: int, radius: int = 3
) -> tuple[int, int, int]:
    """Sample line ink despite grey grid/paper in a small pipette patch.

    Preference is given to coloured neighbours matching the clicked pixel.
    For black curves (without chroma), retain the local median sample.
    Always sample from the original image, never from a preview overlay.
    """
    h, w = image_bgr.shape[:2]
    x, y = int(np.clip(x, 0, w - 1)), int(np.clip(y, 0, h - 1))
    x0, x1 = max(0, x - radius), min(w, x + radius + 1)
    y0, y1 = max(0, y - radius), min(h, y + radius + 1)
    patch = image_bgr[y0:y1, x0:x1]
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
    ink = (hsv[:, :, 1] >= 32) & (hsv[:, :, 2] >= 50)
    if int(np.count_nonzero(ink)) >= 2:
        pixels = patch[ink].astype(np.float32)
        lab = cv2.cvtColor(patch, cv2.COLOR_BGR2LAB)[ink].astype(np.float32)
        clicked = cv2.cvtColor(
            image_bgr[y:y+1, x:x+1], cv2.COLOR_BGR2LAB
        )[0, 0].astype(np.float32)
        delta = np.linalg.norm((lab - clicked) * [0.7, 1.5, 1.5], axis=1)
        near = pixels[np.argsort(delta)[: min(7, len(pixels))]]
        return tuple(int(v) for v in np.median(near, axis=0))
    return tuple(int(v) for v in np.median(patch.reshape(-1, 3), axis=0))


def palette_separation(
    first: Sequence[tuple[int, int, int]], second: Sequence[tuple[int, int, int]]
) -> float:
    """Smallest weighted LAB distance between any two colour sample groups."""
    if not first or not second:
        return float("inf")
    def lab(colors):
        pixels = np.asarray(colors, dtype=np.uint8).reshape(-1, 1, 3)
        return cv2.cvtColor(pixels, cv2.COLOR_BGR2LAB).astype(np.float32).reshape(-1, 3)
    a, b = lab(first), lab(second)
    delta = (a[:, None, :] - b[None, :, :]) * [0.65, 1.6, 1.6]
    return float(np.linalg.norm(delta, axis=2).min())


def _palette_distance(
    lab_roi: np.ndarray,
    hsv_roi: np.ndarray,
    color_samples: Sequence[tuple[int, int, int]],
    precise: bool,
    hue_tolerance: int,
) -> np.ndarray:
    """Minimum ink colour distance, allowing multiple *same-curve* samples.

    OpenCV LAB encodes L/a/b as 0..255. In precise mode luminance is
    de-emphasized and chroma is amplified; JPEG and uneven paper lighting
    normally affect luminance more than the ink's actual colour family.
    Hue is circular and only reliable for saturated samples and pixels.
    """
    refs = np.asarray(color_samples, dtype=np.uint8).reshape(-1, 1, 3)
    ref_lab = cv2.cvtColor(refs, cv2.COLOR_BGR2LAB).astype(np.float32).reshape(-1, 3)
    ref_hsv = cv2.cvtColor(refs, cv2.COLOR_BGR2HSV).reshape(-1, 3)
    if precise:
        weights = np.asarray([0.65, 1.6, 1.6], dtype=np.float32)
    else:
        weights = np.ones(3, dtype=np.float32)
    dist = np.full(lab_roi.shape[:2], np.inf, dtype=np.float32)
    for lab_ref, hsv_ref in zip(ref_lab, ref_hsv):
        d = np.linalg.norm((lab_roi - lab_ref) * weights, axis=2)
        if precise and hsv_ref[1] >= 25:
            dh = np.abs(hsv_roi[:, :, 0].astype(np.int16) - int(hsv_ref[0]))
            dh = np.minimum(dh, 180 - dh)
            # Exclude colours with a distinguishable hue; do not exclude
            # faint areas with unreliable low saturation solely by hue.
            reliable = hsv_roi[:, :, 1] >= 25
            d = np.where(reliable & (dh > hue_tolerance), np.inf, d)
        np.minimum(dist, d, out=dist)
    return dist


def analyze_color_selection(
    image_bgr: np.ndarray,
    cfg: CurveConfig,
    competitors: Sequence[CurveConfig] = (),
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return target mask, target colour distance and ambiguous-pixel mask.

    Competitor exclusion only acts inside each other curve's overlapping
    chart ROI. Uncertain pixels are omitted instead of silently assigned.
    The ambiguity overlay is explicitly diagnostic, *not* a confidence claim.
    """
    x, y, w, h = _safe_roi(image_bgr, cfg.roi)
    roi = image_bgr[y:y + h, x:x + w]
    lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB).astype(np.float32)
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    own_dist = _palette_distance(
        lab, hsv, cfg.effective_colors(), cfg.precise_color, cfg.hue_tolerance
    )
    accepted = own_dist <= float(cfg.color_tolerance)

    # Paper/background gate: a neutral grey print is not a coloured ink.
    # Dark/black curves remain possible when explicitly sampled.
    sat, val = hsv[:, :, 1], hsv[:, :, 2]
    accepted &= (sat >= 14) | (val <= 170)
    ambiguous = np.zeros((h, w), dtype=bool)

    if cfg.precise_color:
        for other in competitors:
            if other is cfg:
                continue
            ox, oy, ow, oh = _safe_roi(image_bgr, other.roi)
            left, right = max(x, ox), min(x + w, ox + ow)
            top, bottom = max(y, oy), min(y + h, oy + oh)
            if left >= right or top >= bottom:
                continue
            xx0, xx1 = left - x, right - x
            yy0, yy1 = top - y, bottom - y
            other_dist = _palette_distance(
                lab[yy0:yy1, xx0:xx1], hsv[yy0:yy1, xx0:xx1],
                other.effective_colors(), True, other.hue_tolerance,
            )
            # A pixel with tiny distance difference is unresolvable by
            # colour alone. Keep it visible as uncertainty, not a curve.
            locally_ambiguous = (
                accepted[yy0:yy1, xx0:xx1]
                & (other_dist <= own_dist[yy0:yy1, xx0:xx1] + cfg.competitor_margin)
            )
            ambiguous[yy0:yy1, xx0:xx1] |= locally_ambiguous
            accepted[yy0:yy1, xx0:xx1] &= ~locally_ambiguous

    mask = accepted.astype(np.uint8) * 255
    if cfg.remove_grid:
        grid = build_grid_mask(roi, cfg.grid_strength)
        mask[grid > 0] = 0
    # Small gaps from JPEG and grid crossings only. Avoid large dilation
    # which can fuse two near-parallel differently coloured curves.
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8))
    return mask, own_dist, ambiguous.astype(np.uint8) * 255


def build_color_mask(
    image_bgr: np.ndarray,
    cfg: CurveConfig,
    competitors: Sequence[CurveConfig] = (),
) -> tuple[np.ndarray, np.ndarray]:
    mask, dist, _ambiguous = analyze_color_selection(image_bgr, cfg, competitors)
    return mask, dist

def trace_curve_from_seed(
    image_bgr: np.ndarray,
    cfg: CurveConfig,
    competitors: Sequence[CurveConfig] = (),
) -> tuple[list[tuple[float, float]], np.ndarray]:
    if cfg.seed_xy is None:
        raise ValueError("Сначала выберите точку на кривой пипеткой")

    rx, ry, rw, rh = _safe_roi(image_bgr, cfg.roi)
    mask, _dist = build_color_mask(image_bgr, cfg, competitors)
    h, w = mask.shape
    sx = int(round(cfg.seed_xy[0] - rx))
    sy = int(round(cfg.seed_xy[1] - ry))
    sx = int(np.clip(sx, 0, w - 1))
    sy = int(np.clip(sy, 0, h - 1))

    row_candidates: list[np.ndarray] = []
    for yy in range(h):
        xs = np.flatnonzero(mask[yy] > 0)
        row_candidates.append(_runs_to_centers(xs))

    seed_x = float(sx)
    seed_y = sy
    found_seed = False
    for radius in range(0, min(30, h)):
        test_rows = [sy] if radius == 0 else [sy - radius, sy + radius]
        for yy in test_rows:
            if yy < 0 or yy >= h:
                continue
            cands = row_candidates[yy]
            if cands.size:
                idx = int(np.argmin(np.abs(cands - sx)))
                if abs(cands[idx] - sx) <= max(10.0, cfg.max_jump_px):
                    seed_x = float(cands[idx])
                    seed_y = yy
                    found_seed = True
                    break
        if found_seed:
            break
    if not found_seed:
        raise ValueError("Не удалось привязать стартовую точку к маске цвета. Увеличьте допуск LAB или выберите более чистый участок кривой.")

    def walk(start_y: int, start_x: float, direction: int) -> list[tuple[int, float]]:
        pts: list[tuple[int, float]] = []
        prev_x = start_x
        prev_dx = 0.0
        gap = 0
        yy = start_y + direction
        while 0 <= yy < h:
            cands = row_candidates[yy]
            if cands.size:
                predicted = prev_x + prev_dx
                d = np.abs(cands - predicted)
                idx = int(np.argmin(d))
                allowed = cfg.max_jump_px * (1.0 + 0.22 * gap)
                if float(d[idx]) <= allowed:
                    x_new = float(cands[idx])
                    dx = x_new - prev_x
                    prev_dx = 0.68 * prev_dx + 0.32 * dx
                    prev_x = x_new
                    pts.append((yy, x_new))
                    gap = 0
                else:
                    gap += 1
            else:
                gap += 1

            if gap > cfg.max_gap_rows:
                recovered = False
                for jump in range(1, min(35, h)):
                    y2 = yy + direction * jump
                    if y2 < 0 or y2 >= h:
                        break
                    c2 = row_candidates[y2]
                    if not c2.size:
                        continue
                    predicted = prev_x + prev_dx * jump
                    d2 = np.abs(c2 - predicted)
                    idx2 = int(np.argmin(d2))
                    if float(d2[idx2]) <= cfg.max_jump_px * 2.2:
                        x_new = float(c2[idx2])
                        pts.append((y2, x_new))
                        prev_dx = (x_new - prev_x) / max(1, jump)
                        prev_x = x_new
                        yy = y2
                        gap = 0
                        recovered = True
                        break
                if not recovered:
                    break
            yy += direction
        return pts

    up = walk(seed_y, seed_x, -1)
    down = walk(seed_y, seed_x, 1)
    local = list(reversed(up)) + [(seed_y, seed_x)] + down

    by_y: dict[int, float] = {}
    for yy, xx in local:
        by_y[int(yy)] = float(xx)
    ys = np.asarray(sorted(by_y.keys()), dtype=int)
    xs = np.asarray([by_y[int(yy)] for yy in ys], dtype=float)

    if xs.size >= 7:
        k = int(max(3, cfg.smooth_window))
        if k % 2 == 0:
            k += 1
        k = min(k, xs.size if xs.size % 2 == 1 else xs.size - 1)
        if k >= 3:
            pad = k // 2
            padded = np.pad(xs, (pad, pad), mode="edge")
            windows = np.lib.stride_tricks.sliding_window_view(padded, k)
            xs_med = np.median(windows, axis=1).astype(np.float32)
            xs = cv2.GaussianBlur(xs_med.reshape(-1, 1), (1, 5), 0).reshape(-1)

    # Fill only short internal gaps (typically grid intersections / JPEG breaks).
    # Long uncertain gaps remain absent and are visible in quality diagnostics.
    if ys.size >= 2:
        filled_y: list[float] = [float(ys[0])]
        filled_x: list[float] = [float(xs[0])]
        max_fill = max(8, int(cfg.max_gap_rows * 3))
        for y_prev, x_prev, y_next, x_next in zip(ys[:-1], xs[:-1], ys[1:], xs[1:]):
            gap = int(y_next - y_prev)
            if 1 < gap <= max_fill:
                for step in range(1, gap):
                    t = step / gap
                    filled_y.append(float(y_prev + step))
                    filled_x.append(float(x_prev + t * (x_next - x_prev)))
            filled_y.append(float(y_next))
            filled_x.append(float(x_next))
        ys = np.asarray(filled_y, dtype=float)
        xs = np.asarray(filled_x, dtype=float)

    points = [(float(rx + xx), float(ry + yy)) for yy, xx in zip(ys, xs)]
    return points, mask


def curve_points_to_hv(
    points_xy: Iterable[tuple[float, float]], cfg: CurveConfig, depth: DepthCalibration,
    scale: AxisScale | None = None,
) -> list[tuple[float, float]]:
    pts = list(points_xy)
    if not pts:
        return []
    xs = np.asarray([p[0] for p in pts], dtype=float)
    ys = np.asarray([p[1] for p in pts], dtype=float)
    hs = np.asarray(pixel_y_to_depth(ys, depth), dtype=float)
    vals = np.asarray(pixel_x_to_value(xs, scale if scale is not None else cfg), dtype=float)
    order = np.argsort(hs)
    return [(float(hs[i]), float(vals[i])) for i in order]


def curve_quality(points_xy: Sequence[tuple[float, float]], cfg: CurveConfig) -> dict[str, float]:
    if not points_xy:
        return {"coverage_pct": 0.0, "p95_jump_px": 0.0, "max_gap_rows": 0.0, "score": 0.0}
    arr = np.asarray(points_xy, dtype=float)
    order = np.argsort(arr[:, 1])
    arr = arr[order]
    dy = np.diff(arr[:, 1])
    dx = np.abs(np.diff(arr[:, 0]))
    expected_rows = max(1.0, float(cfg.roi[3]))
    coverage = min(100.0, 100.0 * len(np.unique(np.round(arr[:, 1]).astype(int))) / expected_rows)
    p95 = float(np.percentile(dx, 95)) if dx.size else 0.0
    max_gap = float(np.max(dy) - 1.0) if dy.size else 0.0
    # Heuristic quality score intended for triage, not metrological uncertainty.
    jump_penalty = min(35.0, 35.0 * p95 / max(cfg.max_jump_px, 1.0))
    gap_penalty = min(25.0, 2.0 * max(0.0, max_gap))
    score = float(np.clip(coverage - jump_penalty - gap_penalty, 0.0, 100.0))
    return {
        "coverage_pct": round(coverage, 2),
        "p95_jump_px": round(p95, 2),
        "max_gap_rows": round(max_gap, 2),
        "score": round(score, 1),
    }


def edit_curve_point(
    points_xy: Sequence[tuple[float, float]], x: float, y: float, y_tolerance: float = 4.0
) -> list[tuple[float, float]]:
    """Move/insert the curve point nearest in Y to the clicked position."""
    pts = [tuple(map(float, p)) for p in points_xy]
    if not pts:
        return [(float(x), float(y))]
    arr = np.asarray(pts, dtype=float)
    idx = int(np.argmin(np.abs(arr[:, 1] - y)))
    if abs(arr[idx, 1] - y) <= y_tolerance:
        arr[idx] = (float(x), float(y))
    else:
        arr = np.vstack([arr, [float(x), float(y)]])
    arr = arr[np.argsort(arr[:, 1])]
    return [(float(px), float(py)) for px, py in arr]


def delete_curve_near(
    points_xy: Sequence[tuple[float, float]], x: float, y: float,
    radius_x: float = 18.0, radius_y: float = 7.0,
) -> list[tuple[float, float]]:
    pts = np.asarray(points_xy, dtype=float)
    if pts.size == 0:
        return []
    keep = ~((np.abs(pts[:, 0] - x) <= radius_x) & (np.abs(pts[:, 1] - y) <= radius_y))
    out = pts[keep]
    return [(float(px), float(py)) for px, py in out]


def clone_curve_config(cfg: CurveConfig, **kwargs) -> CurveConfig:
    return replace(cfg, **kwargs)

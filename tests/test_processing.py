import math

import cv2
import numpy as np

from digitizer.models import (
    AxisScale,
    CurveConfig,
    CurveData,
    DepthCalibration,
    ProjectData,
)

from digitizer.processing import (
    analyze_color_selection,
    build_color_mask,
    build_grid_mask,
    curve_quality,
    delete_curve_near,
    detect_vertical_track_lines,
    edit_curve_point,
    order_quad_points,
    palette_separation,
    perspective_warp,
    pixel_x_to_value,
    pixel_y_to_depth,
    sample_ink_color_at,
    trace_curve_from_seed,
)

from digitizer.project_io import (
    load_project,
    save_project,
)


def test_depth_mapping():
    cal = DepthCalibration(
        y1=100,
        h1=20,
        y2=1000,
        h2=200,
    )

    assert math.isclose(
        pixel_y_to_depth(
            550,
            cal,
        ),
        110.0,
    )


def test_linear_x_mapping():
    cfg = CurveConfig(
        name="t",
        x_min=250,
        x_max=550,
        roi=(
            100,
            0,
            600,
            1000,
        ),
    )

    assert math.isclose(
        pixel_x_to_value(
            400,
            cfg,
        ),
        400.0,
    )


def test_log_x_mapping():
    cfg = CurveConfig(
        name="A",
        x_min=1,
        x_max=1000,
        scale_type="log",
        roi=(
            0,
            0,
            300,
            1000,
        ),
    )

    assert math.isclose(
        pixel_x_to_value(
            100,
            cfg,
        ),
        10.0,
        rel_tol=1e-9,
    )

    assert math.isclose(
        pixel_x_to_value(
            200,
            cfg,
        ),
        100.0,
        rel_tol=1e-9,
    )


def test_independent_scale_mapping():
    scale = AxisScale(
        id="time",
        name="Time",
        unit="us",
        value_min=250,
        value_max=650,
        x1=100,
        x2=500,
        scale_type="linear",
        roi=(
            100,
            0,
            400,
            300,
        ),
    )

    assert math.isclose(
        pixel_x_to_value(
            300,
            scale,
        ),
        450.0,
    )


def test_perspective_warp_size_and_order():
    img = np.full(
        (
            200,
            300,
            3,
        ),
        255,
        np.uint8,
    )

    pts = [
        (20, 20),
        (280, 10),
        (290, 180),
        (10, 190),
    ]

    ordered = order_quad_points(
        [
            pts[2],
            pts[0],
            pts[3],
            pts[1],
        ]
    )

    assert ordered.shape == (
        4,
        2,
    )

    warped = perspective_warp(
        img,
        pts,
    )

    assert warped.shape[0] > 150
    assert warped.shape[1] > 240


def test_track_line_detection():
    img = np.full(
        (
            300,
            400,
            3,
        ),
        250,
        np.uint8,
    )

    for x in [
        50,
        180,
        330,
    ]:
        cv2.line(
            img,
            (x, 0),
            (x, 299),
            (20, 20, 20),
            3,
        )

    lines = detect_vertical_track_lines(
        img,
        min_separation_px=30,
        max_lines=8,
    )

    assert any(
        abs(x - 50) < 8
        for x in lines
    )

    assert any(
        abs(x - 180) < 8
        for x in lines
    )

    assert any(
        abs(x - 330) < 8
        for x in lines
    )


def test_grid_mask_finds_long_lines():
    img = np.full(
        (
            160,
            220,
            3,
        ),
        255,
        np.uint8,
    )

    for x in [
        30,
        90,
        160,
    ]:
        cv2.line(
            img,
            (x, 0),
            (x, 159),
            (100, 100, 100),
            1,
        )

    for y in [
        20,
        80,
        140,
    ]:
        cv2.line(
            img,
            (0, y),
            (219, y),
            (100, 100, 100),
            1,
        )

    mask = build_grid_mask(
        img
    )

    assert (
        mask[:, 30].mean()
        > 80
    )

    assert (
        mask[80, :].mean()
        > 80
    )


def test_trace_colored_curve_with_grid():
    img = np.full(
        (
            300,
            220,
            3,
        ),
        255,
        np.uint8,
    )

    for x in range(
        0,
        220,
        20,
    ):
        cv2.line(
            img,
            (x, 0),
            (x, 299),
            (205, 205, 205),
            1,
        )

    for y in range(
        0,
        300,
        20,
    ):
        cv2.line(
            img,
            (0, y),
            (219, y),
            (205, 205, 205),
            1,
        )

    curve_color = (
        180,
        60,
        40,
    )

    for y in range(
        15,
        285,
    ):
        x = int(
            105
            + 28
            * np.sin(
                y / 35
            )
        )

        img[
            y,
            max(
                0,
                x - 1,
            ):
            min(
                220,
                x + 2,
            ),
        ] = curve_color

    seed_y = 150

    seed_x = (
        105
        + 28
        * np.sin(
            seed_y / 35
        )
    )

    cfg = CurveConfig(
        name="t",
        roi=(
            0,
            0,
            220,
            300,
        ),
        color_bgr=curve_color,
        color_tolerance=25,
        seed_xy=(
            seed_x,
            seed_y,
        ),
        max_jump_px=12,
        max_gap_rows=8,
        remove_grid=True,
    )

    points, _ = trace_curve_from_seed(
        img,
        cfg,
    )

    assert len(points) > 240

    arr = np.asarray(
        points
    )

    expected = (
        105
        + 28
        * np.sin(
            arr[:, 1]
            / 35
        )
    )

    assert (
        float(
            np.mean(
                np.abs(
                    arr[:, 0]
                    - expected
                )
            )
        )
        < 2.0
    )


def test_manual_edit_helpers_and_quality():
    pts = [
        (
            50.0,
            float(y),
        )
        for y in range(
            100
        )
    ]

    moved = edit_curve_point(
        pts,
        80,
        50,
    )

    near = min(
        moved,
        key=lambda p: abs(
            p[1] - 50
        ),
    )

    assert near[0] == 80

    reduced = delete_curve_near(
        moved,
        80,
        50,
        radius_x=5,
        radius_y=2,
    )

    assert (
        len(reduced)
        < len(moved)
    )

    cfg = CurveConfig(
        name="x",
        roi=(
            0,
            0,
            100,
            100,
        ),
        max_jump_px=20,
    )

    quality = curve_quality(
        pts,
        cfg,
    )

    assert (
        quality[
            "coverage_pct"
        ]
        >= 99
    )

    assert (
        quality[
            "score"
        ]
        > 90
    )


def test_multiple_color_samples_build_one_curve_mask():
    img = np.full(
        (
            80,
            120,
            3,
        ),
        255,
        np.uint8,
    )

    c1 = (
        30,
        150,
        60,
    )

    c2 = (
        60,
        185,
        90,
    )

    img[
        10:40,
        30:33,
    ] = c1

    img[
        40:70,
        31:34,
    ] = c2

    cfg = CurveConfig(
        name="multi",
        roi=(
            0,
            0,
            120,
            80,
        ),
        color_bgr=c1,
        color_samples_bgr=[
            c1,
            c2,
        ],
        color_tolerance=18,
        remove_grid=False,
    )

    mask, _ = build_color_mask(
        img,
        cfg,
    )

    assert (
        mask[
            20,
            31,
        ]
        > 0
    )

    assert (
        mask[
            55,
            32,
        ]
        > 0
    )


def test_near_colours_are_assigned_exclusively_to_their_curves():
    img = np.full(
        (
            185,
            120,
            3,
        ),
        255,
        np.uint8,
    )

    greenish = (
        118,
        145,
        170,
    )

    slightly_different = (
        123,
        153,
        167,
    )

    cv2.line(
        img,
        (35, 7),
        (35, 177),
        greenish,
        2,
    )

    cv2.line(
        img,
        (79, 7),
        (79, 177),
        slightly_different,
        2,
    )

    a = CurveConfig(
        name="A",
        roi=(
            0,
            0,
            120,
            185,
        ),
        color_bgr=greenish,
        seed_xy=(
            35,
            90,
        ),
        color_tolerance=35,
        precise_color=True,
        competitor_margin=5,
        remove_grid=False,
    )

    b = CurveConfig(
        name="B",
        roi=(
            0,
            0,
            120,
            185,
        ),
        color_bgr=slightly_different,
        seed_xy=(
            79,
            90,
        ),
        color_tolerance=35,
        precise_color=True,
        competitor_margin=5,
        remove_grid=False,
    )

    naive, _, _ = analyze_color_selection(
        img,
        a,
    )

    # Без конкурирующей палитры
    # соседняя линия тоже может попадать в маску.
    assert (
        naive[
            90,
            79,
        ]
        != 0
    )

    mask_a, _, _ = analyze_color_selection(
        img,
        a,
        [b],
    )

    mask_b, _, _ = analyze_color_selection(
        img,
        b,
        [a],
    )

    assert (
        mask_a[
            90,
            35,
        ]
        > 0
    )

    assert (
        mask_a[
            90,
            79,
        ]
        == 0
    )

    assert (
        mask_b[
            90,
            79,
        ]
        > 0
    )

    assert (
        mask_b[
            90,
            35,
        ]
        == 0
    )

    pts_a, _ = trace_curve_from_seed(
        img,
        a,
        [b],
    )

    pts_b, _ = trace_curve_from_seed(
        img,
        b,
        [a],
    )

    assert len(
        pts_a
    ) > 150

    assert len(
        pts_b
    ) > 150

    arr_a = np.asarray(
        pts_a
    )

    arr_b = np.asarray(
        pts_b
    )

    assert (
        np.percentile(
            np.abs(
                arr_a[:, 0]
                - 35
            ),
            90,
        )
        < 2
    )

    assert (
        np.percentile(
            np.abs(
                arr_b[:, 0]
                - 79
            ),
            90,
        )
        < 2
    )


def test_ambiguous_near_colours_are_flagged_instead_of_guessed():
    c1 = (
        118,
        145,
        170,
    )

    c2 = (
        123,
        153,
        167,
    )

    mid = tuple(
        int(
            round(
                (
                    v1
                    + v2
                )
                / 2
            )
        )
        for v1, v2
        in zip(
            c1,
            c2,
        )
    )

    img = np.full(
        (
            70,
            75,
            3,
        ),
        255,
        np.uint8,
    )

    img[
        25:45,
        25:45,
    ] = mid

    a = CurveConfig(
        name="A",
        roi=(
            0,
            0,
            75,
            70,
        ),
        color_bgr=c1,
        color_tolerance=35,
        remove_grid=False,
        competitor_margin=5,
    )

    b = CurveConfig(
        name="B",
        roi=(
            0,
            0,
            75,
            70,
        ),
        color_bgr=c2,
    )

    mask, _, uncertain = (
        analyze_color_selection(
            img,
            a,
            [b],
        )
    )

    assert (
        uncertain[
            34,
            33,
        ]
        == 255
    )

    assert (
        mask[
            34,
            33,
        ]
        == 0
    )


def test_competitor_in_another_track_does_not_remove_current_curve():
    img = np.full(
        (
            80,
            160,
            3,
        ),
        255,
        np.uint8,
    )

    sample = (
        50,
        110,
        150,
    )

    cv2.line(
        img,
        (22, 4),
        (22, 75),
        sample,
        2,
    )

    a = CurveConfig(
        name="A",
        roi=(
            0,
            0,
            75,
            80,
        ),
        color_bgr=sample,
        remove_grid=False,
    )

    b = CurveConfig(
        name="B",
        roi=(
            80,
            0,
            80,
            80,
        ),
        color_bgr=sample,
    )

    mask, _, ambiguous = (
        analyze_color_selection(
            img,
            a,
            [b],
        )
    )

    assert (
        mask[
            35,
            22,
        ]
        != 0
    )

    assert (
        ambiguous.sum()
        == 0
    )


def test_pipette_extracts_thin_ink_over_white_paper():
    img = np.full(
        (
            50,
            50,
            3,
        ),
        250,
        np.uint8,
    )

    ink = (
        65,
        120,
        182,
    )

    img[
        15:35,
        23:25,
    ] = ink

    sampled = sample_ink_color_at(
        img,
        24,
        25,
    )

    assert (
        max(
            abs(
                int(v)
                - int(ref)
            )
            for v, ref
            in zip(
                sampled,
                ink,
            )
        )
        <= 1
    )

    assert (
        palette_separation(
            [ink],
            [ink],
        )
        == 0
    )


def test_project_roundtrip_saves_colour_discrimination_controls(
    tmp_path,
):
    cfg = CurveConfig(
        name="T1",
        roi=(
            0,
            0,
            100,
            100,
        ),
        scale_id="time",
        color_tolerance=19,
        competitor_margin=9.5,
        hue_tolerance=8,
        precise_color=True,
    )

    project = ProjectData(
        curves=[
            CurveData(
                config=cfg
            )
        ]
    )

    path = (
        tmp_path
        / "test.json"
    )

    save_project(
        path,
        project,
    )

    loaded = load_project(
        path
    )

    loaded_cfg = (
        loaded
        .curves[0]
        .config
    )

    assert (
        loaded_cfg.competitor_margin
        == 9.5
    )

    assert (
        loaded_cfg.hue_tolerance
        == 8
    )

    assert (
        loaded_cfg.precise_color
        is True
    )


def test_project_roundtrip_with_russian_filename(
    tmp_path,
):
    """
    Проверяем, что JSON-проект нормально работает
    с кириллицей в имени файла.
    """

    path = (
        tmp_path
        / "Проект скважины №12.json"
    )

    project = ProjectData(
        image_path=(
            "Скважина №12.png"
        ),
        source_image_path=(
            "Исходное фото №12.jpg"
        ),
    )

    save_project(
        path,
        project,
    )

    assert path.exists()

    loaded = load_project(
        path
    )

    assert (
        "Скважина №12.png"
        in loaded.image_path
    )

    assert (
        "Исходное фото №12.jpg"
        in loaded.source_image_path
    )
# -*- coding: utf-8 -*-
"""把 Logo_src.png 处理成 App 图标（圆角矩形，沿用原图卡片的弧度）。

用法：  python images/make_icon.py

源图：1024²，最外层白底 + 一个浅色圆角卡片（卡片里有蓝色水杯和橙色伸展人形）。
产物：
    images/logo.png   1024×1024 RGBA，透明背景 + 圆角矩形
    images/logo.ico   9 个尺寸（16~256），给 exe / 托盘 / 浮层 / 标题徽标用

处理思路：
    1. 沿中线扫描找出浅色卡片的边界（白底与卡片之间有明确台阶，比全局阈值稳）；
    2. 量出卡片圆角半径，按同比例还原——保留原图"自然的弧形弧度"；
    3. 以卡片中心取正方形裁切，LANCZOS 缩到 1024（内容不缩放，保持原始构图）；
    4. 4 倍超采样的圆角矩形遮罩，边缘抗锯齿；
    5. 由 1024 母版生成多尺寸 ICO。

为什么不裁成圆形：原图的构图是方形的（水杯在左下、人形在右侧伸展），
圆切会削掉四个角，视觉上像被硬生生咬掉一块，反而不如原来的圆角矩形自然。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
SRC = HERE / "Logo_src.png"
OUT_PNG = HERE / "logo.png"
OUT_ICO = HERE / "logo.ico"

SIZE = 1024          # PNG 母版边长
SS = 4               # 遮罩超采样倍数
INSET = 1.0          # 遮罩内缩像素，去掉边缘残留的白边
EDGE_PAD = 6         # 卡片外扩像素（柔和边缘的实心部分）
ICO_SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]


def card_rect(rgb: np.ndarray) -> tuple[int, int, int, int]:
    """定位浅色卡片。

    不能按亮度找：卡片面 ~248、外层白底 ~254、卡片外还有一圈 ~230 的柔和投影，
    三者亮度区间是重叠的，阈值法会把投影一起框进来（导致图标边缘出现双层轮廓）。
    卡片面是**偏蓝**的（B−R ≈ 6~8），白底和投影都是中性灰（B−R ≈ 0），
    用色差判别干净利落。
    """
    blue = rgb[:, :, 2].astype(np.int16) - rgb[:, :, 0].astype(np.int16)
    mask = blue > 2
    ys, xs = np.where(mask)
    if len(xs) == 0:
        raise RuntimeError("没找到浅色卡片，色差阈值可能需要调整")
    x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
    # 往外放几个像素，把柔和边缘的实心部分包进来
    h, w = rgb.shape[:2]
    return (max(0, x0 - EDGE_PAD), max(0, y0 - EDGE_PAD),
            min(w - 1, x1 + EDGE_PAD), min(h - 1, y1 + EDGE_PAD))


def corner_radius(rgb: np.ndarray, rect: tuple[int, int, int, int]) -> float:
    """量卡片圆角半径：圆角矩形顶行只从 left+r 处开始，故首行偏移即半径。"""
    blue = rgb[:, :, 2].astype(np.int16) - rgb[:, :, 0].astype(np.int16)
    mask = blue > 2
    x0, y0, x1, _ = rect
    offs = []
    for dy in range(EDGE_PAD, EDGE_PAD + 4):
        idx = np.where(mask[y0 + dy, x0:x1 + 1])[0]
        if len(idx):
            offs.append(int(idx[0]))
    return float(np.median(offs)) if offs else 0.0


def round_rect_mask(size: int, radius: float) -> Image.Image:
    """4 倍超采样的圆角矩形 alpha 遮罩。

    缩小用 BOX（面积平均）而不是 LANCZOS：后者在硬边会产生振铃，
    四条边的中点会残留一圈 ~7% 的杂边。
    """
    big = Image.new("L", (size * SS, size * SS), 0)
    inset = INSET * SS
    ImageDraw.Draw(big).rounded_rectangle(
        [inset, inset, size * SS - 1 - inset, size * SS - 1 - inset],
        radius=radius * SS, fill=255)
    return big.resize((size, size), Image.BOX)


def main() -> None:
    src = Image.open(SRC).convert("RGB")
    rgb = np.asarray(src)

    card = card_rect(rgb)
    radius = corner_radius(rgb, card)
    cw, ch = card[2] - card[0] + 1, card[3] - card[1] + 1
    print(f"原图 {src.width}x{src.height}")
    print(f"卡片 {card} -> {cw}x{ch}，圆角半径 {radius:.0f}")

    # 裁在卡片**内部**：只要裁切框的四角落在卡片的平面上，就不会露出卡片自己的
    # 那条边和外面的投影。外扩补边会把卡片整体内移、圆角弧心错位，结果就是
    # 一条卡片边 + 一条遮罩边，看起来像双层轮廓。
    side = int(round(min(cw, ch) - 0.586 * radius))
    cx, cy = (card[0] + card[2]) / 2.0, (card[1] + card[3]) / 2.0
    box = (round(cx - side / 2), round(cy - side / 2),
           round(cx + side / 2), round(cy + side / 2))
    master = src.crop(box).resize((SIZE, SIZE), Image.LANCZOS)
    print(f"卡片裁切 {cw}x{ch}，取内部 {side}² 方框 {box}，缩放 {SIZE / side:.3f}")

    # 圆角比例沿用卡片自己的弧度（radius / 卡片短边）
    r_out = radius / min(cw, ch) * SIZE
    alpha = round_rect_mask(SIZE, r_out)
    logo = master.convert("RGBA")
    logo.putalpha(alpha)
    logo.save(OUT_PNG, optimize=True)
    logo.save(OUT_ICO, sizes=[(s, s) for s in ICO_SIZES])
    print(f"圆角半径换算到 {SIZE}² 后为 {r_out:.1f}")

    # 自检：圆角矩形——中心与四边中点为不透明，四角为透明
    a = np.asarray(logo)[:, :, 3]
    assert a[SIZE // 2, SIZE // 2] == 255, "中心应完全不透明"
    assert a[0, 0] == 0 and a[-1, -1] == 0, "四角应完全透明"
    assert a[SIZE // 2, 3] == 255, f"左边中点应不透明（实测 {a[SIZE // 2, 3]}）"
    assert a[SIZE // 2, SIZE - 4] == 255, "右边中点应不透明"
    assert a[3, SIZE // 2] == 255, "上边中点应不透明"
    print(f"已写出 {OUT_PNG.name} 与 {OUT_ICO.name} {ICO_SIZES}")


if __name__ == "__main__":
    main()

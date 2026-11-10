"""把「久坐」线稿设计图处理成透明底、粗细合适的小图标。

输入  images/sit_src.png   白底线稿（784x1168，线宽约 15px）
输出  images/sit_icon.png  256x256 RGBA，内容居中、四周留 4% 安全边

处理链：
1. 用蓝色通道反推 alpha（白底 → 0，纯色线条 → 1），保留抗锯齿过渡
2. 线条统一改成本 App 的橙色 ACCENT
3. 膨胀（MaxFilter）把线宽从 15px 加到 ~25px——原图线宽只占内容高度 2.7%，
   直接缩到 20px 显示会变成 0.5px 的灰雾，必须加粗
4. 裁到内容外接框 → 居中放到正方形画布 → LANCZOS 缩到 256
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
SRC = HERE / "sit_src.png"
OUT = HERE / "sit_icon.png"

SIZE = 256          # 输出边长
MARGIN = 0.04       # 四周留白比例
DILATE = 17         # MaxFilter 窗口（奇数），17 → 每侧 +8px，线宽 15→31
ACCENT = (0xFF, 0x7A, 0x00)   # #FF7A00，与 ACCENT_SED 一致


def main() -> None:
    im = Image.open(SRC).convert("RGB")
    a = np.asarray(im).astype(np.float32)

    # 1. alpha：白底 (255,255,255) → 0；线条主色 (246,127,45) → 1。
    #    蓝色通道反差最大（255→45），抗锯齿像素按比例落在 0~1
    alpha = (255.0 - a[:, :, 2]) / (255.0 - 45.0)
    alpha = np.clip(alpha, 0.0, 1.0)
    # 白底不是纯 255（有 253 之类的噪点），先抹掉，否则外接框会识别成整张图
    alpha[alpha < 0.06] = 0.0

    # 2. 统一染色（保留 alpha 做边缘过渡）
    rgba = np.zeros((a.shape[0], a.shape[1], 4), dtype=np.uint8)
    rgba[:, :, 0], rgba[:, :, 1], rgba[:, :, 2] = ACCENT
    rgba[:, :, 3] = (alpha * 255).round().astype(np.uint8)
    img = Image.fromarray(rgba, "RGBA")

    # 3. 加粗线条
    ch_a = img.getchannel("A").filter(ImageFilter.MaxFilter(DILATE))
    img.putalpha(ch_a)

    # 4. 裁内容 -> 正方形画布 -> 缩放
    box = ch_a.getbbox()
    if box is None:
        raise SystemExit("没检测到内容，检查源图")
    img = img.crop(box)
    w, h = img.size
    side = int(max(w, h) * (1 + MARGIN * 2))
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    # 注意：不能写 paste(img, pos, img)——带 mask 的 paste 是 alpha 合成，
    # 会把 RGB 按 alpha 预乘变暗（橙色会变成褐色）。这里整块直接拷贝
    canvas.paste(img, ((side - w) // 2, (side - h) // 2))
    out = canvas.resize((SIZE, SIZE), Image.LANCZOS)
    out.save(OUT)

    # 自检
    arr = np.asarray(out)
    print(f"源图 {im.size}  内容框 {box}  {w}x{h}")
    print(f"输出 {OUT.name} {out.size}  {OUT.stat().st_size / 1024:.1f} KB")
    print("四角 alpha:", [int(arr[y, x, 3]) for y, x in
                          ((0, 0), (0, SIZE - 1), (SIZE - 1, 0), (SIZE - 1, SIZE - 1))])
    print("中心 alpha:", int(arr[SIZE // 2, SIZE // 2, 3]))

    # 缩到 26px 看线宽还剩多少
    small = out.resize((26, 26), Image.LANCZOS)
    s = np.asarray(small)[:, :, 3]
    solid = (s > 128).sum()
    print(f"26px 下不透明像素 {solid} 个，平均 alpha {s.mean():.0f}")


if __name__ == "__main__":
    main()

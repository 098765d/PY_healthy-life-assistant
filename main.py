# -*- coding: utf-8 -*-
"""久坐 · 喝水提醒 —— 极简久坐 / 喝水提醒

单文件 PyQt5 应用，仅依赖 PyQt5。

运行：  python main.py
打包：  pyinstaller --noconfirm --windowed --icon images/logo.ico main.py
"""

from __future__ import annotations

import csv
import json
import math
import os
import sys
import time
import webbrowser
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional

from PyQt5.QtCore import (
    QEasingCurve, QEvent, QPointF, QPropertyAnimation, QRectF, QSize, Qt, QTimer,
    QVariantAnimation,
)
from PyQt5.QtGui import (
    QBrush, QColor, QCursor, QFont, QFontMetrics, QIcon, QLinearGradient,
    QPainter, QPainterPath, QPen, QPixmap, QPolygonF, QRadialGradient, QRegion,
)
from PyQt5.QtWidgets import (
    QApplication, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel,
    QLayout, QMenu, QPushButton, QSizePolicy, QSpinBox, QSystemTrayIcon,
    QVBoxLayout, QWidget,
)

# ------------------------------- 常量 ------------------------------- #

APP_NAME = "久坐 · 喝水提醒"
APP_DIR = Path(os.getenv("APPDATA", Path.home())) / "HealthyLifeAssistant"
SETTINGS_PATH = APP_DIR / "settings.json"
LOG_PATH = APP_DIR / "log.csv"
REPORT_DIR = APP_DIR / "报告"

TICK_MS = 500            # 界面刷新间隔
TOAST_MS = 5000          # 提醒停留时长（无操作自动关闭）
TOAST_GAP_MS = 6200      # 两条提醒同时到期时的错开间隔

WIN_W = 368              # 面板宽度
SHADOW = 18              # 面板四周留出的投影空间
RADIUS = 26              # 面板圆角
PILL_H = 52              # 主按钮胶囊高度
PILL_SHADOW = 6          # 主按钮投影预留高度

ACCENT_WATER = "#0A84FF"   # 主蓝（新稿的圆环 / 按钮主色）
ACCENT_SED = "#FF7A00"     # 活力橙
TINT_WATER = "#EAF3FE"     # 喝水分组卡底色
TINT_SED = "#FDF2E6"       # 久坐分组卡底色
INK = "#0B1B2B"
SUB = "#8A94A6"
DIM_COLOR = "#B9C2D0"

DEFAULTS = {"sed_min": 60, "water_min": 60, "sip_ml": 250,
            "goal_ml": 2000, "goal_stands": 8}

QSS = """
QWidget {
    font-family: "Segoe UI", "SF Pro Display", "Microsoft YaHei UI",
                 "PingFang SC", sans-serif;
    font-size: 15px;
    color: #1E293B;
    background: transparent;
}
#H1 { font-size: 27px; font-weight: 700; color: #0B1B2B; }
#Sub { font-size: 12px; color: #8A94A6; }
#GroupTitle { font-size: 16px; font-weight: 600; color: #16233A; }
#GroupSub { font-size: 11px; color: #8A94A6; }
#RowLabel { font-size: 14px; color: #3E4A5E; }
#Chevron { font-size: 18px; color: #AAB6C6; }
#Panel {
    background: #FFFFFF;
    border: 0;
    border-radius: 12px;
}
#RowTitle { font-size: 15px; font-weight: 600; color: #1E293B; }
#Time {
    /* 只用 Segoe UI 400/600：500 会命中 Medium 字面，数字变成比例宽，倒计时会左右抖 */
    font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
    font-size: 20px; font-weight: 400; color: #1E293B;
}
#Card {
    /* 面板本身已是近白，纯白卡片会看不出边界，这里用极淡蓝灰托出层次 */
    background: #F4F8FD;
    border: 0;
    border-radius: 18px;
}
#Ghost {
    background: rgba(10, 132, 255, 0.10); color: #0A84FF;
    border: 0; border-radius: 17px; font-size: 13px; padding: 8px 0;
}
#Ghost:hover { background: rgba(10, 132, 255, 0.18); }
#Ghost:pressed { background: rgba(10, 132, 255, 0.26); }
#Ghost:disabled { background: rgba(122, 135, 155, 0.10); color: #AAB4C4; }
QSpinBox {
    background: transparent; border: 0;
    font-size: 14px; font-weight: 600; padding: 0;
}
QSpinBox:focus { color: #0A84FF; }
QMenu { background: #FFFFFF; border: 1px solid #E5E5EA; border-radius: 10px; padding: 4px; }
QMenu::item { padding: 7px 22px; border-radius: 7px; }
QMenu::item:selected { background: #F2F6FC; }
"""


def resource_path(rel: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


# ------------------------------- 配置 ------------------------------- #

@dataclass
class Settings:
    """持久化配置 + 当日统计（按自然日自动归零）。"""

    sed_min: int = DEFAULTS["sed_min"]
    water_min: int = DEFAULTS["water_min"]
    sip_ml: int = DEFAULTS["sip_ml"]
    goal_ml: int = DEFAULTS["goal_ml"]
    goal_stands: int = DEFAULTS["goal_stands"]
    day: str = ""
    today_ml: int = 0
    today_sips: int = 0
    today_stands: int = 0

    @classmethod
    def load(cls) -> "Settings":
        s = cls()
        try:
            raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raw = {}
        for key in ("sed_min", "water_min", "sip_ml", "goal_ml", "goal_stands",
                    "today_ml", "today_sips", "today_stands"):
            if isinstance(raw.get(key), int):
                setattr(s, key, raw[key])
        if isinstance(raw.get("day"), str):
            s.day = raw["day"]
        s.clamp()
        s.roll_day()
        return s

    def clamp(self) -> None:
        self.sed_min = min(600, max(1, self.sed_min))
        self.water_min = min(600, max(1, self.water_min))
        self.sip_ml = min(2000, max(50, self.sip_ml))
        self.goal_ml = min(5000, max(200, self.goal_ml))
        self.goal_stands = min(50, max(1, self.goal_stands))

    def roll_day(self) -> bool:
        today = date.today().isoformat()
        if self.day == today:
            return False
        self.day = today
        self.today_ml = self.today_sips = self.today_stands = 0
        return True

    def save(self) -> None:
        try:
            APP_DIR.mkdir(parents=True, exist_ok=True)
            SETTINGS_PATH.write_text(
                json.dumps(self.__dict__, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass


def log_event(event: str) -> None:
    """追加一条事件到 CSV：date,time,event"""
    try:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        new = not LOG_PATH.exists()
        with LOG_PATH.open("a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["date", "time", "event"])
            w.writerow([date.today().isoformat(), datetime.now().strftime("%H:%M:%S"), event])
    except OSError:
        pass


# ---------------------------- 报告模板 ---------------------------- #

REPORT_CSS = """
:root {
  --bg: #F5F5F7; --card: #FFFFFF; --ink: #1D1D1F; --sub: #6E6E73;
  --line: #E8E8ED; --blue: #0A84FF; --amber: #FF9F0A;
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 48px 20px 64px; background: var(--bg); color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
               "Microsoft YaHei UI", "PingFang SC", sans-serif;
  -webkit-font-smoothing: antialiased;
}
.wrap { max-width: 660px; margin: 0 auto; }
h1 { font-size: 21px; font-weight: 600; margin: 0 0 6px; }
.meta { color: var(--sub); font-size: 13px; margin-bottom: 26px; }
.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.card {
  background: var(--card); border: 1px solid var(--line);
  border-radius: 14px; padding: 16px 18px;
}
.k { color: var(--sub); font-size: 12px; margin-bottom: 8px; }
.v { font-size: 25px; font-weight: 600; font-variant-numeric: tabular-nums; }
.v small { font-size: 12px; font-weight: 400; color: var(--sub); margin: 0 2px; }
h2 { font-size: 13px; font-weight: 600; color: var(--sub); margin: 26px 0 10px; }
.panel {
  background: var(--card); border: 1px solid var(--line);
  border-radius: 14px; padding: 4px 18px;
}
table { width: 100%; border-collapse: collapse; font-size: 14px; }
td { padding: 10px 0; border-bottom: 1px solid var(--line); }
tr:last-child td { border-bottom: 0; }
td.t { color: var(--sub); width: 88px; font-variant-numeric: tabular-nums; }
td.n { text-align: right; color: var(--sub); font-size: 13px; }
td.val { text-align: right; font-variant-numeric: tabular-nums; }
.dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%;
       margin-right: 9px; vertical-align: 1px; }
.blue { background: var(--blue); }
.amber { background: var(--amber); }
.foot { margin-top: 26px; color: var(--sub); font-size: 12px; }
"""


def fmt_hm(sec: float) -> str:
    sec = int(max(0, sec))
    h, m = divmod(sec // 60, 60)
    return f"{h} 小时 {m} 分" if h else f"{m} 分"


def fmt_hm_big(sec: float) -> str:
    sec = int(max(0, sec))
    h, m = divmod(sec // 60, 60)
    return f"{h}<small>小时</small> {m}<small>分</small>" if h else f"{m}<small>分</small>"


# ---------------------------- 提醒浮层 ---------------------------- #

class Toast(QWidget):
    """半透明置顶提醒：不抢焦点、5 秒自动消失、全局唯一（新提醒覆盖旧提醒）。"""

    def __init__(self):
        super().__init__(
            None,
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedWidth(316)
        self.setCursor(Qt.PointingHandCursor)

        self._on_action: Optional[Callable[[], None]] = None
        self._anim: Optional[QPropertyAnimation] = None
        self._deadline = 0.0
        self._duration = TOAST_MS

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(12)

        self.icon = QLabel()
        self.icon.setFixedSize(26, 26)
        self.icon.setPixmap(QIcon(resource_path("images/logo.ico")).pixmap(QSize(26, 26)))
        self.icon.setStyleSheet("background: transparent;")
        root.addWidget(self.icon)

        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        self.title = QLabel()
        self.title.setStyleSheet(
            "color: #FFFFFF; font-size: 14px; font-weight: 600; background: transparent;")
        self.sub = QLabel()
        self.sub.setStyleSheet(
            "color: rgba(255,255,255,150); font-size: 12px; background: transparent;")
        text_col.addWidget(self.title)
        text_col.addWidget(self.sub)
        root.addLayout(text_col, 1)

        self.btn = QPushButton()
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,38); color: #FFFFFF;"
            " border: 0; border-radius: 10px; padding: 7px 12px; font-size: 12px; }"
            "QPushButton:hover { background: rgba(255,255,255,70); }")
        self.btn.clicked.connect(self._run_action)
        root.addWidget(self.btn, 0, Qt.AlignVCenter)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.dismiss)

    # ---- 外观 ----
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(255, 255, 255, 26), 1))
        p.setBrush(QColor(16, 26, 42, 232))          # 半透明深色卡片
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 18, 18)

    # ---- 展示 ----
    def notify(self, title: str, sub: str,
               action: str = "", on_action: Optional[Callable[[], None]] = None,
               duration_ms: int = TOAST_MS) -> None:
        self.title.setText(title)
        self.sub.setText(sub)
        # 没有动作时不显示按钮：记录确认 / 暂停提示这类只是"告知"，不该长按钮
        self.btn.setVisible(bool(action))
        self.btn.setText(action)
        self._on_action = on_action
        self._duration = duration_ms
        self._present()

    def _present(self) -> None:
        self.adjustSize()
        area = self._target_area()
        self.move(area.right() - self.width() - 24,
                  area.bottom() - self.height() - 24)

        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self._keep_on_top()
        self._fade(0.92, 160)

        self._deadline = time.monotonic() + self._duration / 1000
        self._timer.start(self._duration)

    def _target_area(self):
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        return screen.availableGeometry()

    def _keep_on_top(self) -> None:
        """在 Windows 上用 SetWindowPos 强制置顶，且不激活窗口。"""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            HWND_TOPMOST, SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = -1, 0x1, 0x2, 0x10
            ctypes.windll.user32.SetWindowPos(
                int(self.winId()), HWND_TOPMOST, 0, 0, 0, 0,
                SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)
        except Exception:
            pass

    def _fade(self, target: float, ms: int, done: Optional[Callable] = None) -> None:
        if self._anim is not None:
            self._anim.stop()
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(ms)
        anim.setStartValue(self.windowOpacity())
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        if done is not None:
            anim.finished.connect(done)
        anim.start()
        self._anim = anim

    # ---- 关闭 ----
    def dismiss(self) -> None:
        if not self.isVisible():
            return
        self._timer.stop()
        self._fade(0.0, 200, self.hide)

    def _run_action(self) -> None:
        cb, self._on_action = self._on_action, None
        self.dismiss()
        if cb is not None:
            cb()

    # ---- 交互：悬停时暂停倒计时，点击整卡片即执行动作 ----
    def enterEvent(self, e):
        self._timer.stop()
        super().enterEvent(e)

    def leaveEvent(self, e):
        if self.isVisible():
            remain = max(0.8, self._deadline - time.monotonic())
            self._timer.start(int(remain * 1000))
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._run_action()
        super().mousePressEvent(e)


# ---------------------------- 自绘组件 ---------------------------- #

def rounded(rect: QRectF, r: float) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(rect, r, r)
    return path


def ui_font(size: int, bold: bool = False) -> QFont:
    f = QFont("Microsoft YaHei UI")
    f.setPixelSize(size)
    if bold:
        f.setWeight(QFont.DemiBold)
    return f


def draw_glyph(p: QPainter, r: QRectF, kind: str, color: QColor) -> None:
    """在 r 内绘制线性小图标：水滴（实心）/ 水杯（描边）/ 人形（实心）。"""
    p.save()
    p.setRenderHint(QPainter.Antialiasing, True)
    # 线宽随尺寸缩放：13px 的小图标用 1.7 会糊成一团，26px 的大图标又显得单薄
    pen = QPen(color, max(1.15, min(r.width(), r.height()) * 0.085))
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    l, t, w, h = r.left(), r.top(), r.width(), r.height()

    if kind == "drop":
        path = QPainterPath()
        path.moveTo(l + w / 2, t)
        path.cubicTo(l + w * 0.94, t + h * 0.40, l + w * 0.90, t + h,
                     l + w / 2, t + h)
        path.cubicTo(l + w * 0.10, t + h, l + w * 0.06, t + h * 0.40,
                     l + w / 2, t)
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawPath(path)
    elif kind == "glass":
        path = QPainterPath()
        path.moveTo(l + w * 0.18, t + h * 0.06)
        path.lineTo(l + w * 0.82, t + h * 0.06)
        path.lineTo(l + w * 0.71, t + h * 0.94)
        path.lineTo(l + w * 0.29, t + h * 0.94)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(QPointF(l + w * 0.30, t + h * 0.56),
                   QPointF(l + w * 0.70, t + h * 0.56))
    elif kind == "clock":
        # 细描边时钟：外圈 + 时针 + 分针，13px 下仍可辨认
        c = QPointF(l + w / 2, t + h / 2)
        rr = min(w, h) * 0.44
        p.drawEllipse(c, rr, rr)
        p.drawLine(c, QPointF(c.x(), c.y() - rr * 0.58))
        p.drawLine(c, QPointF(c.x() + rr * 0.46, c.y() + rr * 0.20))
    elif kind == "target":
        # 同心圆靶心：外圈 + 内圈 + 圆心点
        c = QPointF(l + w / 2, t + h / 2)
        rr = min(w, h) * 0.44
        p.drawEllipse(c, rr, rr)
        p.drawEllipse(c, rr * 0.52, rr * 0.52)
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawEllipse(c, rr * 0.17, rr * 0.17)
    else:  # person：起身 / 久坐
        # 实心圆角人形：头 + 肩臂横条 + 躯干 + 双腿。同色图元相互融合，
        # 16px 下仍能读出"人"；比早期 1.7px 细线火柴人有分量，
        # 也和左边的实心水滴同属"实心"语汇，不再是描线草稿感。
        # 手臂用**水平**横条而非斜线：斜臂在 16px 只剩两个小凸起，会糊成星形
        p.setPen(Qt.NoPen)
        p.setBrush(color)

        head_r = w * 0.13
        p.drawEllipse(QPointF(l + w * 0.5, t + h * 0.16), head_r, head_r)

        arms = QPainterPath()                     # 肩臂：一条圆角横条
        arms.addRoundedRect(
            QRectF(l + w * 0.175, t + h * 0.345, w * 0.65, h * 0.13),
            h * 0.065, h * 0.065)
        p.drawPath(arms)

        torso = QPainterPath()                    # 躯干：竖胶囊，上端与肩臂融合
        torso.addRoundedRect(
            QRectF(l + w * 0.375, t + h * 0.345, w * 0.25, h * 0.40),
            w * 0.125, w * 0.125)
        p.drawPath(torso)

        leg = QPen(color, w * 0.135)              # 双腿：圆头粗线，略向外分
        leg.setCapStyle(Qt.RoundCap)
        p.setPen(leg)
        p.drawLine(QPointF(l + w * 0.44, t + h * 0.67),
                   QPointF(l + w * 0.295, t + h * 0.925))
        p.drawLine(QPointF(l + w * 0.56, t + h * 0.67),
                   QPointF(l + w * 0.705, t + h * 0.925))
    p.restore()


class IconTile(QWidget):
    """圆角图标底托 + 单色图标（自绘 glyph 或位图线稿）。"""

    # 「久坐」用的是位图线稿（images/sit_icon.png），
    # 线稿细节多，塞进 16px 会糊，所以内绘尺寸按底托的 0.62 倍给
    IMAGE_KINDS = {"sit"}
    # 位图线稿本身就是圆形构图，底托用正圆更贴合；其余仍用圆角方
    CIRCLE_KINDS = {"sit"}

    def __init__(self, kind: str, accent: str, size: int = 30):
        super().__init__()
        self.kind = kind
        self.accent = QColor(accent)
        self.setFixedSize(size, size)
        self._inner = max(1, int(round(size * 0.62)))   # 内绘尺寸随底托缩放
        self._src = None            # 256px 原始位图
        self._pm = None             # 按当前 DPR 预缩后的位图
        self._pm_dpr = 0.0
        if kind in self.IMAGE_KINDS:
            path = resource_path("images/sit_icon.png")
            if os.path.exists(path):
                pm = QPixmap(path)
                if not pm.isNull():
                    self._src = pm

    def _pixmap(self) -> Optional[QPixmap]:
        """按实时 devicePixelRatio 预缩到目标像素尺寸。

        不能只在 __init__ 里缩一次：控件还没上屏时 devicePixelRatioF()
        可能返回 1，等到 2 倍屏上就会被放大成糊图。
        """
        if self._src is None:
            return None
        dpr = self.devicePixelRatioF() or 1.0
        if self._pm is not None and abs(dpr - self._pm_dpr) < 0.01:
            return self._pm
        side = max(1, int(round(self._inner * dpr)))
        # 从 256 一次平滑缩到目标尺寸，比让 QPainter 双线性降采样更清晰
        self._pm = self._src.scaled(side, side, Qt.KeepAspectRatio,
                                    Qt.SmoothTransformation)
        self._pm.setDevicePixelRatio(dpr)
        self._pm_dpr = dpr
        return self._pm

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        bg = QColor(self.accent)
        bg.setAlpha(32)
        p.setPen(Qt.NoPen)
        p.setBrush(bg)
        # 分组标题图标统一用正圆底托：新稿里喝水/久坐两组的头图都是圆形
        p.drawEllipse(QRectF(self.rect()))

        pm = self._pixmap()
        if pm is not None:
            r = QRectF(0, 0, self._inner, self._inner)
            r.moveCenter(QRectF(self.rect()).center())
            p.drawPixmap(r, pm, QRectF(pm.rect()))
        else:
            inner = QRectF(0, 0, self._inner, self._inner)
            inner.moveCenter(QRectF(self.rect()).center())
            draw_glyph(p, inner, self.kind, self.accent)


class Bar(QWidget):
    """4px 细进度条。"""

    def __init__(self, accent: str):
        super().__init__()
        self.accent = QColor(accent)
        self.setFixedHeight(4)
        self._v = 0.0

    def set_value(self, v: float) -> None:
        self._v = max(0.0, min(1.0, v))
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect())
        p.setPen(Qt.NoPen)
        track = QColor(self.accent)
        track.setAlpha(26)
        p.setBrush(track)
        p.drawRoundedRect(r, 2, 2)
        if self._v > 0.001:
            p.setBrush(self.accent)
            p.drawRoundedRect(QRectF(r.left(), r.top(), r.width() * self._v, r.height()), 2, 2)


class PillButton(QPushButton):
    """通栏胶囊主按钮：渐变 + 顶部玻璃高光 + 同色弥散投影 + 右端箭头。"""

    TONES = {
        "blue":   ("#2E90FF", "#0A6BFF", (10, 132, 255)),
        "orange": ("#FFA53D", "#FF6A00", (255, 122, 0)),
        "gray":   ("#9AA6B8", "#8794A8", (122, 135, 155)),
    }

    def __init__(self, text: str = "", icon: str = "none", tone: str = "blue",
                 chevron: bool = True):
        super().__init__(text)
        self._icon = icon                 # none / play / pause
        self._tone = tone
        self._chevron = chevron
        # QSS 会覆盖 setFont，绘制时直接给 painter 设字体，保证测量与绘制一致
        self._font = ui_font(17, bold=True)
        self.setFixedHeight(PILL_H + PILL_SHADOW)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)

    def set_icon_kind(self, kind: str) -> None:
        if kind != self._icon:
            self._icon = kind
            self.update()

    def set_tone(self, tone: str) -> None:
        if tone != self._tone and tone in self.TONES:
            self._tone = tone
            self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0.5, 1, self.width() - 1, PILL_H)
        c0, c1, glow = self.TONES[self._tone]
        rad = PILL_H / 2

        p.setPen(Qt.NoPen)
        for i in range(7, 0, -1):                       # 弥散投影
            p.setBrush(QColor(*glow, 5))
            p.drawRoundedRect(r.adjusted(-i * 0.3, i * 0.55, i * 0.3, i * 0.7),
                              rad + i * 0.5, rad + i * 0.5)

        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0.0, QColor(c0))
        g.setColorAt(1.0, QColor(c1))
        p.setBrush(QBrush(g))
        p.drawPath(rounded(r, rad))

        p.save()                                        # 顶部 1px 内高光
        p.setClipPath(rounded(r.adjusted(0.7, 0.7, -0.7, -0.7), rad))
        hl = QLinearGradient(0, r.top(), 0, r.top() + PILL_H * 0.55)
        hl.setColorAt(0.0, QColor(255, 255, 255, 110))
        hl.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(hl))
        p.drawRect(QRectF(r.left(), r.top(), r.width(), PILL_H * 0.55))
        p.restore()

        # 文字整段居中：新稿里箭头独立贴在右端，不参与居中
        p.setFont(self._font)
        fm = p.fontMetrics()
        text_w = fm.horizontalAdvance(self.text())
        icon_w = 0 if self._icon == "none" else 11
        gap = 10 if icon_w else 0
        x = r.center().x() - (icon_w + gap + text_w) / 2
        cy = r.center().y()

        if icon_w:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 240))
            if self._icon == "play":
                p.drawPolygon(QPolygonF([QPointF(x, cy - 6), QPointF(x + 10, cy),
                                         QPointF(x, cy + 6)]))
            else:
                p.drawRoundedRect(QRectF(x, cy - 6, 3.4, 12), 1.7, 1.7)
                p.drawRoundedRect(QRectF(x + 6.4, cy - 6, 3.4, 12), 1.7, 1.7)

        p.setPen(QColor(255, 255, 255))
        p.drawText(QRectF(x + icon_w + gap, r.top(), text_w + 2, PILL_H),
                   Qt.AlignLeft | Qt.AlignVCenter, self.text())

        if self._chevron:
            pen = QPen(QColor(255, 255, 255, 185), 2.2)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            cx = r.right() - 26
            p.drawPolyline(QPolygonF([
                QPointF(cx - 3, cy - 6), QPointF(cx + 3, cy), QPointF(cx - 3, cy + 6)]))


class RingIcon(QWidget):
    """圆环中央的图标：自绘 glyph 或位图线稿，尺寸固定、交给布局定位。"""

    def __init__(self, kind: str, color: QColor, pixmap: Optional[QPixmap] = None,
                 size: int = 24):
        super().__init__()
        self.kind = kind
        self.color = color
        self._pm = pixmap
        self.setFixedSize(size, size)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        if self._pm is not None:
            p.drawPixmap(QRectF(self.rect()), self._pm, QRectF(self._pm.rect()))
        else:
            draw_glyph(p, QRectF(self.rect()), self.kind, self.color)


class RingCell(QWidget):
    """单个圆环：圆环自绘，环内的图标 / 数值 / 说明全部交给布局排布。

    早期用 drawText 按 0.30D / 0.615D 这类硬编码比例画文字，字号或文案一变
    就会压到圆环线上。现在换成真实控件 + QVBoxLayout(spacing=2, margins=0)，
    整列在环心垂直居中，行距由布局保证，不再依赖手算坐标。
    """

    D = 122.0            # 圆环外径（含描边）
    STROKE = 8.0

    def __init__(self, kind: str, accent: str):
        super().__init__()
        self.kind = kind
        self.accent = QColor(accent)
        self._value = 0
        self._goal = 1

        pixmap = None
        if kind == "sit":
            path = resource_path("images/sit_icon.png")
            if os.path.exists(path):
                pm = QPixmap(path)
                if not pm.isNull():
                    pixmap = pm

        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(2)
        col.addStretch(1)

        self.icon = RingIcon("drop" if kind == "water" else "sit",
                             self.accent, pixmap, 24)
        col.addWidget(self.icon, 0, Qt.AlignHCenter)

        # 数值行：数字 + 单位各自是 QLabel，用 spacing=2 的 HBox 拼成一行。
        # 这里直接把 HBox 加进竖向布局、两侧用 stretch 撑开居中，而不是套一层
        # QWidget 再 AlignHCenter——套容器时容器的 sizeHint 是构造期用 "0"
        # 量出来的，后面 setText("750") 换了文本，容器宽度不跟着更新，数字就被
        # 挤成只剩一位。直接加布局则标签始终按自身 sizeHint 显示。
        self.num = QLabel()
        self.num.setStyleSheet(
            f"color: {accent}; font-size: 22px; font-weight: 700;")
        self.num.setAlignment(Qt.AlignCenter)
        self.unit = QLabel("ml")
        self.unit.setStyleSheet(
            f"color: {accent}; font-size: 12px; font-weight: 700;"
            " padding-bottom: 3px;")          # 底对齐后略微抬到数字基线上
        self.unit.setAlignment(Qt.AlignCenter)

        rl = QHBoxLayout()
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(2)
        rl.addStretch(1)
        rl.addWidget(self.num, 0, Qt.AlignBottom)
        rl.addWidget(self.unit, 0, Qt.AlignBottom)
        rl.addStretch(1)
        col.addLayout(rl)

        self.sub = QLabel()
        self.sub.setStyleSheet(f"color: {SUB}; font-size: 11px;")
        self.sub.setAlignment(Qt.AlignCenter)
        # 固定行高：左环是 "/ 1900"、右环是中文"今日已起身"，中英文行高差 3px，
        # 不固定的话两个环的内容块总高不同，垂直居中后图标会错开一格
        self.sub.setFixedHeight(15)
        col.addWidget(self.sub)               # 占满整行宽度，文字自身居中

        col.addStretch(1)

        self.set_values(0, 1)

    def set_values(self, value: int, goal: int) -> None:
        self._value, self._goal = value, max(1, goal)
        if self.kind == "water":
            self.num.setText(str(value))
            self.unit.setVisible(True)
            self.sub.setText(f"/ {goal}")
        else:
            self.num.setText(f"{value} / {goal}")
            self.unit.setVisible(False)
            self.sub.setText("今日已起身")
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        d, s = self.D, self.STROKE
        outer = QRectF(0, 0, d, d)
        outer.moveCenter(QRectF(self.rect()).center())
        # drawArc/drawEllipse 的描边以路径为中线向两侧各扩 s/2，
        # 所以路径要内缩半个线宽，圆环外缘才正好等于 outer
        line = outer.adjusted(s / 2, s / 2, -s / 2, -s / 2)

        track = QColor(self.accent)
        track.setAlpha(42)
        p.setPen(QPen(track, s))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(line)

        frac = min(1.0, self._value / self._goal)
        if frac > 0.004:                       # 0 时不画：圆头线帽会留下一个圆点
            pen = QPen(self.accent, s)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.drawArc(line, 90 * 16, -int(360 * 16 * frac))   # 12 点起，顺时针


class RingsPanel(QWidget):
    """双环进度：左饮水（蓝）、右起身（橙），圆环本身即目标完成度。"""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(int(RingCell.D) + 12)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        self.water = RingCell("water", ACCENT_WATER)
        self.sit = RingCell("sit", ACCENT_SED)
        row.addWidget(self.water, 1)
        row.addWidget(self.sit, 1)

    def set_values(self, ml: int, stands: int,
                   goal_ml: int, goal_stands: int) -> None:
        self.water.set_values(ml, goal_ml)
        self.sit.set_values(stands, goal_stands)


class GlyphIcon(QWidget):
    """纯图标（无底托），用于分组卡内的小行。"""

    def __init__(self, kind: str, color: str, size: int = 15):
        super().__init__()
        self.kind = kind
        self.color = QColor(color)
        self.setFixedSize(size, size)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        draw_glyph(p, QRectF(self.rect()), self.kind, self.color)


class Separator(QWidget):
    """1px 分隔线。设置卡内用实线，倒计时卡内用虚线。"""

    def __init__(self, alpha: int = 60, dashed: bool = False):
        super().__init__()
        self._c = QColor(120, 140, 170, alpha)
        self._dashed = dashed
        self.setFixedHeight(1)

    def paintEvent(self, _e):
        p = QPainter(self)
        if self._dashed:
            pen = QPen(self._c, 1, Qt.CustomDashLine)
            pen.setDashPattern([3, 3])
        else:
            pen = QPen(self._c, 1)
        p.setPen(pen)
        p.drawLine(0, 0, self.width(), 0)


class CornerControls(QWidget):
    """右上角悬浮的最小化 / 关闭，仅在鼠标移入时淡入。"""

    def __init__(self, on_min, on_close, parent=None):
        super().__init__(parent)
        self.setFixedSize(58, 26)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.min_btn = self._btn("–", on_min)
        self.close_btn = self._btn("×", on_close)
        lay.addWidget(self.min_btn)
        lay.addWidget(self.close_btn)

        self._fx = QGraphicsOpacityEffect(self)
        self._fx.setOpacity(0.0)
        self.setGraphicsEffect(self._fx)
        self._anim = QPropertyAnimation(self._fx, b"opacity", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    @staticmethod
    def _btn(text: str, slot) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(26, 26)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setStyleSheet(
            "QPushButton { background: rgba(122, 135, 155, 0.16); border: 0;"
            " border-radius: 13px; color: #5B6678; font-size: 15px;"
            " padding-bottom: 3px; }"
            "QPushButton:hover { background: rgba(122, 135, 155, 0.32); }")
        btn.clicked.connect(slot)
        return btn

    def _fade(self, to: float) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._fx.opacity())
        self._anim.setEndValue(to)
        self._anim.start()

    def enterEvent(self, e):
        self._fade(1.0)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._fade(0.0)
        super().leaveEvent(e)


class ValuePill(QSpinBox):
    """胶囊外观的数字输入框：白底 + 圆角描边，宽度随内容自适应。

    做成胶囊是为了给出「这里能点、能改」的视觉暗示——纯文本数字在卡片里
    和说明文字长得一样，用户不会想到去点它。
    """

    PAD = 10                     # 胶囊内左右留白，与 QSS 的 padding 保持一致

    def __init__(self, value: int, lo: int, hi: int, step: int,
                 unit: str, accent: str):
        super().__init__()
        self.setRange(lo, hi)
        self.setSingleStep(step)
        self.setValue(value)
        self.setSuffix(unit)          # 单位写进 suffix：数字与单位成为同一段文本
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(25)
        self.setFrame(False)
        self.setButtonSymbols(QSpinBox.NoButtons)
        self.setFont(ui_font(14, bold=True))   # 与 QSS 的 font-size 对齐，便于量宽
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            f"QSpinBox {{ color: {accent}; background: #FFFFFF;"
            f" border: 1px solid #DFE7F2; border-radius: 12px;"
            f" padding: 0 {self.PAD}px; font-size: 14px; font-weight: 600; }}"
            f"QSpinBox:hover {{ border-color: {accent}; }}"
            f"QSpinBox:focus {{ border-color: {accent}; }}")
        self.valueChanged.connect(self._refit)
        self._refit()

    def _refit(self) -> None:
        """宽度跟着文本走，让胶囊像「按钮」而不是「固定宽度的输入槽」。"""
        fm = QFontMetrics(self.font())
        w = fm.horizontalAdvance(self.text()) + 2 * self.PAD + 4
        self.setFixedWidth(max(62, w))

    def changeEvent(self, e):
        # QSS 的 font-size 在 polish 时才真正接管字体，构造期量出来的宽度会偏大几像素
        if e.type() == QEvent.FontChange:
            self._refit()
        super().changeEvent(e)


class SettingRow(QWidget):
    """分组卡内的一行：名称 + 胶囊数值 + 箭头。点整行即可编辑。"""

    def __init__(self, text: str, pill: ValuePill):
        super().__init__()
        self._spin = pill
        self.setFixedHeight(33)
        self.setCursor(Qt.PointingHandCursor)

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 0, 8, 0)
        row.setSpacing(8)

        name = QLabel(text)
        name.setObjectName("RowLabel")
        row.addWidget(name)
        row.addStretch(1)
        row.addWidget(pill)

        chev = QLabel("›")
        chev.setObjectName("Chevron")
        chev.setFixedWidth(9)
        chev.setAlignment(Qt.AlignCenter)
        row.addWidget(chev)

    def mousePressEvent(self, e):
        self._spin.setFocus()
        self._spin.selectAll()
        e.accept()


class SettingCard(QFrame):
    """一组设置：淡色底卡（图标 + 标题 + 副标题）+ 白色内面板中的可编辑行。"""

    def __init__(self, title: str, subtitle: str,
                 kind: str, accent: str, tint: str):
        super().__init__()
        self.setObjectName("Group")
        self.setStyleSheet(
            f"#Group {{ background: {tint}; border: 0; border-radius: 18px; }}")
        col = QVBoxLayout(self)
        col.setContentsMargins(12, 11, 12, 11)
        col.setSpacing(0)

        head = QHBoxLayout()
        head.setContentsMargins(2, 0, 0, 0)
        head.setSpacing(9)
        head.addWidget(IconTile(kind, accent, 36))

        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(1)
        name = QLabel(title)
        name.setObjectName("GroupTitle")
        hint = QLabel(subtitle)
        hint.setObjectName("GroupSub")
        text.addWidget(name)
        text.addWidget(hint)
        head.addLayout(text)
        head.addStretch(1)
        col.addLayout(head)
        col.addSpacing(7)

        # 行放进白色内面板：淡色底卡上再叠一层白，把「可填写的表单区」
        # 和「卡头说明」在视觉上分开
        panel = QFrame()
        panel.setObjectName("Panel")
        self._pcol = QVBoxLayout(panel)
        self._pcol.setContentsMargins(0, 3, 0, 3)
        self._pcol.setSpacing(0)
        col.addWidget(panel)

    def add_row(self, label: str, pill: ValuePill) -> None:
        if self._pcol.count():                 # 第二行起，前面插一条分隔线
            wrap = QWidget()
            wl = QHBoxLayout(wrap)
            wl.setContentsMargins(12, 0, 12, 0)
            wl.setSpacing(0)
            wl.addWidget(Separator(alpha=42))
            wrap.setFixedHeight(1)
            self._pcol.addWidget(wrap)
        self._pcol.addWidget(SettingRow(label, pill))


class CountRow(QWidget):
    """倒计时行：图标 + 名称 + 大号时间 + 细进度条。"""

    def __init__(self, name: str, accent: str, kind: str):
        super().__init__()
        self.accent = accent
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 9, 0, 9)
        col.setSpacing(7)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(9)
        label = QLabel(name)
        label.setObjectName("RowTitle")
        self.time = QLabel("--:--")
        self.time.setObjectName("Time")
        top.addWidget(GlyphIcon(kind, accent, 17))
        top.addWidget(label)
        top.addStretch(1)
        top.addWidget(self.time)
        col.addLayout(top)

        self.bar = Bar(accent)
        col.addWidget(self.bar)

    def set_remain(self, remain: int, interval: int, paused: bool) -> None:
        remain = max(0, remain)
        self.time.setText(f"{remain // 60:02d}:{remain % 60:02d}")
        self.time.setStyleSheet(f"color: {DIM_COLOR};" if paused else "")
        self.bar.set_value(1 - remain / max(1, interval))


# ------------------------------ 悬浮球 ------------------------------ #

class FloatingOrb(QWidget):
    """220×162 透明画布：主球 + 两枚卫星子球 + 顶部进度胶囊。

    主球保留原有手势：单击暂停 / 继续、拖动移动窗口、右键复用托盘菜单。
    鼠标进入主球圆形范围后，两枚子球以 180ms OutBack 从球心弹出；单击
    子球完成打卡，回调 ``on_checkin(kind)`` 返回胶囊文案，返回 None 表示
    当前不可记录。本类只呈现状态，不保存或修改任何统计数据。

    几何约束（放大版）：主球 r=38、子球 r=25、两子球圆心距 60。
    胶囊底边 34，上子球顶边 39，留 5px；下子球底边 149，画布底留 13px。
    """

    CANVAS_W = 220
    CANVAS_H = 162
    BALL = 76
    LOGO = 56
    SATELLITE = 50
    LEFT_CX = 44                 # 主球靠左：子球向右侧弹出
    RIGHT_CX = 176               # 主球靠右：子球向左侧弹出（= CANVAS_W - LEFT_CX）
    CY = 94
    SAT_DX = 72                  # 主球圆心 → 子球圆心水平距离
    SAT_DY = 30                  # 子球相对主球圆心的上下偏移
    BUBBLE_TOP = 4
    BUBBLE_H = 30
    MAIN_HIT = 40                # 主球命中半径（r=38 + 2）
    SAT_HIT = 27                 # 子球命中半径（r=25 + 2）
    EXPAND_MS = 180
    COLLAPSE_MS = 170
    HIDE_DELAY_MS = 600          # 离开后的收起防抖窗口
    RESET_MS = 1200              # 打卡后自动归位
    ALERT_MS = 50                # 提醒光环刷新步长
    ALERT_PERIOD_MS = 1000       # 一个呼吸周期：v0.0.18 由 1400ms 缩短，闪动更急促
    BLUE = "#3B82F6"
    ORANGE = "#F97316"

    def __init__(self, on_primary: Callable[[], None], menu: QMenu,
                 on_checkin: Optional[Callable[[str], Optional[str]]] = None):
        super().__init__(
            None,
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool,
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedSize(self.CANVAS_W, self.CANVAS_H)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover, True)

        # 顶层窗口不能挂 QGraphicsDropShadowEffect：离屏缓存会让每次重绘都
        # 合成整窗，hover / 子球动画会明显掉帧。阴影预生成两张位图，之后只贴图。
        self._shadow_main = self._make_shadow(self.BALL + 16)
        self._shadow_sat = self._make_shadow(self.SATELLITE + 16)

        self._on_primary = on_primary
        self._on_checkin = on_checkin
        self._menu = menu

        self._running = False
        self._paused = False
        self._water_ratio = 1.0
        self._sed_ratio = 1.0

        self._right_side = True       # 默认贴屏幕右侧：主球靠右、子球向左
        self._expand = 0.0            # 0 = 收起，1 = 完全展开（OutBack 可短暂过冲）
        self._expanded = False
        self._hover_kind: Optional[str] = None
        self._hover = 0.0
        self._hovered = False

        self._press_offset = None
        self._press_kind: Optional[str] = None
        self._dragging = False

        self._feedback_kind: Optional[str] = None
        self._feedback_step = 0
        self._click = 0.0

        self._alerts: set = set()     # {"water"} / {"stand"} / 两者
        self._alert_phase = 0.0

        self._checked: Optional[str] = None
        self._check_t = 0.0
        self._nudge_kind: Optional[str] = None
        self._nudge_t = 0.0

        self._bubble_text = ""
        self._bubble_alpha = 0.0
        self._bubble_font = 11
        self._bubble_w = 0.0

        self._logo = QPixmap()
        for name in ("images/logo.png", "images/logo.ico"):
            path = resource_path(name)
            if os.path.exists(path):
                pm = QPixmap(path)
                if not pm.isNull():
                    # 预缩到 3 倍图，悬停重绘时不再从 1024px 原图重采样。
                    self._logo = pm.scaled(
                        self.LOGO * 3, self.LOGO * 3,
                        Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    break

        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.setDuration(150)
        self._hover_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._hover_anim.valueChanged.connect(self._on_hover_value)

        self._click_anim = QVariantAnimation(self)
        self._click_anim.setDuration(200)
        self._click_anim.setStartValue(0.0)
        self._click_anim.setEndValue(1.0)
        self._click_anim.valueChanged.connect(self._on_click_value)

        self._expand_anim = QVariantAnimation(self)
        self._expand_anim.valueChanged.connect(self._on_expand_value)
        self._expand_anim.finished.connect(self._on_expand_done)

        self._check_anim = QVariantAnimation(self)
        self._check_anim.setDuration(280)
        self._check_anim.setStartValue(0.0)
        self._check_anim.setEndValue(1.0)
        self._check_anim.setEasingCurve(QEasingCurve.OutBack)
        self._check_anim.valueChanged.connect(self._on_check_value)

        self._nudge_anim = QVariantAnimation(self)
        self._nudge_anim.setDuration(260)
        self._nudge_anim.setStartValue(0.0)
        self._nudge_anim.setEndValue(1.0)
        self._nudge_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._nudge_anim.valueChanged.connect(self._on_nudge_value)

        self._bubble_anim = QVariantAnimation(self)
        self._bubble_anim.setDuration(180)
        self._bubble_anim.valueChanged.connect(self._on_bubble_value)

        self._feedback_timer = QTimer(self)
        self._feedback_timer.setInterval(35)
        self._feedback_timer.timeout.connect(self._advance_feedback)

        self._alert_timer = QTimer(self)
        self._alert_timer.setInterval(self.ALERT_MS)
        self._alert_timer.timeout.connect(self._advance_alert)

        # 600ms 单次防抖：离开球体后不立即收起，留出移向子球的时间。
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(self.HIDE_DELAY_MS)
        self._hide_timer.timeout.connect(self._collapse_now)

        self._reset_timer = QTimer(self)
        self._reset_timer.setSingleShot(True)
        self._reset_timer.setInterval(self.RESET_MS)
        self._reset_timer.timeout.connect(self._after_checkin)

        self._update_tooltip()
        self._move_to_default()
        self._refresh_mask()

    # ---------------------------- 几何 ---------------------------- #

    @staticmethod
    def _dist(a: QPointF, b: QPointF) -> float:
        return math.hypot(a.x() - b.x(), a.y() - b.y())

    @staticmethod
    def _circle(center: QPointF, d: float) -> QRectF:
        return QRectF(center.x() - d / 2, center.y() - d / 2, d, d)

    def _main_center(self) -> QPointF:
        return QPointF(self.RIGHT_CX if self._right_side else self.LEFT_CX, self.CY)

    def _sat_targets(self) -> dict:
        c = self._main_center()
        dx = -self.SAT_DX if self._right_side else self.SAT_DX
        return {
            "water": QPointF(c.x() + dx, c.y() - self.SAT_DY),
            "stand": QPointF(c.x() + dx, c.y() + self.SAT_DY),
        }

    def _sat_position(self, kind: str) -> QPointF:
        c = self._main_center()
        target = self._sat_targets()[kind]
        t = max(0.0, min(1.15, self._expand))
        return QPointF(c.x() + (target.x() - c.x()) * t,
                       c.y() + (target.y() - c.y()) * t)

    def _hit_test(self, pos: QPointF) -> Optional[str]:
        if self._dist(pos, self._main_center()) <= self.MAIN_HIT:
            return "main"
        if self._expand > 0.55:
            for kind in ("water", "stand"):
                # 提醒态子球放大 1.15 倍，命中半径必须同步放大，
                # 否则点在最外圈会没反应。
                radius = self.SAT_HIT
                if kind in self._alerts:
                    radius = self.SATELLITE * 1.15 / 2 + 2
                if self._dist(pos, self._sat_position(kind)) <= radius:
                    return kind
        return None

    def _refresh_mask(self) -> None:
        """窗口大部分是透明区，用圆并集做输入遮罩。

        不加遮罩的话，这块透明矩形会把下方应用的点击一起吃掉。
        """
        c = self._main_center()
        r = self.BALL // 2 + 16
        # 圆必须被画布裁一遍：主球靠左时热区会探出画布左侧。
        main_rect = QRegion(int(c.x() - r), int(c.y() - r), r * 2, r * 2,
                            QRegion.Ellipse).intersected(
            QRegion(0, 0, self.CANVAS_W, self.CANVAS_H))
        region = main_rect
        if self._expanded or self._expand > 0.01:
            for target in self._sat_targets().values():
                rr = self.SATELLITE // 2 + 14
                region = region.united(QRegion(
                    int(target.x() - rr), int(target.y() - rr),
                    rr * 2, rr * 2, QRegion.Ellipse))
        # 胶囊只在真正可见时才占输入区，否则会在屏幕顶部留下一条点击死区。
        if self._bubble_alpha > 0.01 and self._bubble_text:
            region = region.united(QRegion(
                int((self.CANVAS_W - self._bubble_w) / 2) - 6,
                self.BUBBLE_TOP - 4,
                int(self._bubble_w) + 12,
                self.BUBBLE_H + 8))
        # 子球热区会让靠下那颗探出画布几像素，统一裁到画布内。
        self.setMask(region.intersected(QRegion(0, 0, self.CANVAS_W, self.CANVAS_H)))

    def _make_shadow(self, size: int) -> QPixmap:
        """一次性生成柔和投影，替代昂贵的顶层 QGraphicsEffect。"""
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, True)
        center = QPointF(size / 2, size / 2 + 1)
        gradient = QRadialGradient(center, size / 2 - 2)
        gradient.setColorAt(0.0, QColor(0, 0, 0, 46))
        gradient.setColorAt(0.70, QColor(0, 0, 0, 26))
        gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(gradient))
        p.drawEllipse(QRectF(1, 3, size - 2, size - 4))
        p.end()
        return pm

    def _move_to_default(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        # 主球圆心距右边缘 58、距底 188（= 旧版 180 + 半径增量 8），
        # 保证放大后球体底边与屏幕底边的间距不变。
        self._right_side = True
        self.move(area.right() - 58 - self.RIGHT_CX,
                  area.bottom() - 188 - self.CY)

    def _update_side(self, compensate: bool) -> None:
        """贴到屏幕右缘时改用「主球靠右、子球向左」布局，并保持主球视觉位置不动。"""
        screen = QApplication.screenAt(self.frameGeometry().center())
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        gap = area.right() - (self.x() + self.width())
        want_right = gap < 120
        if want_right == self._right_side:
            return
        # 先按旧布局取屏幕坐标，再切换，否则 _main_center() 已经变成新圆心。
        screen_cx = self.x() + self._main_center().x()
        self._right_side = want_right
        if compensate:
            new_x = int(round(screen_cx - (self.RIGHT_CX if want_right else self.LEFT_CX)))
            # 窗口不能越出可用区，钳制后主球可能略有位移，这是可接受的边界代价。
            new_x = max(area.left(), min(new_x, area.right() - self.width() + 1))
            self.move(new_x, self.y())
        self._refresh_mask()
        self.update()

    # ---------------------------- 状态同步 ---------------------------- #

    def _update_tooltip(self) -> None:
        if not self._running:
            primary = "左键打开"
        else:
            primary = "左键继续" if self._paused else "左键暂停"
        self.setToolTip(
            f"健康生活小助手\n{primary} · 悬停主球展开打卡 · 拖动移动 · 右键菜单")

    def set_progress(self, water: float, sed: float, running: bool) -> None:
        """传入剩余时间比例：1 = 刚到起点，0 = 到点。暂停时数值自然冻结。"""
        water = max(0.0, min(1.0, water))
        sed = max(0.0, min(1.0, sed))
        changed = running != self._running
        self._running = running
        self._water_ratio = water
        self._sed_ratio = sed
        if changed:
            self._update_tooltip()
        self.update()

    def set_paused(self, paused: bool) -> None:
        """暂停是持续状态；悬停时暂停符号切换为播放符号，同时收起子球。"""
        if self._paused == paused:
            return
        self._paused = paused
        if paused:
            self._feedback_timer.stop()
            self._feedback_kind = None
            self._hide_timer.stop()
            self._collapse_now()
            # 收起后鼠标可能仍压在主球上，清掉悬停记录，下次移动才能重新展开。
            self._hover_kind = None
        self._update_tooltip()
        self.click_feedback()
        self.update()

    def set_alert(self, kind: str) -> None:
        """倒计时到点：主球进入呼吸光环，对应子球在展开时高亮引导。"""
        if kind not in ("water", "stand") or kind in self._alerts:
            return
        self._alerts.add(kind)
        if not self._alert_timer.isActive():
            self._alert_timer.start()
        self.update()

    def clear_alert(self, kind: Optional[str] = None) -> None:
        if kind is None:
            self._alerts.clear()
        else:
            self._alerts.discard(kind)
        if not self._alerts:
            self._alert_timer.stop()
            self._alert_phase = 0.0
        self.update()

    def _alert_kind(self) -> Optional[str]:
        if "water" in self._alerts:
            return "water"
        if "stand" in self._alerts:
            return "stand"
        return None

    def _advance_alert(self) -> None:
        # 约 1 秒一个呼吸周期（旧版 1.4 秒），暂停时相位冻结、光环不闪。
        if not self._paused:
            self._alert_phase = (
                self._alert_phase + self.ALERT_MS / self.ALERT_PERIOD_MS) % 1.0
        self.update()

    # ---------------------------- 动画驱动 ---------------------------- #

    def click_feedback(self) -> None:
        """单击或状态切换后给一圈 200ms 的确认扩散，不让操作显得无响应。"""
        self._click_anim.stop()
        self._click = 0.0
        self._click_anim.start()

    def _on_click_value(self, value) -> None:
        self._click = float(value)
        self.update()

    def feedback(self, kind: str) -> None:
        """真实记录成功后短暂显示水滴 / 人形，并扩散一圈同色涟漪。"""
        if kind not in ("drop", "person"):
            return
        self._feedback_kind = kind
        self._feedback_step = 0
        self._feedback_timer.start()
        self.update()

    def _advance_feedback(self) -> None:
        self._feedback_step += 1
        if self._feedback_step >= 26:
            self._feedback_timer.stop()
            self._feedback_kind = None
        self.update()

    def _on_hover_value(self, value) -> None:
        self._hover = float(value)
        self.update()

    def _animate_hover(self, target: float) -> None:
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover)
        self._hover_anim.setEndValue(target)
        self._hover_anim.start()

    def _animate_expand(self, target: float, duration: int) -> None:
        self._expand_anim.stop()
        self._expand_anim.setDuration(duration)
        # 弹出用 OutBack 制造回弹；收起用 OutCubic，避免先反向膨胀一下。
        self._expand_anim.setEasingCurve(
            QEasingCurve.OutBack if target > 0 else QEasingCurve.OutCubic)
        self._expand_anim.setStartValue(self._expand)
        self._expand_anim.setEndValue(target)
        self._expand_anim.start()

    def _on_expand_value(self, value) -> None:
        self._expand = float(value)
        # 收起动画期间子球还没回到主球，遮罩必须跟着缩，不能立刻裁掉。
        self._refresh_mask()
        self.update()

    def _on_expand_done(self) -> None:
        if not self._expanded:
            self._expand = 0.0
            self._refresh_mask()
            self.update()

    def _on_check_value(self, value) -> None:
        self._check_t = float(value)
        self.update()

    def _on_nudge_value(self, value) -> None:
        self._nudge_t = float(value)
        self.update()

    def _on_bubble_value(self, value) -> None:
        self._bubble_alpha = float(value)
        self._refresh_mask()
        self.update()

    # ---------------------------- 展开 / 收起 ---------------------------- #

    def _expand_now(self) -> None:
        if self._expanded:
            return
        self._expanded = True
        self._refresh_mask()          # 先扩遮罩，否则子球动画会被裁在主球圆内
        self._animate_expand(1.0, self.EXPAND_MS)

    def _collapse_now(self) -> None:
        if not self._expanded:
            return
        self._expanded = False
        self._hide_timer.stop()
        self._checked = None
        self._nudge_kind = None
        if self._hover_kind in ("water", "stand"):
            self._hover_kind = None
        self._fade_bubble(0.0)
        self._animate_expand(0.0, self.COLLAPSE_MS)

    # ---------------------------- 悬停判定 ---------------------------- #

    def _update_hover(self, pos: QPointF) -> None:
        if self._press_offset is not None and self._dragging:
            return
        kind = self._hit_test(pos)
        if kind != self._hover_kind:
            self._hover_kind = kind
            self._hovered = kind is not None
            self._animate_hover(1.0 if kind is not None else 0.0)
        if kind is not None:
            self._hide_timer.stop()
            if kind == "main":
                # 无条件调用：暂停会收起子球但鼠标仍停在主球上，
                # 只靠 kind 变化判断会再也展不开。
                self._expand_now()
        elif self._expanded and not self._hide_timer.isActive():
            # 只在计时未启动时启动：鼠标在球体外继续移动不重置 600ms 窗口。
            self._hide_timer.start(self.HIDE_DELAY_MS)
        self.update()

    def enterEvent(self, e) -> None:
        self._update_hover(QPointF(self.mapFromGlobal(QCursor.pos())))
        super().enterEvent(e)

    def leaveEvent(self, e) -> None:
        self._hover_kind = None
        self._hovered = False
        self._animate_hover(0.0)
        if self._expanded:
            self._hide_timer.start(self.HIDE_DELAY_MS)
        self.update()
        super().leaveEvent(e)

    # ---------------------------- 打卡 ---------------------------- #

    def _checkin(self, kind: str) -> None:
        text = None
        if self._on_checkin is not None:
            text = self._on_checkin(kind)
        if not text:
            # 待机 / 暂停时子球仍可弹出，但记录入口是关闭的，抖一下表明无效。
            self._nudge_kind = kind
            self._nudge_t = 0.0
            self._nudge_anim.stop()
            self._nudge_anim.start()
            self.update()
            return
        self._checked = kind
        self._check_t = 0.0
        self._check_anim.stop()
        self._check_anim.start()
        self._nudge_kind = None
        self.clear_alert("water" if kind == "water" else "stand")
        self._show_bubble(text)
        # 打卡后自动归位：胶囊淡出 + 子球缩回，不需要用户再移开鼠标。
        self._reset_timer.start(self.RESET_MS)

    def _after_checkin(self) -> None:
        self._checked = None
        self._fade_bubble(0.0)
        self._collapse_now()

    def _show_bubble(self, text: str) -> None:
        size, width, shown = self._bubble_metrics(text)
        self._bubble_text = shown
        self._bubble_font = size
        self._bubble_w = width
        self._refresh_mask()
        self._fade_bubble(1.0)

    def _fade_bubble(self, target: float) -> None:
        self._bubble_anim.stop()
        self._bubble_anim.setDuration(180 if target > 0 else 240)
        self._bubble_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._bubble_anim.setStartValue(self._bubble_alpha)
        self._bubble_anim.setEndValue(target)
        self._bubble_anim.start()

    def _bubble_metrics(self, text: str):
        """按画布宽度选字号；放大版优先 13 号字，放不下才逐级降。"""
        limit = self.CANVAS_W - 8
        for size in (13, 12, 11, 10):
            fm = QFontMetrics(ui_font(size, True))
            width = getattr(fm, "horizontalAdvance", fm.width)(text) + 20
            if width <= limit:
                return size, float(width), text
        fm = QFontMetrics(ui_font(10, True))
        return 10, float(limit), fm.elidedText(text, Qt.ElideRight, int(limit - 20))

    # ---------------------------- 绘制 ---------------------------- #

    def _draw_logo(self, p: QPainter, base: QRectF, dy: float = 0.0) -> None:
        p.save()
        clip = QPainterPath()
        clip.addEllipse(base)
        p.setClipPath(clip)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(base)
        if not self._logo.isNull():
            logo_rect = QRectF(0, 0, self.LOGO, self.LOGO)
            logo_rect.moveCenter(base.center() + QPointF(0, dy))
            p.drawPixmap(logo_rect, self._logo, QRectF(self._logo.rect()))
        p.restore()

    def _draw_main(self, p: QPainter) -> None:
        base = self._circle(self._main_center(), self.BALL)
        center = base.center()
        # 所有装饰尺寸相对 60px 基线缩放：调大 BALL 时图标、光环、进度环
        # 会同步放大，不会留下细线小图标配大球的违和感。
        k = self.BALL / 60.0
        # 微缩放只改变绘制，不改变窗口与命中半径；展开时轻微回落让出视觉焦点。
        scale = 1.0 + 0.08 * self._hover - 0.06 * max(0.0, min(1.0, self._expand))
        p.save()
        p.translate(center)
        p.scale(scale, scale)
        p.translate(-center)

        alert = self._alert_kind()
        if alert is not None:
            self._draw_alert_rings(p, base, alert)
        elif self._hover > 0.001:
            halo = QColor(59, 130, 246, int(76 * self._hover))
            p.setPen(QPen(halo, 5 * k))
            p.setBrush(Qt.NoBrush)
            spread = (2.5 + 1.5 * self._hover) * k
            p.drawEllipse(base.adjusted(-spread, -spread, spread, spread))

        kind = self._feedback_kind
        icon_dy = 0.0
        if kind is None and alert is not None:
            kind = "drop" if alert == "water" else "person"
            ph = 0.5 - 0.5 * math.cos(2 * math.pi * self._alert_phase)
            # 水滴上下浮动、人形小幅跳跃；v0.0.18 幅度加大，让闪动更醒目。
            icon_dy = (-4.5 if kind == "drop" else -6.5) * ph * k
        if kind is None:
            if self._paused:
                kind = "play" if self._hover_kind == "main" else "pause"
            elif self._running and self._hover_kind == "main":
                kind = "pause"            # 明示单击将暂停
            else:
                kind = "logo"

        if kind in ("drop", "person"):
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(self.BLUE if kind == "drop" else self.ORANGE))
            p.drawEllipse(base)
            inner = base.adjusted(16 * k, 15 * k, -16 * k, -15 * k).translated(0, icon_dy)
            draw_glyph(p, inner, kind, QColor(255, 255, 255))
        else:
            self._draw_logo(p, base)
            if kind in ("pause", "play"):
                # 保留 logo，只覆盖半透明深色层，不用实心灰球替换。
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(30, 41, 59, 166))
                p.drawEllipse(base)
                p.setBrush(QColor(255, 255, 255))
                c = base.center()
                if kind == "pause":
                    p.drawRoundedRect(QRectF(c.x() - 10 * k, c.y() - 11 * k,
                                             7 * k, 22 * k), 3 * k, 3 * k)
                    p.drawRoundedRect(QRectF(c.x() + 3 * k, c.y() - 11 * k,
                                             7 * k, 22 * k), 3 * k, 3 * k)
                else:
                    p.drawPolygon(QPolygonF([
                        QPointF(c.x() - 7 * k, c.y() - 12 * k),
                        QPointF(c.x() + 12 * k, c.y()),
                        QPointF(c.x() - 7 * k, c.y() + 12 * k),
                    ]))

        # 半透明高光内描边，强化球体与深色壁纸之间的分离感。
        p.setPen(QPen(QColor(255, 255, 255, 170), 1.5 * k))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(base.adjusted(0.75 * k, 0.75 * k, -0.75 * k, -0.75 * k))

        # 外圈轨道常驻；运行时左半蓝弧=喝水剩余，右半橙弧=起身剩余。
        ring = base.adjusted(-2 * k, -2 * k, 2 * k, 2 * k)
        width = (3.0 + self._hover) * k
        p.setPen(QPen(QColor(226, 232, 240, 204), width))
        p.drawEllipse(ring)
        if self._running:
            alpha = 120 if self._paused else 255
            water = QColor(self.BLUE)
            water.setAlpha(alpha)
            pen = QPen(water, width)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.drawArc(ring, 90 * 16, int(180 * 16 * self._water_ratio))
            sed = QColor(self.ORANGE)
            sed.setAlpha(alpha)
            pen = QPen(sed, width)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.drawArc(ring, 90 * 16, -int(180 * 16 * self._sed_ratio))

        if 0.001 < self._click < 0.999:            # 200ms 单击确认脉冲
            pulse = QColor(59, 130, 246, int(150 * (1 - self._click)))
            p.setPen(QPen(pulse, 2.4 * k))
            spread = (3 + self._click * 5) * k
            p.drawEllipse(base.adjusted(-spread, -spread, spread, spread))

        if self._feedback_kind is not None:         # 约 0.9 秒记录反馈
            progress = self._feedback_step / 26.0
            spread = (2 + progress * 6) * k
            ring_color = QColor(self.BLUE if self._feedback_kind == "drop" else self.ORANGE)
            ring_color.setAlpha(max(0, int(150 * (1 - progress))))
            p.setPen(QPen(ring_color, 2.2 * k))
            p.drawEllipse(base.adjusted(-spread, -spread, spread, spread))
        p.restore()

    def _draw_alert_rings(self, p: QPainter, base: QRectF, alert: str) -> None:
        """扩散光晕 + 双圈脉冲涟漪，暂停时相位冻结。

        v0.0.18：辐射范围扩大约 1.7 倍、周期 1400ms → 1000ms。
        外层用径向渐变（球边缘最亮、向外淡出到全透明），主球贴屏幕
        边缘被画布裁切时也能自然消散，不会露出半截描边硬边。
        """
        ph = 0.5 - 0.5 * math.cos(2 * math.pi * self._alert_phase)
        k = self.BALL / 60.0
        color = QColor(self.BLUE if alert == "water" else self.ORANGE)
        center = base.center()
        r_ball = self.BALL / 2.0
        outer = r_ball + (16.0 + 30.0 * ph) * k

        # 1) 径向渐变光晕：主要视觉，向外淡出，贴边裁切也无硬边。
        grad = QRadialGradient(center, outer)
        transparent = QColor(color.red(), color.green(), color.blue(), 0)
        peak = QColor(color)
        peak.setAlpha(max(0, int(125 * (0.40 + 0.60 * ph))))
        grad.setColorAt(0.0, transparent)
        grad.setColorAt(max(0.01, min(0.99, r_ball / outer)), peak)
        grad.setColorAt(1.0, transparent)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(QRectF(center.x() - outer, center.y() - outer,
                             outer * 2, outer * 2))

        # 2) 双圈脉冲涟漪：内圈稳定清晰，外圈扩散并淡出，强化"闪动"节奏。
        p.setBrush(Qt.NoBrush)
        for grow, spread, alpha, width, fade in (
            (4.0, 9.0 * ph, 165, 3.0, 0.35),
            (11.0, 22.0 * ph, 105, 2.4, 0.80),
        ):
            c = QColor(color)
            a = alpha * (0.45 + 0.55 * ph) * (1.0 - fade * ph)
            c.setAlpha(max(0, min(255, int(a))))
            p.setPen(QPen(c, width * (0.85 + 0.15 * ph) * k))
            d = (grow + spread) * k
            p.drawEllipse(base.adjusted(-d, -d, d, d))

    def _draw_tick(self, p: QPainter, rect: QRectF) -> None:
        pen = QPen(QColor(255, 255, 255), max(2.6, rect.width() * 0.08))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        w, c = rect.width(), rect.center()
        p.drawPolyline(QPolygonF([
            QPointF(c.x() - w * 0.20, c.y() + w * 0.01),
            QPointF(c.x() - w * 0.06, c.y() + w * 0.15),
            QPointF(c.x() + w * 0.21, c.y() - w * 0.15),
        ]))

    def _draw_satellites(self, p: QPainter) -> None:
        if self._expand <= 0.001:
            return
        alpha = max(0.0, min(1.0, self._expand))
        ph = 0.5 - 0.5 * math.cos(2 * math.pi * self._alert_phase)

        for kind in ("water", "stand"):
            center = self._sat_position(kind)
            hovered = self._hover_kind == kind
            alerted = kind in self._alerts
            # 提醒态：对应子球放大到 46px（1.15 倍）并加闪烁白边引导点击。
            scale = 1.15 if alerted else 1.0
            if hovered:
                scale += 0.05
            if self._checked == kind:
                scale += 0.12 * math.sin(math.pi * min(1.0, self._check_t))
            if self._nudge_kind == kind:
                center = QPointF(center.x() + math.sin(self._nudge_t * math.pi * 3) * 4.0,
                                 center.y())

            d = self.SATELLITE * scale
            rect = QRectF(0, 0, d, d)
            rect.moveCenter(center)

            p.save()
            p.setOpacity(alpha)

            p.drawPixmap(QPointF(center.x() - self._shadow_sat.width() / 2,
                                 center.y() - self._shadow_sat.height() / 2),
                         self._shadow_sat)

            grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
            if kind == "water":
                grad.setColorAt(0.0, QColor("#60A5FA"))
                grad.setColorAt(1.0, QColor(self.BLUE))
            else:
                grad.setColorAt(0.0, QColor("#FB923C"))
                grad.setColorAt(1.0, QColor(self.ORANGE))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(grad))
            p.drawEllipse(rect)

            p.setPen(QPen(QColor(255, 255, 255, 210), 1.8))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(rect.adjusted(0.9, 0.9, -0.9, -0.9))

            if self._checked == kind:
                self._draw_tick(p, rect)
            else:
                inner = rect.adjusted(d * 0.29, d * 0.27, -d * 0.29, -d * 0.27)
                draw_glyph(p, inner, "drop" if kind == "water" else "person",
                           QColor(255, 255, 255))

            if alerted and self._expand > 0.8:
                # v0.0.18：彩色涟漪向外扩散并淡出，配合更亮的白边，
                # 让「该点哪颗球」在一屏里也能一眼看到。
                ripple = QColor(self.BLUE if kind == "water" else self.ORANGE)
                ripple.setAlpha(max(0, int(120 * (1.0 - ph))))
                p.setPen(QPen(ripple, 2.4))
                p.setBrush(Qt.NoBrush)
                rd = 3.0 + 13.0 * ph
                p.drawEllipse(rect.adjusted(-rd, -rd, rd, rd))
                glow = QColor(255, 255, 255)
                glow.setAlpha(max(0, int(150 + 105 * ph)))
                p.setPen(QPen(glow, 3.2))
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(rect.adjusted(-2.5, -2.5, 2.5, 2.5))
            p.restore()

    def _draw_bubble(self, p: QPainter) -> None:
        if self._bubble_alpha <= 0.01 or not self._bubble_text:
            return
        rect = QRectF((self.CANVAS_W - self._bubble_w) / 2,
                      self.BUBBLE_TOP, self._bubble_w, self.BUBBLE_H)
        p.save()
        p.setOpacity(self._bubble_alpha)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(15, 23, 42, 217))
        p.drawRoundedRect(rect, self.BUBBLE_H / 2, self.BUBBLE_H / 2)
        p.setPen(QColor(255, 255, 255))
        p.setFont(ui_font(self._bubble_font, True))
        p.drawText(rect, Qt.AlignCenter, self._bubble_text)
        p.restore()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)

        c = self._main_center()
        p.drawPixmap(QPointF(c.x() - self._shadow_main.width() / 2,
                             c.y() - self._shadow_main.height() / 2),
                     self._shadow_main)
        self._draw_satellites(p)
        self._draw_main(p)
        self._draw_bubble(p)

    # ---------------------------- 鼠标 ---------------------------- #

    def contextMenuEvent(self, e) -> None:
        self._menu.exec_(e.globalPos())
        e.accept()

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.LeftButton:
            kind = self._hit_test(QPointF(e.pos()))
            self._press_kind = kind
            # 无论按在主球还是子球都能拖动，避免用户想挪球却按在子球上失灵。
            self._press_offset = e.globalPos() - self.frameGeometry().topLeft()
            self._dragging = False
            e.accept()
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e) -> None:
        if self._press_offset is not None and e.buttons() & Qt.LeftButton:
            target = e.globalPos() - self._press_offset
            if (target - self.frameGeometry().topLeft()).manhattanLength() > 5:
                self._dragging = True
            if self._dragging:
                screen = QApplication.screenAt(e.globalPos()) or QApplication.primaryScreen()
                if screen is not None:
                    area = screen.availableGeometry()
                    target.setX(max(area.left(), min(target.x(),
                                                     area.right() - self.width() + 1)))
                    target.setY(max(area.top(), min(target.y(),
                                                    area.bottom() - self.height() + 1)))
                self.move(target)
            e.accept()
        else:
            self._update_hover(QPointF(e.pos()))
            e.accept()

    def mouseReleaseEvent(self, e) -> None:
        if e.button() == Qt.LeftButton and self._press_offset is not None:
            was_dragging = self._dragging
            kind = self._press_kind
            self._press_offset = None
            self._press_kind = None
            self._dragging = False
            if was_dragging:
                # 拖动结束后再决定左右布局，避免拖动过程中主球来回跳。
                self._update_side(compensate=True)
            elif kind == "main":
                self._on_primary()
            elif kind in ("water", "stand"):
                if self._hit_test(QPointF(e.pos())) == kind:
                    self._checkin(kind)
            e.accept()
        else:
            super().mouseReleaseEvent(e)


# ------------------------------ 主窗口 ------------------------------ #

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = Settings.load()
        # 每次启动都从零开始：上一次使用（含异常退出）的累计不再延续
        self.settings.today_ml = 0
        self.settings.today_sips = 0
        self.settings.today_stands = 0
        self.settings.save()
        self.setFocusPolicy(Qt.StrongFocus)   # 启动时焦点停在窗口上，不落在输入框

        # 运行状态
        self.running = False
        self.paused = False
        self._t0 = 0.0                 # 会话起点（monotonic）
        self._paused_total = 0.0       # 累计暂停秒数
        self._paused_at: Optional[float] = None
        self._sed_interval = 0
        self._water_interval = 0
        self._next_sed = 0.0           # 下次久坐提醒（有效运行秒）
        self._next_water = 0.0
        self._pending_kind: Optional[str] = None
        self._tray_hinted = False

        # 本次会话记录（用于报告）
        self._session_start: Optional[datetime] = None
        self._drinks: list = []      # [(datetime, 有效秒数)]
        self._stands: list = []

        self._build_ui()
        self._build_toast()
        self._build_tray()
        self._build_floating()

        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._on_tick)

        self._pending_timer = QTimer(self)
        self._pending_timer.setSingleShot(True)
        self._pending_timer.timeout.connect(self._flush_pending)

        self._apply_mode("idle")
        self._refresh_stats()

    # ---------------------------- 界面 ---------------------------- #

    def _build_ui(self) -> None:
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(self._app_icon())
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.StrongFocus)

        page = QWidget()
        page.setMinimumWidth(WIN_W)

        root = QVBoxLayout(page)
        root.setContentsMargins(20, 14, 20, 14)
        root.setSpacing(0)

        # ---- 标题区：居中大标题 + 副标题 ----
        title = QLabel(APP_NAME)
        title.setObjectName("H1")
        title.setAlignment(Qt.AlignCenter)
        title.setFixedHeight(36)
        root.addWidget(title)
        root.addSpacing(2)

        sub = QLabel("定时提醒，养成好习惯，保持健康生活节奏")
        sub.setObjectName("Sub")
        sub.setAlignment(Qt.AlignCenter)
        sub.setFixedHeight(18)
        root.addWidget(sub)
        root.addSpacing(8)

        # ---- 双环进度 ----
        self.rings = RingsPanel()
        root.addWidget(self.rings)
        root.addSpacing(10)

        root.addWidget(self._build_setup())
        root.addWidget(self._build_run())
        root.addSpacing(10)

        # 改目标时立刻预览圆环进度（不写盘，点开始才保存）
        for spin in (self.goal_ml_spin, self.goal_stand_spin):
            spin.valueChanged.connect(self._preview_goals)

        # 主按钮只做一个：待机=开始 / 运行=暂停 / 暂停中=继续。
        # 早期是 start_btn + pause_btn 两个控件按状态显隐，隐藏时仍会参与布局，
        # 得靠间距项手工补正；合并成一个后状态切换只改文字与配色。
        self.main_btn = PillButton("开始计时", "play")
        self.main_btn.clicked.connect(self._on_main)
        root.addWidget(self.main_btn)

        self.actions = QWidget()
        acts = QHBoxLayout(self.actions)
        acts.setContentsMargins(0, 10, 0, 0)     # 上间距放进来，隐藏时一起收起
        acts.setSpacing(8)
        # 按钮 / 菜单的 clicked、triggered 都会带一个 bool，不能直接接到
        # 带默认参数的 _log_sip：那会把 checked 当成 quiet 传进去。
        self.sip_btn = self._ghost("喝了一杯", lambda: self._log_sip())
        self.stand_btn = self._ghost("起身了", lambda: self._log_stand())
        self.stop_btn = self._ghost("结束", self._stop)
        for btn in (self.sip_btn, self.stand_btn, self.stop_btn):
            btn.setFixedHeight(34)
            # Fusion 给 QPushButton 的尺寸提示是 150×46（与文字无关），
            # 三个并排会把运行态窗口从 412 撑到 542；Ignored 让它们只按 1/3 分宽度
            btn.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            acts.addWidget(btn, 1)
        root.addWidget(self.actions)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(SHADOW, SHADOW, SHADOW, SHADOW)
        outer.setSizeConstraint(QLayout.SetFixedSize)     # 窗口始终贴合内容
        outer.addWidget(page)

        self.controls = CornerControls(self.showMinimized, self.close, self)
        self.controls.raise_()
        self._drag_from = None

    def _build_setup(self) -> QWidget:
        box = QWidget()
        col = QVBoxLayout(box)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(10)

        self.sed_spin = self._spin(self.settings.sed_min, 1, 600, "分钟", ACCENT_SED)
        self.water_spin = self._spin(self.settings.water_min, 1, 600, "分钟", ACCENT_WATER)
        self.sip_spin = self._spin(self.settings.sip_ml, 50, 2000, "ml",
                                   ACCENT_WATER, step=50)
        self.goal_ml_spin = self._spin(self.settings.goal_ml, 200, 5000, "ml",
                                       ACCENT_WATER, step=100)
        self.goal_stand_spin = self._spin(self.settings.goal_stands, 1, 50, "次", ACCENT_SED)

        water = SettingCard("喝水设置", "设置每日喝水目标和每次饮水量",
                            "drop", ACCENT_WATER, TINT_WATER)
        water.add_row("提醒间隔", self.water_spin)
        water.add_row("每次饮水量", self.sip_spin)
        water.add_row("每日目标", self.goal_ml_spin)

        sit = SettingCard("久坐提醒设置", "设置起身提醒间隔和每日起身次数",
                          "sit", ACCENT_SED, TINT_SED)
        sit.add_row("提醒间隔", self.sed_spin)
        sit.add_row("每日目标起身次数", self.goal_stand_spin)

        col.addWidget(water)
        col.addWidget(sit)

        self.setup_box = box
        return box

    def _build_run(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        col = QVBoxLayout(card)
        col.setContentsMargins(14, 4, 14, 4)
        col.setSpacing(0)

        self.row_sed = CountRow("久坐提醒", ACCENT_SED, "clock")
        self.row_water = CountRow("喝水提醒", ACCENT_WATER, "clock")
        col.addWidget(self.row_sed)
        col.addWidget(Separator(alpha=60, dashed=True))
        col.addWidget(self.row_water)

        self.run_box = card
        return card

    @staticmethod
    def _spin(value: int, lo: int, hi: int, unit: str, accent: str,
              step: int = 5) -> ValuePill:
        return ValuePill(value, lo, hi, step, unit, accent)

    @staticmethod
    def _ghost(text: str, slot) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("Ghost")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(slot)
        return btn

    def _app_icon(self) -> QIcon:
        for name in ("images/logo.ico", "images/logo.png"):
            path = resource_path(name)
            if os.path.exists(path):
                return QIcon(path)
        return QIcon()

    def _build_toast(self) -> None:
        self.toast = Toast()

    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(self._app_icon(), self)
        self.tray.setToolTip(APP_NAME)
        self.tray.activated.connect(self._on_tray_activated)

        menu = QMenu(self)
        self._menu = menu                # 保持引用，避免菜单被回收
        self.act_show = menu.addAction("显示窗口", self._show_window)
        menu.addSeparator()
        self.act_toggle = menu.addAction("开始", self._tray_toggle)
        self.act_sip = menu.addAction("喝了一杯", lambda: self._log_sip())
        self.act_stand = menu.addAction("起身了", lambda: self._log_stand())
        menu.addSeparator()
        # 与主界面「结束」按钮等价：无需打开主窗口，右键悬浮球即可收尾并出报告。
        # 悬浮球与托盘共用此菜单，两处右键都会有这一项（槽函数内部已判 running）。
        self.act_stop = menu.addAction("结束", self._stop)
        # 用 lambda 包一层：addAction 会把 triggered 的 bool 传进第一个形参
        menu.addAction("今日清零", lambda: self._reset_today())
        menu.addSeparator()
        menu.addAction("退出", self._quit)
        self.tray.setContextMenu(menu)
        self.tray.show()

    def _build_floating(self) -> None:
        # 与托盘共用同一个 QMenu：菜单项的可用状态、文案和槽函数始终一致。
        self.floating = FloatingOrb(
            self._on_floating_primary, self._menu, self._on_orb_checkin)
        # 每次从托盘或悬浮球展开菜单前都重新同步，暂停时记录项必定禁用。
        self._menu.aboutToShow.connect(self._refresh_buttons)
        self.floating.show()

    def _on_orb_checkin(self, kind: str) -> Optional[str]:
        """悬浮球子球打卡：返回顶部胶囊文案，None 表示当前不可记录。

        记录走与按钮 / 托盘完全相同的函数，统计口径只有一处；胶囊本身就是
        回执，所以这里要抑制重复的浮层确认。
        """
        if not self.running or self.paused:
            return None
        if kind == "water":
            if not self._log_sip(quiet=True):
                return None
            ml, goal = self.settings.today_ml, max(1, self.settings.goal_ml)
            return f"+{self.settings.sip_ml}ml · 今日 {ml}/{goal}ml"
        if kind == "stand":
            if not self._log_stand(quiet=True):
                return None
            times = self.settings.today_stands
            goal = max(1, self.settings.goal_stands)
            return f"+1次 · 今日 {times}/{goal}次"
        return None

    def _on_floating_primary(self) -> None:
        """悬浮球单击：运行中暂停，暂停中继续；尚未开始时打开主窗口。"""
        if self.running:
            self._toggle_pause()
        else:
            self._show_window()

    def _update_floating_progress(self) -> None:
        if not self.running:
            self.floating.set_progress(1.0, 1.0, False)
            return
        now = self._elapsed()
        water = (self._next_water - now) / max(1, self._water_interval)
        sed = (self._next_sed - now) / max(1, self._sed_interval)
        self.floating.set_progress(water, sed, True)

    # ---------------------------- 状态切换 ---------------------------- #

    def _apply_mode(self, mode: str) -> None:
        idle = mode == "idle"
        self.setup_box.setVisible(idle)
        self.run_box.setVisible(not idle)
        self.actions.setVisible(not idle)
        self.layout().invalidate()
        self.layout().activate()
        self._refresh_buttons()

    def _on_main(self) -> None:
        """主按钮：待机时开始，运行中暂停/继续。"""
        if self.running:
            self._toggle_pause()
        else:
            self._start()

    def _refresh_buttons(self) -> None:
        if not self.running:
            self.main_btn.setText("开始计时")
            self.main_btn.set_icon_kind("play")
            self.main_btn.set_tone("blue")
        elif self.paused:
            self.main_btn.setText("继续计时")
            self.main_btn.set_icon_kind("play")
            self.main_btn.set_tone("gray")
        else:
            self.main_btn.setText("暂停提醒")
            self.main_btn.set_icon_kind("pause")
            self.main_btn.set_tone("orange")

        can_log = self.running and not self.paused
        self.sip_btn.setEnabled(can_log)
        self.stand_btn.setEnabled(can_log)

        if not self.running:
            self.act_toggle.setText("开始")
        else:
            self.act_toggle.setText("继续" if self.paused else "暂停")
        self.act_sip.setEnabled(can_log)
        self.act_stand.setEnabled(can_log)
        # 待机（未开始计时）时没有可结束的本次使用，禁用「结束」避免误点。
        self.act_stop.setEnabled(self.running)
        self.floating.set_paused(self.running and self.paused)
        # 暂停或待机时不该继续呼吸闪烁：提醒只在真正计时中才有意义。
        if not self.running or self.paused:
            self.floating.clear_alert()
        self._update_floating_progress()

    def _refresh_stats(self) -> None:
        if self.settings.roll_day():
            self.settings.save()
        self.rings.set_values(self.settings.today_ml, self.settings.today_stands,
                              self.settings.goal_ml, self.settings.goal_stands)

    def _preview_goals(self) -> None:
        """在设置页改目标时实时预览圆环，不必等到开始。"""
        self.rings.set_values(self.settings.today_ml, self.settings.today_stands,
                              self.goal_ml_spin.value(), self.goal_stand_spin.value())

    # ---------------------------- 窗口外观 ---------------------------- #

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        panel = QRectF(self.rect()).adjusted(SHADOW, SHADOW, -SHADOW, -SHADOW)

        p.setPen(Qt.NoPen)                        # 柔和投影：多层低透明度叠加
        for i in range(SHADOW, 0, -1):
            p.setBrush(QColor(16, 34, 62, 3))
            p.drawRoundedRect(
                panel.adjusted(-i, -i + 2, i, i + 3), RADIUS + i, RADIUS + i)

        p.setBrush(QColor(255, 255, 255, 246))    # 近白面板，衬得淡色分组卡更干净
        p.drawPath(rounded(panel, RADIUS))

        p.setBrush(Qt.NoBrush)                    # 内描边高光
        p.setPen(QPen(QColor(255, 255, 255, 170), 1))
        p.drawPath(rounded(panel.adjusted(0.5, 0.5, -0.5, -0.5), RADIUS - 0.5))

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        if hasattr(self, "controls"):
            self.controls.move(self.width() - SHADOW - 12 - self.controls.width(),
                               SHADOW + 13)
            self.controls.raise_()

    # ---- 无边框窗口：拖动 ----
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_from = e.globalPos() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if self._drag_from is not None and e.buttons() & Qt.LeftButton:
            self.move(e.globalPos() - self._drag_from)
            e.accept()

    def mouseReleaseEvent(self, e):
        self._drag_from = None
        super().mouseReleaseEvent(e)

    # ---------------------------- 计时核心 ---------------------------- #

    def _elapsed(self) -> float:
        """有效运行秒数（扣除暂停）。"""
        if not self.running:
            return 0.0
        secs = time.monotonic() - self._t0 - self._paused_total
        if self._paused_at is not None:
            secs -= time.monotonic() - self._paused_at
        return max(0.0, secs)

    @staticmethod
    def _advance(due: float, interval: float, now: float) -> float:
        """把已过期的到期点跳到下一个未来时刻，跳过所有漏掉的提醒（避免补发堆积）。"""
        if now < due:
            return due
        return due + interval * (1 + int((now - due) // interval))

    def _on_tick(self) -> None:
        if not self.running:
            return
        now = self._elapsed()
        self.row_sed.set_remain(int(self._next_sed - now), self._sed_interval, self.paused)
        self.row_water.set_remain(int(self._next_water - now), self._water_interval, self.paused)
        self._update_floating_progress()
        if self.paused:
            return

        due = []
        if now >= self._next_water:
            due.append("water")
            self._next_water = self._advance(self._next_water, self._water_interval, now)
        if now >= self._next_sed:
            due.append("sed")
            self._next_sed = self._advance(self._next_sed, self._sed_interval, now)

        # 悬浮球立即进入呼吸提醒态，不必等浮层排队；记录后由打卡流程清除。
        for kind in due:
            self.floating.set_alert("water" if kind == "water" else "stand")

        for i, kind in enumerate(due):
            if i == 0:
                self._remind(kind)
            else:                       # 同时到期时错开，避免互相覆盖
                self._queue(kind, TOAST_GAP_MS)

    # ---------------------------- 提醒 ---------------------------- #

    def _remind(self, kind: str) -> None:
        """到点提醒：若当前已有浮层，排队等它消失，避免叠加。"""
        if self.toast.isVisible():
            self._queue(kind, 800)
        else:
            self._show_toast(kind)

    def _show_toast(self, kind: str) -> None:
        if kind == "water":
            self.toast.notify("该喝水了",
                              f"每次 {self.settings.sip_ml} ml",
                              "喝了一杯", self._log_sip)
            log_event("remind_drink")
        else:
            self.toast.notify("起身活动一下",
                              f"已坐 {self._sed_interval // 60} 分钟",
                              "起身了", self._log_stand)
            log_event("remind_stand")

    def _confirm(self, title: str, sub: str) -> None:
        """操作回执：没有按钮，5 秒自动消失。

        从托盘右键记录时窗口是收起的，没有这条回执用户不知道到底记上没有。
        """
        self.toast.notify(title, sub)

    def _queue(self, kind: str, delay_ms: int) -> None:
        self._pending_kind = kind        # 只保留最新一条，绝不堆积
        if not self._pending_timer.isActive():
            self._pending_timer.start(delay_ms)

    def _flush_pending(self) -> None:
        if self._pending_kind is None:
            return
        if self.toast.isVisible():       # 上一条还没消失，稍后再弹
            self._pending_timer.start(800)
            return
        kind, self._pending_kind = self._pending_kind, None
        if self.running and not self.paused:
            self._show_toast(kind)

    # ---------------------------- 操作 ---------------------------- #

    def _start(self) -> None:
        self.settings.sed_min = self.sed_spin.value()
        self.settings.water_min = self.water_spin.value()
        self.settings.sip_ml = self.sip_spin.value()
        self.settings.goal_ml = self.goal_ml_spin.value()
        self.settings.goal_stands = self.goal_stand_spin.value()
        self.settings.roll_day()
        self.settings.save()
        self._refresh_stats()
        self._sed_interval = self.settings.sed_min * 60
        self._water_interval = self.settings.water_min * 60
        self._next_sed = float(self._sed_interval)
        self._next_water = float(self._water_interval)

        self._t0 = time.monotonic()
        self._paused_total = 0.0
        self._paused_at = None
        self.running = True
        self.paused = False

        # 新会话：清空本次记录
        self._session_start = datetime.now()
        self._drinks.clear()
        self._stands.clear()

        self._apply_mode("run")
        self.floating.clear_alert()
        self.row_sed.set_remain(self._sed_interval, self._sed_interval, False)
        self.row_water.set_remain(self._water_interval, self._water_interval, False)
        self._timer.start()
        log_event("start")

        # 开始后自动收进托盘，用浮层告知，避免窗口占地方
        self.hide()
        self.toast.notify(
            "已隐藏在后台",
            f"久坐 {self.settings.sed_min} 分 · 喝水 {self.settings.water_min} 分",
            "打开", self._show_window, duration_ms=3200)

    def _toggle_pause(self) -> None:
        if not self.running:
            self._start()
            return
        self.paused = not self.paused
        if self.paused:
            self._paused_at = time.monotonic()
            self._pending_timer.stop()
            self._pending_kind = None
            log_event("pause")
        else:
            if self._paused_at is not None:
                self._paused_total += time.monotonic() - self._paused_at
                self._paused_at = None
            log_event("resume")
        self._refresh_buttons()
        self._on_tick()

        # 暂停 / 继续都给一条回执：从托盘菜单点的时候窗口是收起的，
        # 没有这条提示就完全看不出操作有没有生效
        if self.paused:
            self._confirm("已暂停记录", "小助手记录仪已暂停，继续后接着计时")
        else:
            self._confirm("已继续记录", "接着上次的进度继续计时")

    def _stop(self) -> None:
        if not self.running:
            return
        active = self._elapsed()
        self._timer.stop()
        self._pending_timer.stop()
        self._pending_kind = None
        self.toast.dismiss()
        self.running = False
        self.paused = False
        self._paused_at = None
        self.floating.clear_alert()
        log_event("stop")
        self._apply_mode("idle")

        # 报告先写：里面要带上本次结束前的累计数据
        path = self._write_report(active)
        # 本次使用到此结束 → 当日累计清零，下次启动从零开始
        self._reset_today(notify=False)
        self._show_window()

        if path is not None:
            try:
                webbrowser.open(path.as_uri())
            except Exception:
                self.tray.showMessage(APP_NAME, f"报告已保存：{path}",
                                      QSystemTrayIcon.Information, 4000)

    def _reset_today(self, notify: bool = True) -> None:
        """清空当日累计（饮水 / 起身），让下一次使用从零开始。"""
        self.settings.today_ml = 0
        self.settings.today_sips = 0
        self.settings.today_stands = 0
        self.settings.save()
        self._drinks.clear()
        self._stands.clear()
        self._refresh_stats()
        log_event("reset")
        if notify:
            self.tray.showMessage(APP_NAME, "今日记录已清零，可以重新开始",
                                  QSystemTrayIcon.Information, 2500)

    def _log_sip(self, quiet: bool = False) -> bool:
        """记录一次饮水，重置喝水倒计时。quiet=True 时不弹浮层回执。"""
        if not self.running or self.paused:
            return False
        self.settings.roll_day()
        self.settings.today_ml += self.settings.sip_ml
        self.settings.today_sips += 1
        self.settings.save()
        self._next_water = self._elapsed() + self._water_interval
        self._drinks.append((datetime.now(), self._elapsed()))
        self._refresh_stats()
        log_event("drink")
        # 任何入口（按钮 / 托盘 / 浮层 / 悬浮球）记录后都要结束呼吸提醒。
        self.floating.clear_alert("water")
        if not quiet:
            self._confirm("已记录喝水",
                          f"今日已饮水 {self.settings.today_ml} ml"
                          f"（{self.settings.today_sips} 次）")
        self._update_floating_progress()
        self.floating.feedback("drop")
        return True

    def _log_stand(self, quiet: bool = False) -> bool:
        """记录一次起身，重置久坐倒计时。quiet=True 时不弹浮层回执。"""
        if not self.running or self.paused:
            return False
        self.settings.roll_day()
        self.settings.today_stands += 1
        self.settings.save()
        self._next_sed = self._elapsed() + self._sed_interval
        self._stands.append((datetime.now(), self._elapsed()))
        self._refresh_stats()
        log_event("stand")
        self.floating.clear_alert("stand")
        if not quiet:
            self._confirm("已记录起身",
                          f"今日已起身活动 {self.settings.today_stands} 次")
        self._update_floating_progress()
        self.floating.feedback("person")
        return True

    # ---------------------------- 报告 ---------------------------- #

    def _write_report(self, active: float) -> Optional[Path]:
        """生成一页纯 HTML 文本报告（无图片依赖），返回文件路径。"""
        s = self.settings
        start = self._session_start or datetime.now()
        end = datetime.now()
        drinks, stands = self._drinks, self._stands

        # 久坐间隔：以会话起点为 0，活动记录之间为间隔
        marks = [0.0] + [e for _, e in stands] + [active]
        gaps = [b - a for a, b in zip(marks, marks[1:])]
        longest = max(gaps) if gaps else active
        avg_drink = active / len(drinks) if drinks else 0.0
        avg_stand = active / len(stands) if stands else 0.0

        rows = []
        for dt, _ in drinks:
            rows.append((dt, "blue", "喝了一杯", f"{s.sip_ml} ml"))
        for dt, _ in stands:
            rows.append((dt, "amber", "起身了", ""))
        rows.sort(key=lambda r: r[0])

        events = "\n".join(
            f'<tr><td class="t">{dt:%H:%M}</td>'
            f'<td><span class="dot {cls}"></span>{name}</td>'
            f'<td class="n">{note}</td></tr>'
            for dt, cls, name, note in rows
        ) or '<tr><td class="t">—</td><td>本次没有记录</td><td class="n"></td></tr>'

        def row(k: str, v: str) -> str:
            return f'<tr><td class="t">{k}</td><td class="val">{v}</td></tr>'

        detail = "".join([
            row("开始", f"{start:%H:%M}"),
            row("结束", f"{end:%H:%M}"),
            row("暂停", fmt_hm(self._paused_total) if self._paused_total >= 60 else "不足 1 分"),
            row("平均饮水间隔", fmt_hm(avg_drink) if avg_drink else "—"),
            row("平均起身间隔", fmt_hm(avg_stand) if avg_stand else "—"),
            row("最长久坐", fmt_hm(longest)),
        ])

        html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>健康报告 {end:%Y-%m-%d}</title>
<style>{REPORT_CSS}</style>
</head>
<body>
<div class="wrap">
  <h1>健康报告</h1>
  <div class="meta">{end:%Y年%m月%d日} · {start:%H:%M} — {end:%H:%M}</div>

  <div class="grid">
    <div class="card"><div class="k">有效时长</div>
      <div class="v">{fmt_hm_big(active)}</div></div>
    <div class="card"><div class="k">饮水</div>
      <div class="v">{len(drinks) * s.sip_ml}<small>ml</small></div></div>
    <div class="card"><div class="k">起身</div>
      <div class="v">{len(stands)}<small>次</small></div></div>
  </div>

  <h2>本次明细</h2>
  <div class="panel"><table>{detail}</table></div>

  <h2>记录</h2>
  <div class="panel"><table>{events}</table></div>

  <div class="foot">今日累计饮水 {s.today_ml} ml（{s.today_sips} 次）· 起身 {s.today_stands} 次
  · 生成于 {end:%H:%M}</div>
</div>
</body>
</html>
"""
        try:
            REPORT_DIR.mkdir(parents=True, exist_ok=True)
            path = REPORT_DIR / f"健康报告_{end:%Y%m%d_%H%M}.html"
            path.write_text(html, encoding="utf-8")
            return path
        except OSError:
            return None

    # ---------------------------- 托盘 ---------------------------- #

    def _tray_toggle(self) -> None:
        if self.running:
            self._toggle_pause()
        else:
            self._start()

    def _on_tray_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger):
            self._show_window()

    def _show_window(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def _quit(self) -> None:
        # 直接退出也视为本次使用结束：清空当日累计，下次打开从零开始
        self._reset_today(notify=False)
        self.toast.hide()
        self.tray.hide()
        self.floating.close()
        QApplication.quit()

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()
        if not self._tray_hinted:
            self._tray_hinted = True
            self.tray.showMessage(APP_NAME, "已最小化到托盘，双击图标可恢复。",
                                  QSystemTrayIcon.Information, 2000)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.setFocus()      # 焦点留在窗口上，避免启动时输入框出现蓝色光标


# ------------------------------ 入口 ------------------------------ #

def main() -> None:
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)
    app.setWindowIcon(QIcon(resource_path("images/logo.ico")))

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

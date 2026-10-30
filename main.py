# -*- coding: utf-8 -*-
"""久坐 · 喝水提醒 —— 极简久坐 / 喝水提醒

单文件 PyQt5 应用，仅依赖 PyQt5。

运行：  python main.py
打包：  pyinstaller --noconfirm --windowed --icon images/logo.ico main.py
"""

from __future__ import annotations

import csv
import json
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
)
from PyQt5.QtGui import (
    QBrush, QColor, QCursor, QFont, QFontMetrics, QIcon, QLinearGradient,
    QPainter, QPainterPath, QPen, QPixmap, QPolygonF,
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
        self.sip_btn = self._ghost("喝了一杯", self._log_sip)
        self.stand_btn = self._ghost("起身了", self._log_stand)
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
        self.act_sip = menu.addAction("喝了一杯", self._log_sip)
        self.act_stand = menu.addAction("起身了", self._log_stand)
        # 用 lambda 包一层：addAction 会把 triggered 的 bool 传进第一个形参
        menu.addAction("今日清零", lambda: self._reset_today())
        menu.addSeparator()
        menu.addAction("退出", self._quit)
        self.tray.setContextMenu(menu)
        self.tray.show()

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
        if self.paused:
            return

        due = []
        if now >= self._next_water:
            due.append("water")
            self._next_water = self._advance(self._next_water, self._water_interval, now)
        if now >= self._next_sed:
            due.append("sed")
            self._next_sed = self._advance(self._next_sed, self._sed_interval, now)

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

    def _log_sip(self) -> None:
        if not self.running or self.paused:
            return
        self.settings.roll_day()
        self.settings.today_ml += self.settings.sip_ml
        self.settings.today_sips += 1
        self.settings.save()
        self._next_water = self._elapsed() + self._water_interval
        self._drinks.append((datetime.now(), self._elapsed()))
        self._refresh_stats()
        log_event("drink")
        self._confirm("已记录喝水",
                      f"今日已饮水 {self.settings.today_ml} ml"
                      f"（{self.settings.today_sips} 次）")

    def _log_stand(self) -> None:
        if not self.running or self.paused:
            return
        self.settings.roll_day()
        self.settings.today_stands += 1
        self.settings.save()
        self._next_sed = self._elapsed() + self._sed_interval
        self._stands.append((datetime.now(), self._elapsed()))
        self._refresh_stats()
        log_event("stand")
        self._confirm("已记录起身",
                      f"今日已起身活动 {self.settings.today_stands} 次")

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

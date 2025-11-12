import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QIcon, QPixmap, QMovie
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QSpinBox, QComboBox, QPushButton, QProgressBar, QDialog,
    QMessageBox, QSystemTrayIcon, QMenu, QScrollArea, QSizePolicy,
    QGroupBox,      # <-- add this
)


# ----------------------------- Constants ----------------------------- #
APP_NAME = "健康生活小助手"
APP_DIR = Path(os.getenv("APPDATA", Path.home())) / "HealthyLifeAssistant"
SETTINGS_PATH = APP_DIR / "settings.json"

LANG_EN, LANG_ZH = "EN", "ZH"
DEBUG_TEST_BUTTONS = False

INTERVALS: Dict[str, List[Tuple[int, str]]] = {
    LANG_EN: [(45, "45 Min"), (60, "1 Hour"), (75, "1 Hour 15 Min"), (90, "1 Hour 30 Min")],
    LANG_ZH: [(45, "45分钟"), (60, "1小时"), (75, "1小时15分"), (90, "1小时30分")],
}

STYLE_QSS = """
    QWidget { font-family: 'Microsoft YaHei','PingFang SC','Segoe UI',sans-serif; font-size: 12pt; }
    QMainWindow { background: #f7fbff; }
    #AppTitle { font-size: 18pt; font-weight: 1000; color: #1b273a; padding: 6px 0 2px 0; }

    /* 卡片基础 */
    QGroupBox { background:#fff; border:1px solid #e5eaf1; border-radius:12px; margin-top:14px; padding:14px; }
    /* 外部标题 */
    #SectionTitleBlue  { font-size:14pt; font-weight:800; color:#000000; padding:6px 2px 2px; }
    #SectionTitleGreen { font-size:14pt; font-weight:800; color:#15803d; padding:6px 2px 2px; }
    #SectionTitleGray  { font-size:14pt; font-weight:800; color:#334155; padding:6px 2px 2px; }

    /* 主题卡片 */
    #CardBlue  { background:#f0f6ff; border:1px solid #d7e3ff; border-left:5px solid #3b82f6; }
    #CardGreen { background:#ecfdf5; border:1px solid #a7f3d0; border-left:5px solid #10b981; }
    #CardGray  { background:#f8fafc; border:1px solid #e2e8f0; border-left:5px solid #64748b; }

    QPushButton { padding:8px 14px; border-radius:10px; background:#2b5aa6; color:#fff; border:0; }
    QPushButton:hover { background:#3a6edc; }
    QPushButton:disabled { background:#aab7c4; }
    QProgressBar { height:16px; border:1px solid #c9d6ea; border-radius:8px; text-align:center; background:#eef4ff; }
    QProgressBar::chunk { border-radius:8px; background-color:#4aa3ff; }
    QLabel { color:#1b273a; }

    #NoteLabel { color:#334155; font-weight:600; padding:2px 0 4px; }
"""

TRANSLATIONS = {
    LANG_EN: {
        "app_name": "Healthy Life Assistant — Hydration & Anti-sedentary",
        "title": "Health Reminder",
        "reco_title": "Daily Water Intake Recommendation",
        "reco_text": (
            "In general conditions, the Chinese Dietary Guidelines (2022) suggest "
            "about <b>1700 ml</b> per day for adult men and <b>1500 ml</b> for adult women. "
            'See details: <a href="http://dg.cnsoc.org/article/04/wDCyy7cWSJCN6pwKHOo5Dw.html">Chinese Dietary Guidelines (2022)</a>'
        ),
        "sed_title": "Why Break Up Sitting",
        "sed_text": (
            "<ul>"
            "<li><b>Vascular/Cardio</b>: Standing up every 60 min can improve endothelial function and lower CVD risk.</li>"
            "<li><b>Spine/Muscles</b>: Brief hourly movement reduces neck and low-back discomfort.</li>"
            "<li><b>Metabolism</b>: ~6 min of light activity each hour helps lower post-meal glucose and insulin.</li>"
            "</ul>"
        ),
        "settings_title": "Health Settings",
        "settings_hint": (
            "Enter your daily water goal and sip size, choose the break interval, then click “Start”. "
            "Closing the window hides it to the tray; to fully exit, right-click the tray icon and choose “Quit”."
        ),
        "progress_section": "Progress",
        "water_goal": "Daily Water Goal (ml)",
        "sip_size": "Sip Size (ml)",
        "interval": "Sedentary Break Interval",
        "start": "Start", "pause": "Pause", "resume": "Resume", "log_sip": "Log Sip",
        "hydrate_time": "Hydration Time!", "move_break": "Move Break!",
        "progress": "You've drank {}/{} ml",
        "log_move": "Log Activity",
        "move_msg": "Stand up and stretch — good for blood flow and spine!",
        "language": "Language", "show": "Show", "quit": "Quit",
        "started": "Reminders started.", "paused": "Reminders paused.", "resumed": "Reminders resumed.",
        "goal_done": "Goal Achieved!", "reset_title": "Reset", "reset_msg": "Defaults applied.",
        "tray_tooltip": "Health Reminder",
        "elapsed_desc": "Elapsed Time",
        "water_log_desc": "Water Log",
        "activity_log_desc": "Activity Log",
        "activity_count_fmt": "x{}",  # 显示为 x1, x2...
        "finish_day": "End Day",
        "report_title": "Daily Health Report",
        "report_saved": "Report saved to:\n{}",
    },
    LANG_ZH: {
        "app_name": "健康生活小助手：提醒喝水·避免久坐",
        "title": "健康生活小助手",
        "reco_title": "每日饮水",
        "reco_text": (
            '<a href="http://dg.cnsoc.org/article/04/wDCyy7cWSJCN6pwKHOo5Dw.html">中国居民膳食指南（2022）</a>建议，在一般情况下，'
            "成年男性每天应饮水约<b>1700毫升</b>，成年女性每天应饮水约<b>1500毫升</b>。"
            "健康的饮水频率应以<b>少量多次</b>为原则，尽量均匀分布在一天中。"
        ),
        "sed_title": "避免久坐",
        "sed_text": (
            "<ul>"
            "<li><b>心血管</b>：长时间久坐与更高的心血管事件和全因死亡风险相关；在日常里把久坐切成更短的时段并起身活动，有助于心血管健康。</li>"
            "<li><b>腰痛/颈痛</b>：定时活动可减轻颈背/腰背僵硬与不适，改善久坐姿势带来的肌骨负担。</li>"
            "<li><b>代谢</b>：用短暂的站立或活动打断久坐（例如每30-60分钟活动1–2分钟），能显著降低餐后血糖与胰岛素反应，改善三酰甘油等代谢指标。</li>"
            "<li><b>如何做</b>：尽量“多动少坐”，把每次坐着的时间缩短，工作或学习时每30–60分钟安排一次 1–2 分钟的起身走动、伸展或轻活动。</li>"
            "</ul>"
            ),
        "settings_title": "健康设定",
        "settings_hint": (
            "使用指南："
            "<ul>"
            "<li><b>设定饮水</b>：根据水杯容量设置「每次饮水量」，再设置「每日饮水目标」。</li>"
            "<li><b>设定久坐提醒</b>：设置久坐提醒间隔（<u>喝水提醒固定为 1.5 小时</u>）。</li>"
            "<li><b>点击“开始”</b>：开始计时并锁定以上设置；<u>若需修改请先点“重置”</u>。</li>"
            "<li><b>暂停/继续</b>：临时离开可点“暂停”，返回后点“继续”恢复，暂停时计时与提醒均停止。</li>"
            "<li><b>最小化到托盘</b>：关闭窗口只会隐藏到托盘，不会退出；右键托盘可 显示/暂停/记录一口/退出。</li>"
            "<li><b>弹窗提醒</b>：喝水弹窗持续<b>5秒</b>，久坐弹窗持续<b>7秒</b>；可手动关闭，也可等待自动消失。</li>"
            "<li><b>日常记录</b>：点“记录一口”增加饮水；点“记录活动”累计一次起身活动。</li>"
            "<li><b>结束/下班</b>：点击后生成当日健康报告（含用时、饮水与活动统计），可保存本地。</li>"
            "</ul>"
        ),
        "progress_section": "进度",
        "water_goal": "每日饮水目标 (ml)",
        "sip_size": "每次饮水量 (ml)",
        "interval": "久坐提醒间隔",
        "start": "开始", "pause": "暂停", "resume": "继续", "log_sip": "记录一口",
        "hydrate_time": "喝水时间！", "move_break": "动一动！",
        "progress": "已饮 {}/{} ml",
        "log_move": "记录活动",
        "move_msg": "来活动活动！",
        "language": "语言", "show": "显示主界面", "quit": "退出",
        "started": "提醒已启动。", "paused": "提醒已暂停。", "resumed": "提醒已继续。",
        "goal_done": "目标达成！", "reset_title": "重置", "reset_msg": "欢迎使用健康小助手，默认设置已应用。",
        "tray_tooltip": "健康提醒",
        "elapsed_desc": "已运行时间",
        "water_log_desc": "饮水记录",
        "activity_log_desc": "活动记录",
        "activity_count_fmt": "{} 次",  # 显示为 1 次, 2 次...
        "finish_day": "结束/下班",
        "report_title": "当日健康活动报告",
        "report_saved": "报告已保存到：\n{}",
    },
}

def t(lang: str, key: str) -> str:
    return TRANSLATIONS.get(lang, TRANSLATIONS[LANG_EN]).get(key, key)

def resource_path(rel_path: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel_path)

# ----------------------------- Settings ----------------------------- #
@dataclass
class Settings:
    goal: int = 1700
    sip_size: int = 250
    interval_min: int = 60
    water_progress: int = 0
    last_reset: str = str(datetime.now().date())
    language: str = LANG_ZH

    @staticmethod
    def load() -> "Settings":
        APP_DIR.mkdir(parents=True, exist_ok=True)
        s = Settings()      # 始终使用默认（保持你“每次启动即默认”的行为）
        s.save()
        return s

    def save(self) -> None:
        SETTINGS_PATH.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")

# ----------------------------- Main Window ----------------------------- #
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings.load()
        self.running = False
        self.paused = False

        self.paused_at = None            # type: Optional[datetime]
        self.water_times = []   # 记录每次“记录一口”的时间戳
        self.move_times  = []   # 记录每次“记录活动”的时间戳

        self.paused_accum = 0.0          # 累积暂停秒数（float）


        self.setWindowTitle(t(self.settings.language, "title"))
        self.resize(1600, 1200)
        self.setMinimumSize(1000, 650)

        # center -> scroll
        scroll = QScrollArea(self); scroll.setWidgetResizable(True)
        page = QWidget(); scroll.setWidget(page)
        self.setCentralWidget(scroll)
        self.outer = QVBoxLayout(page)
        self.outer.setContentsMargins(16, 16, 16, 16)
        self.outer.setSpacing(12)

        self.build_header()
        self.build_reco()
        self.build_sedentary()
        self.build_form()
        self.build_progress()
        self.build_controls()
        self.build_tray()

        QMessageBox.information(self, t(self.settings.language, "reset_title"), t(self.settings.language, "reset_msg"))
        QApplication.setQuitOnLastWindowClosed(False)

    # ---------- UI builders ----------
    def build_header(self):
        row = QHBoxLayout()

        # --- logo ---
        logo = QLabel()
        pix = QPixmap(resource_path("images/logo.png"))
        logo_h = 100
        if not pix.isNull():
            pix = pix.scaledToHeight(logo_h, Qt.SmoothTransformation)
            logo.setPixmap(pix)
            logo_h = pix.height()
        logo.setFixedSize(logo_h, logo_h)          # 正方形区域，便于对齐
        logo.setAlignment(Qt.AlignCenter)
        row.addWidget(logo)

        row.addSpacing(12)

        # --- 标题区域：高度=logo，高度内垂直居中 ---
        self.title_label = QLabel()
        self.title_label.setObjectName("AppTitle")
        self.title_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        title_wrap = QWidget()
        title_wrap.setFixedHeight(logo_h)
        tw = QVBoxLayout(title_wrap)
        tw.setContentsMargins(0, 0, 0, 0)
        tw.addStretch(1)
        tw.addWidget(self.title_label, alignment=Qt.AlignVCenter | Qt.AlignLeft)
        tw.addStretch(1)

        # 让标题区在行里可扩展
        title_wrap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row.addWidget(title_wrap, 1)

        # --- 语言下拉，放最右侧，顶端或居中都可选 ---
        self.lang_box = QComboBox()
        self.lang_box.addItems(["English", "中文"])
        self.lang_box.setCurrentIndex(1 if self.settings.language == LANG_ZH else 0)
        self.lang_box.currentIndexChanged.connect(self.on_lang_change)

        lang_wrap = QWidget()
        lw = QVBoxLayout(lang_wrap)
        lw.setContentsMargins(0, 0, 0, 0)
        # 选一个你喜欢的垂直位置：
        # 顶端：不加 stretch； 居中：上下各加一个 stretch；底部：上面加一个 stretch
        lw.addStretch(1)              # 注释掉这两行可改为顶端
        lw.addWidget(self.lang_box, alignment=Qt.AlignRight)
        lw.addStretch(1)

        row.addWidget(lang_wrap, 0, Qt.AlignRight)

        self.outer.addLayout(row)


    def build_reco(self):
        self.reco_title = QLabel(); self.reco_title.setObjectName("SectionTitleBlue"); self.outer.addWidget(self.reco_title)
        self.reco_card = QGroupBox(); self.reco_card.setObjectName("CardBlue")
        v = QVBoxLayout(self.reco_card)
        self.reco_label = QLabel(); self.reco_label.setTextFormat(Qt.RichText); self.reco_label.setOpenExternalLinks(True); self.reco_label.setWordWrap(True)
        v.addWidget(self.reco_label)
        self.outer.addWidget(self.reco_card)

    def build_sedentary(self):
        self.sed_title = QLabel(); self.sed_title.setObjectName("SectionTitleBlue"); self.outer.addWidget(self.sed_title)
        self.sed_card = QGroupBox(); self.sed_card.setObjectName("CardBlue")
        v = QVBoxLayout(self.sed_card)
        self.sed_label = QLabel(); self.sed_label.setTextFormat(Qt.RichText); self.sed_label.setWordWrap(True)
        v.addWidget(self.sed_label)
        self.outer.addWidget(self.sed_card)

    def build_form(self):
        self.form_title = QLabel(); self.form_title.setObjectName("SectionTitleGreen"); self.outer.addWidget(self.form_title)
        self.form_card = QGroupBox(); self.form_card.setObjectName("CardGreen")
        box = QVBoxLayout(self.form_card)
        form = QFormLayout(); box.addLayout(form)

        self.settings_hint = QLabel(); self.settings_hint.setWordWrap(True)
        form.addRow(self.settings_hint)

        self.goal_spin = QSpinBox(); self.goal_spin.setRange(1500, 3000); self.goal_spin.setSingleStep(100)
        self.sip_spin  = QSpinBox(); self.sip_spin.setRange(50, 1000); self.sip_spin.setSingleStep(50)
        self.interval_box = QComboBox()

        self.lbl_goal = QLabel(); self.lbl_sip = QLabel(); self.lbl_intv = QLabel()
        form.addRow(self.lbl_goal, self.goal_spin)
        form.addRow(self.lbl_sip,  self.sip_spin)
        form.addRow(self.lbl_intv, self.interval_box)

        self.outer.addWidget(self.form_card)

    def build_progress(self):
        self.prog_title = QLabel(); self.prog_title.setObjectName("SectionTitleGray"); self.outer.addWidget(self.prog_title)
        self.prog_card = QGroupBox(); self.prog_card.setObjectName("CardGray")
        v = QVBoxLayout(self.prog_card)
        # ① 计时说明 + 时间
        self.elapsed_desc = QLabel()                 # ← 新增
        self.elapsed_desc.setObjectName("NoteLabel") # ← 可选样式
        v.addWidget(self.elapsed_desc)
        self.elapsed_label = QLabel("00:00:00")
        v.addWidget(self.elapsed_label)

        # ② 饮水记录说明 + 文本 + 进度条
        self.water_log_desc = QLabel()               # ← 新增
        self.water_log_desc.setObjectName("NoteLabel")
        v.addWidget(self.water_log_desc)
        self.progress_label = QLabel()
        self.progress_bar = QProgressBar()
        v.addWidget(self.progress_label); v.addWidget(self.progress_bar)

         # ③ 活动记录说明 + 计数 + GIF 列
        self.activity_log_desc = QLabel()            # ← 新增
        self.activity_log_desc.setObjectName("NoteLabel")
        v.addWidget(self.activity_log_desc)

        hdr = QHBoxLayout()                          # ← 计数行（在 GIF 前）
        self.move_count = 0                          # ← 计数器
        self.move_count_label = QLabel("0")
        hdr.addWidget(self.move_count_label)
        hdr.addStretch(1)
        v.addLayout(hdr)
        # 进度条下面一行放“活动小图标”
        self.moves_row = QHBoxLayout()
        self.moves_row.setSpacing(6)
        self.moves_row.setContentsMargins(0, 6, 0, 0)
        moves_wrap = QWidget(); moves_wrap.setLayout(self.moves_row)
        v.addWidget(moves_wrap)
        self.move_icons = []  # [(QLabel, QMovie), ...]

        self.outer.addWidget(self.prog_card)

        self.start_time = None
        self.elapsed_timer = QTimer(self); self.elapsed_timer.timeout.connect(self._tick_elapsed)

    def build_controls(self):
        row = QHBoxLayout()
        self.reset_btn = QPushButton(); self.reset_btn.clicked.connect(self.reset_form)
        self.start_btn = QPushButton(); self.start_btn.clicked.connect(self.start_reminders)
        self.pause_btn = QPushButton(); self.pause_btn.clicked.connect(self.toggle_pause); self.pause_btn.setEnabled(False)
        self.log_btn = QPushButton(); self.log_btn.clicked.connect(self.log_sip); self.log_btn.setEnabled(False)
        self.log_move_btn = QPushButton()
        self.log_move_btn.clicked.connect(self.log_move)
        self.log_move_btn.setEnabled(False)
        self.finish_btn = QPushButton()
        self.finish_btn.setText(t(self.settings.language, "finish_day"))
        self.finish_btn.clicked.connect(self.finish_and_report)
        self.finish_btn.setEnabled(False)  # 未开始前禁用
        row.addWidget(self.finish_btn)
        row.addWidget(self.log_move_btn)
        row.addWidget(self.reset_btn); row.addWidget(self.start_btn); row.addWidget(self.pause_btn); row.addWidget(self.log_btn)
        self.outer.addLayout(row)
        if DEBUG_TEST_BUTTONS:
            test_row = QHBoxLayout()
            self.test_water_btn = QPushButton(t(self.settings.language, "test_water"))
            self.test_water_btn.clicked.connect(self.water_reminder)
            self.test_sit_btn = QPushButton(t(self.settings.language, "test_sit"))
            self.test_sit_btn.clicked.connect(self.sedentary_reminder)
            test_row.addWidget(self.test_water_btn)
            test_row.addWidget(self.test_sit_btn)
            self.outer.addLayout(test_row)


    def build_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(QIcon(resource_path("images/logo.png")))
        self.tray.setToolTip(t(self.settings.language, "tray_tooltip"))
        self._rebuild_tray_menu()
        self.tray.show()

        self.water_timer = QTimer(self); self.water_timer.timeout.connect(self.water_reminder)
        self.sedentary_timer = QTimer(self); self.sedentary_timer.timeout.connect(self.sedentary_reminder)

        # 初始值赋入
        self.goal_spin.setValue(self.settings.goal)
        self.sip_spin.setValue(self.settings.sip_size)
        self.apply_texts()

    # ---------- Texts / Language ----------
    def apply_texts(self):
        lang = self.settings.language
        self.setWindowTitle(t(lang, "title"))
        self.title_label.setText(t(lang, "app_name"))
        # self.lang_label.setText(t(lang, "language"))

        self.reco_title.setText("💧 " + t(lang, "reco_title"))        # 每日饮水
        self.reco_label.setText(t(lang, "reco_text"))
        self.sed_title.setText("🪑 " + t(lang, "sed_title"))          # 避免久坐
        self.sed_label.setText(t(lang, "sed_text"))
        self.form_title.setText("⚙️ " + t(lang, "settings_title"))     # 健康设定
        self.settings_hint.setText(t(lang, "settings_hint"))
        self.prog_title.setText("📊 " + t(lang, "progress_section"))  # 进度
        self.log_move_btn.setText(t(lang, "log_move"))

        self.lbl_goal.setText(t(lang, "water_goal"))
        self.lbl_sip.setText(t(lang, "sip_size"))
        self.lbl_intv.setText(t(lang, "interval"))

        # 说明文字（双语）
        self.elapsed_desc.setText("⏱️ " + t(lang, "elapsed_desc"))
        self.water_log_desc.setText("💦 " + t(lang, "water_log_desc"))
        self.activity_log_desc.setText("🚶 " + t(lang, "activity_log_desc"))
        # 计数字样
        self.move_count_label.setText(t(lang, "activity_count_fmt").format(self.move_count))

        # interval items
        self.interval_box.blockSignals(True)
        self.interval_box.clear()
        for _, label in INTERVALS[lang]:
            self.interval_box.addItem(label)
        self.interval_box.blockSignals(False)
        # 保持当前分钟选项
        self.set_interval_minutes(self.settings.interval_min)

        # buttons
        self.reset_btn.setText(t(lang, "reset_title"))
        self.start_btn.setText(t(lang, "start") if not self.running else t(lang, "started"))
        self.pause_btn.setText(t(lang, "pause") if not self.paused else t(lang, "resume"))
        self.log_btn.setText(t(lang, "log_sip"))
        self.tray.setToolTip(t(lang, "tray_tooltip"))

        self._update_progress_bar()
        self.finish_btn.setText(t(lang, "finish_day"))


    def on_lang_change(self, idx: int):
        self.settings.language = LANG_ZH if idx == 1 else LANG_EN
        self.apply_texts()
        self._rebuild_tray_menu()
        self.settings.save()

    # ---------- Helpers ----------
    def get_interval_minutes(self) -> int:
        # 根据当前语言和索引拿分钟
        idx = self.interval_box.currentIndex()
        pairs = INTERVALS[self.settings.language]
        return pairs[idx][0] if 0 <= idx < len(pairs) else 60

    def set_interval_minutes(self, minutes: int) -> None:
        pairs = INTERVALS[self.settings.language]
        for i, (m, _) in enumerate(pairs):
            if m == minutes:
                self.interval_box.setCurrentIndex(i); return
        self.interval_box.setCurrentIndex(1)  # 默认 60

    def _progress_text(self) -> str:
        return t(self.settings.language, "progress").format(self.settings.water_progress, self.settings.goal)

    def _update_progress_bar(self):
        pct = int(round((self.settings.water_progress / max(1, self.settings.goal)) * 100))
        self.progress_bar.setValue(max(0, min(100, pct)))
        self.progress_label.setText(self._progress_text())

    def _set_inputs_enabled(self, enabled: bool):
        self.goal_spin.setEnabled(enabled)
        self.sip_spin.setEnabled(enabled)
        self.interval_box.setEnabled(enabled)

    def _tick_elapsed(self):
        if self.start_time is None:
            return
        now = datetime.now()
        secs = (now - self.start_time).total_seconds() - float(self.paused_accum)
        if self.paused_at is not None:
            # 正在暂停中，把当前这段暂停也扣掉
            secs -= (now - self.paused_at).total_seconds()
        secs = max(0.0, secs)
        h, rem = divmod(int(secs), 3600)
        m, s = divmod(rem, 60)
        self.elapsed_label.setText(f"{h:02d}:{m:02d}:{s:02d}")


    def _rebuild_tray_menu(self):
        menu = QMenu()
        act_show = menu.addAction(t(self.settings.language, "show"));  act_show.triggered.connect(self._show_normal)
        self.act_pause_resume = menu.addAction(t(self.settings.language, "pause")); self.act_pause_resume.triggered.connect(self.toggle_pause)
        act_quit = menu.addAction(t(self.settings.language, "quit"));  act_quit.triggered.connect(lambda: QApplication.instance().quit())
        self.tray.setContextMenu(menu)

    def _show_normal(self):
        self.show(); self.raise_(); self.activateWindow()

    def _elapsed_seconds_now(self) -> float:
        """返回当前累计运行秒数（扣除暂停），与你的计时显示一致。"""
        if self.start_time is None:
            return 0.0
        now = datetime.now()
        secs = (now - self.start_time).total_seconds() - float(self.paused_accum)
        if self.paused_at is not None:
            secs -= (now - self.paused_at).total_seconds()
        return max(0.0, secs)

    @staticmethod
    def _fmt_hm_lang(secs: float, lang: str) -> str:
        """把秒格式化成“x小时x分钟”（中文）或“xh ymin”（英文）"""
        secs = int(max(0, secs))
        h, rem = divmod(secs, 3600)
        m, _ = divmod(rem, 60)
        if lang == LANG_ZH:
            return f"{h}小时{m}分钟"
        else:
            return f"{h}h {m}min"

    # ---------- Actions ----------
    def start_reminders(self):
        self.settings.goal = self.goal_spin.value()
        self.settings.sip_size = self.sip_spin.value()
        self.settings.interval_min = self.get_interval_minutes()
        self.settings.water_progress = 0
        self.settings.last_reset = str(datetime.now().date())
        self.settings.save()

        self.paused_at = None
        self.paused_accum = 0.0
        self.start_time = datetime.now()
        self.elapsed_label.setText("00:00:00")
        self.elapsed_timer.start(1000)

        self.running = True; self.paused = False
        self.start_btn.setEnabled(False); self.pause_btn.setEnabled(True); self.log_btn.setEnabled(True)
        self.pause_btn.setText(t(self.settings.language, "pause"))
        self.act_pause_resume.setText(t(self.settings.language, "pause"))

        self._set_inputs_enabled(False)
        self._update_progress_bar()

        self.water_timer.start(int(1.5 * 60 * 60 * 1000))                 # 1.5h
        self.sedentary_timer.start(self.settings.interval_min * 60 * 1000)

        self.tray.showMessage(t(self.settings.language, "tray_tooltip"), t(self.settings.language, "started"), QSystemTrayIcon.Information, 2000)
        self.water_reminder()  # 第一次就弹一次
        self.log_move_btn.setEnabled(True)
        self.finish_btn.setEnabled(True)


    def toggle_pause(self):
        if not self.running:
            return
        self.paused = not self.paused
        if self.paused:
            # 进入暂停：停止计时器，记录暂停起点
            self.water_timer.stop()
            self.sedentary_timer.stop()
            self.elapsed_timer.stop()
            self.paused_at = datetime.now()
            self.pause_btn.setText(t(self.settings.language, "resume"))
            self.act_pause_resume.setText(t(self.settings.language, "resume"))
            self.tray.showMessage(t(self.settings.language, "tray_tooltip"),
                                t(self.settings.language, "paused"),
                                QSystemTrayIcon.Information, 1500)
        else:
            # 结束暂停：把这段暂停时间纳入累计
            if self.paused_at is not None:
                self.paused_accum += (datetime.now() - self.paused_at).total_seconds()
                self.paused_at = None
            # 重新启动计时器
            self.water_timer.start(int(1.5 * 60 * 60 * 1000))      # 固定 1.5h
            self.sedentary_timer.start(self.settings.interval_min * 60 * 1000)
            if self.start_time is not None:
                self.elapsed_timer.start(1000)
            self.pause_btn.setText(t(self.settings.language, "pause"))
            self.act_pause_resume.setText(t(self.settings.language, "pause"))
            self.tray.showMessage(t(self.settings.language, "tray_tooltip"),
                                t(self.settings.language, "resumed"),
                                QSystemTrayIcon.Information, 1500)

    def reset_form(self):
        self.paused_at = None
        self.paused_accum = 0.0
        self.water_timer.stop(); self.sedentary_timer.stop(); self.elapsed_timer.stop()
        self.running = False; self.paused = False; self.start_time = None
        self._set_inputs_enabled(True)
        self.settings.water_progress = 0; self._update_progress_bar()
        self.elapsed_label.setText("00:00:00")
        self.start_btn.setEnabled(True); self.pause_btn.setEnabled(False); self.log_btn.setEnabled(False)
        self.log_move_btn.setEnabled(False)
        # 清掉历史活动小图标
        for lbl, mv in self.move_icons:
            mv.stop()
            lbl.deleteLater()
        self.move_icons.clear()
        self.move_count = 0
        self.move_count_label.setText(t(self.settings.language, "activity_count_fmt").format(0))

        self.finish_btn.setEnabled(False)
        self.tray.showMessage(t(self.settings.language, "reset_title"), t(self.settings.language, "reset_msg"), QSystemTrayIcon.Information, 1500)

    def log_sip(self):
        if not self.running or self.paused: return
        self.settings.water_progress += self.settings.sip_size
        self.settings.save()
        self._update_progress_bar()
        self.water_times.append(datetime.now())
        if self.settings.water_progress >= self.settings.goal:
            self.tray.showMessage(t(self.settings.language, "tray_tooltip"), t(self.settings.language, "goal_done"), QSystemTrayIcon.Information, 3000)
        
    def log_move(self):
        if not self.running or self.paused:
            return
        # 新增一个小 GIF
        lbl = QLabel()
        mv = QMovie(resource_path("images/sit.gif"))
        mv.setScaledSize(QSize(96, 96))
        lbl.setMovie(mv); mv.start()
        self.moves_row.addWidget(lbl)
        self.move_icons.append((lbl, mv))

        # 计数 +1 并刷新展示
        self.move_count += 1
        self.move_count_label.setText(
            t(self.settings.language, "activity_count_fmt").format(self.move_count)
        )
        self.move_times.append(datetime.now())

    def _build_report_text(self, end_time: datetime) -> str:
        # 固定双语样式，不再依赖 self.settings.language
        start_str = self.start_time.strftime("%Y-%m-%d %H:%M:%S") if self.start_time else "-"
        end_str   = end_time.strftime("%Y-%m-%d %H:%M:%S")

        # 已运行总时长（已扣除暂停）
        elapsed = self._elapsed_seconds_now()
        def fmt_hm(sec: float) -> str:
            sec = int(max(0, sec))
            h, r = divmod(sec, 3600)
            m, _ = divmod(r, 60)
            return f"{h}小时{m}分钟 / {h}h {m}min"

        # 饮水统计
        sips_cnt  = len(self.water_times)
        sip_size  = self.settings.sip_size
        total_ml  = self.settings.water_progress
        goal_ml   = self.settings.goal
        remain_ml = max(0, goal_ml - total_ml)

        # 活动统计：平均间隔 & 最长久坐
        move_times = list(self.move_times)
        gaps = []
        if self.start_time is not None:
            prev = self.start_time
            for t in move_times:
                gaps.append((t - prev).total_seconds())
                prev = t
            gaps.append((end_time - prev).total_seconds())

        if gaps:
            longest_gap = max(gaps)
            if len(move_times) >= 2:
                pair_gaps = [(move_times[i+1] - move_times[i]).total_seconds()
                            for i in range(len(move_times)-1)]
                avg_gap = sum(pair_gaps) / len(pair_gaps)
            else:
                avg_gap = elapsed / max(1, len(move_times))
        else:
            longest_gap = elapsed
            avg_gap = elapsed if elapsed > 0 else 0

        lines = [
            "——————  当日健康活动报告 / Daily Health Report  ——————",
            f"开始时间 / Start: {start_str}",
            f"结束时间 / End:   {end_str}",
            f"共计时长 / Duration: {fmt_hm(elapsed)}",
            "",
            "[饮水 / Hydration]",
            f"累计次数 / Sips: {sips_cnt}",
            f"每次饮水 / Per sip: {sip_size} ml",
            f"累计饮水 / Total intake: {total_ml} ml",
            f"饮水目标 / Goal: {goal_ml} ml",
            f"还需饮水 / Remaining: {remain_ml} ml",
            "",
            "[久坐/活动 Sedentary / Activity]",
            f"累计活动 / Activities: {len(move_times)}",
            f"平均间隔 / Avg between moves: {fmt_hm(avg_gap)}",
            f"最长久坐 / Longest sedentary interval: {fmt_hm(longest_gap)}",
            "",
            "（本报告由“健康生活小助手”自动生成 / Generated by Healthy Life Assistant）",
        ]
        return "\n".join(lines)

    # ---------- Popups ----------
    def _show_image_dialog(self, title: str, img_path: str, auto_close_ms: int, hydration: bool):
        dlg = QDialog(self); dlg.setWindowTitle(title); dlg.setWindowIcon(QIcon(resource_path("images/logo.png"))); dlg.setFixedSize(650, 650)
        v = QVBoxLayout(dlg)

        img_label = QLabel()
        if img_path.endswith(".gif"):
            movie = QMovie(resource_path(img_path)); movie.setScaledSize(QSize(500, 500))
            img_label.setMovie(movie); movie.start()
        else:
            pix = QPixmap(resource_path(img_path)); img_label.setPixmap(pix.scaled(475, 475, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        v.addWidget(img_label, alignment=Qt.AlignCenter)

        if hydration:
            live = QLabel(self._progress_text()); v.addWidget(live, alignment=Qt.AlignCenter)
            bar = QProgressBar(); bar.setValue(self.progress_bar.value()); v.addWidget(bar)
            btn = QPushButton(t(self.settings.language, "log_sip"))
            def _log_and_update():
                self.log_sip(); live.setText(self._progress_text()); bar.setValue(self.progress_bar.value())
            btn.clicked.connect(_log_and_update); v.addWidget(btn, alignment=Qt.AlignCenter)

        QTimer.singleShot(auto_close_ms, dlg.accept)
        dlg.exec_()

    def water_reminder(self):
        self._show_image_dialog(t(self.settings.language, "hydrate_time"), "images/water_remind.jpg", 5000, hydration=True)

    def sedentary_reminder(self):
        self._show_image_dialog(t(self.settings.language, "move_break"), "images/sit.gif", 7000, hydration=False)

    def finish_and_report(self):
        # 结束时间取“现在”
        end_time = datetime.now()

        # 生成报告文本
        text = self._build_report_text(end_time)

        # 保存到文件（按日期命名）
        APP_DIR.mkdir(parents=True, exist_ok=True)
        path = APP_DIR / f"health_report_{end_time:%Y-%m-%d}.txt"
        path.write_text(text, encoding="utf-8")

        # 尝试用系统默认记事本打开（Windows）
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
        except Exception:
            pass  # 打不开也没关系，下面会弹窗展示路径

        # 弹窗提示保存位置
        QMessageBox.information(
            self,
            t(self.settings.language, "report_title"),
            t(self.settings.language, "report_saved").format(str(path))
        )

        # 你也可以选择在“结束/下班”后自动重置：
        self.reset_form()

    # ---------- Window ----------
    def closeEvent(self, event):
        event.ignore(); self.hide()
        self.tray.showMessage(t(self.settings.language, "tray_tooltip"), "窗口已隐藏到托盘。", QSystemTrayIcon.Information, 1500)

# --------------------------------- Main --------------------------------- #
def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setStyleSheet(STYLE_QSS)

    app.setWindowIcon(QIcon(resource_path("images/logo.png")))
    win = MainWindow(); win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

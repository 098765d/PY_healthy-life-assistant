import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QIcon, QPixmap, QMovie
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QSpinBox, QComboBox, QPushButton, QProgressBar, QDialog,
    QMessageBox, QSystemTrayIcon, QMenu, QScrollArea, QSizePolicy,
    QGroupBox, QToolButton,
)


# ----------------------------- Constants ----------------------------- #
APP_NAME = "健康生活小助手"
APP_DIR = Path(os.getenv("APPDATA", Path.home())) / "HealthyLifeAssistant"
SETTINGS_PATH = APP_DIR / "settings.json"

LANG_EN, LANG_ZH = "EN", "ZH"
DEBUG_TEST_BUTTONS = False


# 新增：喝水提醒间隔（秒），含 10s/20s 测试选项
HYDRATE_INTERVALS_SEC = {
    LANG_EN: [
        (10,  "10 s (test)"), 
        (30 * 60, "30 Min"),
        (60 * 60, "1 Hour"),
        (90 * 60, "1.5 Hour"),
        (120*60,  "2 Hours"),
    ],
    LANG_ZH: [
        (10,  "10 秒（测试）"),
        (30 * 60, "30分钟"),
        (60 * 60, "1小时"),
        (90 * 60, "1.5 小时"),
        (120*60,  "2 小时"),
    ],
}

# 新增：久坐提醒间隔（秒），含 10s/20s 测试选项
SED_INTERVALS_SEC = {
    LANG_EN: [
        (10,      "10 s (test)"),
        (45 * 60, "45 Min"),
        (60 * 60, "1 Hour"),
        (75 * 60, "1 Hour 15 Min"),
        (90 * 60, "1 Hour 30 Min"),
    ],
    LANG_ZH: [
        (10,      "10 秒（测试）"),
        (45 * 60, "45分钟"),
        (60 * 60, "1小时"),
        (75 * 60, "1小时15分"),
        (90 * 60, "1小时30分"),
    ],
}

STYLE_QSS = """
    /* 全局：浅色 Apple 风格 */
    QWidget {
        font-family: "SF Pro Text", "PingFang SC", "Microsoft YaHei UI",
                     "Microsoft YaHei", "Segoe UI", system-ui, sans-serif;
        font-size: 10pt;
        color: #1F2933;
    }

    QMainWindow {
        background: #F5F5F7;              /* 类似 macOS 浅灰背景 */
    }

    /* 顶部 App 标题 */
    #AppTitle {
        font-size: 14pt;
        font-weight: 1000;
        color: #111827;
        padding: 10px 0 6px 0;
    }

    /* 通用卡片：白底+淡灰边框，圆角稍大一点 */
    QGroupBox {
        background: #FFFFFF;
        border: 1px solid #E5E5EA;
        border-radius: 10px;
        margin-top: 5px;
        padding: 5px 5px;
    }

    /* 分区标题：统一 iOS 蓝色 */
    #SectionTitleBlue,
    #SectionTitleGreen,
    #SectionTitleGray {
        font-size: 12pt;
        font-weight: 600;
        color: #007AFF;
        padding: 2px 2px 4px;
    }

    /* 进度区三个卡片：和其它保持统一 */
    #CardTime,
    #CardHydration,
    #CardActivity {
        background: #FFFFFF;
        border-color: #E5E5EA;
    }

    /* 顶部信息卡片（饮水推荐、久坐说明、健康设定）：略微淡灰底 */
    #CardBlue,
    #CardGreen,
    #CardGray {
        background: #F9FAFB;
        border-color: #E5E7EB;
    }

    /* 按钮：Apple 风蓝色按钮 */
    QPushButton {
        padding: 6px 18px;
        border-radius: 10px;
        background: #007AFF;
        color: #FFFFFF;
        border: 0;
        font-size: 14pt;
        font-weight: 500;
    }
    QPushButton:hover {
        background: #0A84FF;
    }
    QPushButton:disabled {
        background: #C7D2F5;
        color: #FFFFFF;
    }

    /* 进度条：浅灰底 + 亮绿色进度（和 Apple 健康/运动那种感觉类似） */
    QProgressBar {
        height: 8px;
        border-radius: 7px;
        border: 1px solid #E5E7EB;
        background: #E5E7EB;
        text-align: center;
    }
    QProgressBar::chunk {
        border-radius: 7px;
        background: #34C759;
    }

    /* 小标题说明 */
    #NoteLabel {
        color: #4B5563;
        font-weight: 500;
        padding: 2px 0 4px;
        font-size: 12pt;
    }

    QLabel {
        color: #1F2933;
    }

    /* 表单控件 */
    QComboBox,
    QSpinBox {
        background: #FFFFFF;
        border: 1px solid #D1D5DB;
        border-radius: 8px;
        padding: 4px 8px;
        min-height: 24px;
    }

    QScrollArea {
        border: none;
    }
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
        "water_interval": "💧Hydration Reminder Interval",
        "interval": "🪑Sedentary Break Interval",
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
        "logged_sip": "Hydration logged.",
        "logged_move": "Activity logged.",
        "welcome_title": "Welcome",
        "welcome_msg": "Welcome to Healthy Life Assistant.",
    },
    LANG_ZH: {
        "app_name": "健康生活小助手：提醒喝水·避免久坐",
        "title": "健康生活小助手",
        "reco_title": "每日足量饮水 & 避免久坐",
        "reco_text": (
            '<a href="http://dg.cnsoc.org/article/04/wDCyy7cWSJCN6pwKHOo5Dw.html">中国居民膳食指南（2022）</a>建议一般情况下，'
            "成年男性每天应饮水约<b>1700毫升</b>，成年女性每天应饮水约<b>1500毫升</b>。久坐对健康有害，<b>心血管</b>：长时间久坐与更高的心血管事件和全因死亡风险相关。<b>腰痛/颈痛</b>：尽量“多动少坐”可以减轻颈背/腰背僵硬与不适。<b>代谢</b>：打断久坐（例如每30-60分钟活动1–2分钟），能显著降低餐后血糖等代谢指标。"
            "健康的饮水频率应以<b>少量多次</b>为原则。"
        ),
        "settings_title": "健康设定",
        "settings_hint": (
            "<ul>"
            "<li><b>个人健康设定</b>：根据水杯容量设置「每次饮水量」，再设置「每日饮水目标」[饮水间隔]和[久坐提醒间隔]。</li>"
            "<li><b>点击“开始”</b>：开始计时会<b>锁定设置</b>；<u>若需修改请点“重置”</u>；离开可点“暂停”，返回后点“继续”。关闭窗口会隐藏到托盘；右键托盘可 显示/暂停/记录一口/记录活动/退出。</li>"
            "<li><b>结束/下班</b>：点击后生成当日健康报告，可保存本地。</li>"
            "</ul>"
        ),
        "progress_section": "进度",
        "water_goal": "每日饮水目标 (ml)",
        "sip_size": "每次饮水量 (ml)",
        "water_interval": "💧喝水提醒间隔",
        "interval": "🪑久坐提醒间隔",
        "start": "开始", "pause": "暂停", "resume": "继续", "log_sip": "记录一杯",
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
        "logged_sip": "饮水已记录。",
        "logged_move": "活动已记录。",
        "welcome_title": "欢迎使用",
        "welcome_msg": "欢迎使用健康小助手",
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
        s = Settings()      # 保持“每次启动即默认”的行为
        s.save()
        return s

    def save(self) -> None:
        SETTINGS_PATH.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )


# ----------------------------- Main Window ----------------------------- #
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings.load()
        self.running = False
        self.paused = False

        self.paused_at: Optional[datetime] = None
        self.water_times: List[datetime] = []   # 记录每次“记录一口”的时间戳
        self.move_times: List[datetime] = []    # 记录每次“记录活动”的时间戳

        self.paused_accum = 0.0          # 累积暂停秒数（float）

        # 用“活动时间（进度栏时间）”来控制弹窗
        self.water_interval_sec = int(1.5 * 60 * 60)   # 喝水提醒间隔（秒）
        self.sedentary_interval_sec = self.settings.interval_min * 60  # 久坐提醒间隔（秒）

        self.next_water_due: Optional[float] = None   # 下一次喝水提醒需要达到的“已运行秒数”
        self.next_move_due: Optional[float] = None    # 下一次久坐提醒需要达到的“已运行秒数”

        self.setWindowTitle(t(self.settings.language, "title"))
        self.resize(1600, 1300)
        self.setMinimumSize(1000, 650)

        # center -> scroll
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        page = QWidget()
        scroll.setWidget(page)
        self.setCentralWidget(scroll)
        self.outer = QVBoxLayout(page)
        self.outer.setContentsMargins(16, 16, 16, 16)
        self.outer.setSpacing(12)

        self.build_header()
        self.build_reco()
        self.build_form()
        self.build_progress()
        self.build_controls()
        self.build_tray()

        QMessageBox.information(
            self,
            t(self.settings.language, "welcome_title"),
            t(self.settings.language, "welcome_msg")
        )

        QApplication.setQuitOnLastWindowClosed(False)

    # ---------- UI builders ----------
    def build_header(self):
        row = QHBoxLayout()

        # --- logo ---
        logo = QLabel()
        pix = QPixmap(resource_path("images/logo.png"))
        logo_h = 75
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
        # 上：大标题，下：状态
        tw.addWidget(self.title_label, alignment=Qt.AlignVCenter | Qt.AlignLeft)
        tw.addStretch(1)

        # 让标题区在行里可扩展
        title_wrap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row.addWidget(title_wrap, 1)

        # --- 语言下拉 ---
        self.lang_box = QComboBox()
        self.lang_box.addItems(["English", "中文"])
        self.lang_box.setCurrentIndex(1 if self.settings.language == LANG_ZH else 0)
        self.lang_box.currentIndexChanged.connect(self.on_lang_change)

        lang_wrap = QWidget()
        lw = QVBoxLayout(lang_wrap)
        lw.setContentsMargins(0, 0, 0, 0)
        lw.addStretch(1)
        lw.addWidget(self.lang_box, alignment=Qt.AlignRight)
        lw.addStretch(1)

        row.addWidget(lang_wrap, 0, Qt.AlignRight)

        self.outer.addLayout(row)

    def build_reco(self):
        self.reco_title = QLabel()
        self.reco_title.setObjectName("SectionTitleBlue")
        self.outer.addWidget(self.reco_title)

        self.reco_card = QGroupBox()
        self.reco_card.setObjectName("CardBlue")
        v = QVBoxLayout(self.reco_card)

        self.reco_label = QLabel()
        self.reco_label.setTextFormat(Qt.RichText)
        self.reco_label.setOpenExternalLinks(True)
        self.reco_label.setWordWrap(True)
        v.addWidget(self.reco_label)

        self.outer.addWidget(self.reco_card)

    def build_form(self):
        self.form_title = QLabel()
        self.form_title.setObjectName("SectionTitleGreen")
        self.outer.addWidget(self.form_title)

        self.form_card = QGroupBox()
        self.form_card.setObjectName("CardGreen")
        box = QVBoxLayout(self.form_card)
        form = QFormLayout()
        box.addLayout(form)

        self.settings_hint = QLabel()
        self.settings_hint.setWordWrap(True)
        form.addRow(self.settings_hint)

        self.goal_spin = QSpinBox()
        self.goal_spin.setRange(1500, 3000)
        self.goal_spin.setSingleStep(100)

        self.sip_spin = QSpinBox()
        self.sip_spin.setRange(50, 1000)
        self.sip_spin.setSingleStep(50)

        self.water_interval_box = QComboBox()   # 喝水提醒间隔（测试）
        self.interval_box = QComboBox()         # 久坐提醒间隔

        self.lbl_goal = QLabel()
        self.lbl_sip = QLabel()
        self.lbl_water_intv = QLabel()
        self.lbl_intv = QLabel()

        form.addRow(self.lbl_goal, self.goal_spin)
        form.addRow(self.lbl_sip, self.sip_spin)
        form.addRow(self.lbl_water_intv, self.water_interval_box)
        form.addRow(self.lbl_intv, self.interval_box)

        self.outer.addWidget(self.form_card)

    def build_progress(self):
        # 顶部一行：左边“进度”，右边“状态”
        header_row = QHBoxLayout()
        # 顶部标题
        self.prog_title = QLabel()
        self.prog_title.setObjectName("SectionTitleGray")
        header_row.addWidget(self.prog_title)

        # 新增：状态文字放在右侧
        self.state_label = QLabel()
        self.state_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header_row.addStretch(1)
        header_row.addWidget(self.state_label)

        self.outer.addLayout(header_row)

        # 进度区单独的垂直布局，卡片之间间距设为 4
        prog_layout = QVBoxLayout()
        prog_layout.setContentsMargins(0, 0, 0, 0)
        prog_layout.setSpacing(0)   # ← 卡片之间距离（可以改成 2 或 0 更紧）

        # —— 时间卡片 —— #
        self.time_card = QGroupBox()
        self.time_card.setObjectName("CardTime")
        v_time = QVBoxLayout(self.time_card)
        v_time.setContentsMargins(8, 4, 8, 4)   # ← 新增：缩小上下边距
        v_time.setSpacing(4)  

        self.elapsed_desc = QLabel()
        self.elapsed_desc.setObjectName("NoteLabel")
        v_time.addWidget(self.elapsed_desc)

        self.elapsed_label = QLabel("00:00:00")
        v_time.addWidget(self.elapsed_label)

        self.outer.addWidget(self.time_card)

        # —— 饮水卡片 —— #
        self.hyd_card = QGroupBox()
        self.hyd_card.setObjectName("CardHydration")
        v_hyd = QVBoxLayout(self.hyd_card)
        v_hyd.setContentsMargins(8, 4, 8, 4)
        v_hyd.setSpacing(4)

        self.water_log_desc = QLabel()
        self.water_log_desc.setObjectName("NoteLabel")
        v_hyd.addWidget(self.water_log_desc)

        self.progress_label = QLabel()
        self.progress_bar = QProgressBar()
        v_hyd.addWidget(self.progress_label)
        v_hyd.addWidget(self.progress_bar)

        self.outer.addWidget(self.hyd_card)

        # —— 活动卡片 —— #
        self.act_card = QGroupBox()
        self.act_card.setObjectName("CardActivity")
        v_act = QVBoxLayout(self.act_card)
        v_act.setContentsMargins(8, 4, 8, 4)
        v_act.setSpacing(4)

        self.activity_log_desc = QLabel()
        self.activity_log_desc.setObjectName("NoteLabel")
        v_act.addWidget(self.activity_log_desc)

        hdr = QHBoxLayout()  # 计数 + GIF 同一行
        self.move_count = 0
        self.move_count_label = QLabel("0")
        hdr.addWidget(self.move_count_label)

        hdr.addSpacing(12)

        self.moves_row = QHBoxLayout()
        self.moves_row.setSpacing(6)
        self.moves_row.setContentsMargins(0, 0, 0, 0)
        hdr.addLayout(self.moves_row)

        hdr.addStretch(1)
        v_act.addLayout(hdr)

        self.move_icons = []  # [(QLabel, QMovie), ...]

        self.outer.addWidget(self.act_card)
        self.outer.addLayout(prog_layout)

        # 计时器
        self.start_time = None
        self.elapsed_timer = QTimer(self)
        self.elapsed_timer.timeout.connect(self._tick_elapsed)


    def build_controls(self):
        row = QHBoxLayout()

        # —— 主操作（靠左）：开始、暂停/继续
        self.start_btn = QPushButton()
        self.start_btn.clicked.connect(self.start_reminders)

        self.pause_btn = QPushButton()
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.setEnabled(False)

        row.addWidget(self.start_btn)
        row.addWidget(self.pause_btn)

        row.addSpacing(12)

        # —— 记录分组（中间）：记录一口 + 记录活动
        log_wrap = QHBoxLayout()
        self.log_btn = QPushButton()
        self.log_btn.clicked.connect(self.log_sip)
        self.log_btn.setEnabled(False)

        self.log_move_btn = QPushButton()
        self.log_move_btn.clicked.connect(self.log_move)
        self.log_move_btn.setEnabled(False)

        log_wrap.addWidget(self.log_btn)
        log_wrap.addWidget(self.log_move_btn)
        row.addLayout(log_wrap)

        row.addStretch(1)

        # —— 结束与重置（靠右）
        self.finish_btn = QPushButton()
        self.finish_btn.setText(t(self.settings.language, "finish_day"))
        self.finish_btn.clicked.connect(self.finish_and_report)
        self.finish_btn.setEnabled(False)

        self.reset_btn = QPushButton()
        self.reset_btn.clicked.connect(self.reset_form)

        row.addWidget(self.finish_btn)
        row.addWidget(self.reset_btn)

        for btn in [
            self.start_btn, self.pause_btn, self.log_btn,
            self.log_move_btn, self.finish_btn, self.reset_btn
        ]:
            btn.setMinimumWidth(110)

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
        self.tray.activated.connect(self.on_tray_activated)


        # 初始值赋入
        self.goal_spin.setValue(self.settings.goal)
        self.sip_spin.setValue(self.settings.sip_size)
        self.apply_texts()

    # ---------- Texts / Language ----------
    def apply_texts(self):
        lang = self.settings.language
        self.setWindowTitle(t(lang, "title"))
        self.title_label.setText(t(lang, "app_name"))

        self.reco_title.setText("💧/🪑 " + t(lang, "reco_title"))
        self.reco_label.setText(t(lang, "reco_text"))

        self.form_title.setText("⚙️ " + t(lang, "settings_title"))
        self.settings_hint.setText(t(lang, "settings_hint"))

        self.prog_title.setText("📊 " + t(lang, "progress_section"))
        self.log_move_btn.setText(t(lang, "log_move"))

        self.lbl_goal.setText(t(lang, "water_goal"))
        self.lbl_sip.setText(t(lang, "sip_size"))
        self.lbl_water_intv.setText(t(lang, "water_interval"))
        self.lbl_intv.setText(t(lang, "interval"))

        self.elapsed_desc.setText("⏱️ " + t(lang, "elapsed_desc"))
        self.water_log_desc.setText("💦 " + t(lang, "water_log_desc"))
        self.activity_log_desc.setText("🚶 " + t(lang, "activity_log_desc"))

        self.move_count_label.setText(
            t(lang, "activity_count_fmt").format(self.move_count)
        )

        # 喝水提醒间隔
        self.water_interval_box.blockSignals(True)
        self.water_interval_box.clear()
        for sec, label in HYDRATE_INTERVALS_SEC[lang]:
            self.water_interval_box.addItem(label, sec)
        default_water = 90 * 60
        idx = 0
        for i in range(self.water_interval_box.count()):
            if self.water_interval_box.itemData(i) == default_water:
                idx = i
                break
        self.water_interval_box.setCurrentIndex(idx)
        self.water_interval_box.blockSignals(False)

        # 久坐提醒间隔
        self.interval_box.blockSignals(True)
        self.interval_box.clear()
        for sec, label in SED_INTERVALS_SEC[lang]:
            self.interval_box.addItem(label, sec)
        target = self.settings.interval_min * 60
        idx = 0
        for i in range(self.interval_box.count()):
            if self.interval_box.itemData(i) == target:
                idx = i
                break
        self.interval_box.setCurrentIndex(idx)
        self.interval_box.blockSignals(False)

        self.reset_btn.setText(t(lang, "reset_title"))
        self.start_btn.setText(t(lang, "start") if not self.running else t(lang, "started"))
        self.pause_btn.setText(t(lang, "pause") if not self.paused else t(lang, "resume"))
        self.log_btn.setText(t(lang, "log_sip"))
        self.tray.setToolTip(t(lang, "tray_tooltip"))

        self._update_progress_bar()
        self.finish_btn.setText(t(lang, "finish_day"))
        self._update_state_label()


    def on_lang_change(self, idx: int):
        self.settings.language = LANG_ZH if idx == 1 else LANG_EN
        self.apply_texts()
        self._rebuild_tray_menu()
        self.settings.save()

    def _clear_activity_ui(self):
        for lbl, mv in self.move_icons:
            try:
                mv.stop()
            except Exception:
                pass
            lbl.deleteLater()
        self.move_icons.clear()
        self.move_count = 0
        self.move_count_label.setText(
            t(self.settings.language, "activity_count_fmt").format(0)
        )

    # ---------- Helpers ----------
    def get_sedentary_interval_sec(self) -> int:
        data = self.interval_box.currentData()
        return int(data) if data is not None else 60 * 60

    def get_water_interval_sec(self) -> int:
        data = self.water_interval_box.currentData()
        return int(data) if data is not None else 90 * 60

    def _progress_text(self) -> str:
        return t(self.settings.language, "progress").format(
            self.settings.water_progress, self.settings.goal
        )

    def _update_progress_bar(self):
        pct = int(round(
            (self.settings.water_progress / max(1, self.settings.goal)) * 100
        ))
        self.progress_bar.setValue(max(0, min(100, pct)))
        self.progress_label.setText(self._progress_text())

    def _set_inputs_enabled(self, enabled: bool):
        self.goal_spin.setEnabled(enabled)
        self.sip_spin.setEnabled(enabled)
        self.water_interval_box.setEnabled(enabled)
        self.interval_box.setEnabled(enabled)

    def _update_state_label(self):
        """根据 running/paused 状态，更新标题下方的小状态文字和颜色。"""
        lang = self.settings.language

        if not self.running:
            text = "⏺ 未开始" if lang == LANG_ZH else "⏺ Not started"
            color = "#6B7280"   # 灰色
        elif self.paused:
            text = "⏸ 已暂停" if lang == LANG_ZH else "⏸ Paused"
            color = "#F97316"   # 橙色
        else:
            text = "▶ 运行中" if lang == LANG_ZH else "▶ Running"
            color = "#16A34A"   # 绿色

        self.state_label.setText(text)
        self.state_label.setStyleSheet(
            f"color: {color}; font-weight: 600; font-size: 14pt;"
        )


    def _elapsed_seconds_now(self) -> float:
        """返回当前累计运行秒数（扣除暂停），用于进度时间 & 提醒调度。"""
        if self.start_time is None:
            return 0.0
        now = datetime.now()
        secs = (now - self.start_time).total_seconds() - float(self.paused_accum)
        if self.paused_at is not None:
            secs -= (now - self.paused_at).total_seconds()
        return max(0.0, secs)

    def _tick_elapsed(self):
        if self.start_time is None:
            return

        secs = self._elapsed_seconds_now()   # 已扣除暂停时间
        h, rem = divmod(int(secs), 3600)
        m, s = divmod(rem, 60)
        self.elapsed_label.setText(f"{h:02d}:{m:02d}:{s:02d}")

        # 若没在运行或暂停中，不做提醒逻辑
        if not self.running or self.paused:
            return

        # —— 用“活动时间秒数”触发喝水提醒 —— #
        if self.next_water_due is not None and secs >= self.next_water_due:
            self.water_reminder()
            self.next_water_due += self.water_interval_sec

        # —— 用“活动时间秒数”触发久坐提醒 —— #
        if self.next_move_due is not None and secs >= self.next_move_due:
            self.sedentary_reminder()
            self.next_move_due += self.sedentary_interval_sec
        # 若暂停，则把时间文字变成灰色；否则恢复默认颜色
        if self.paused:
            self.elapsed_label.setStyleSheet("color: #9CA3AF;")   # 灰
        else:
            self.elapsed_label.setStyleSheet("")  # 用回全局样式

    def _tray_log_sip(self):
        # 只在“正在运行且未暂停”时生效
        if not self.running or self.paused:
            return
        self.log_sip()
        self.tray.showMessage(
            t(self.settings.language, "tray_tooltip"),
            t(self.settings.language, "logged_sip"),
            QSystemTrayIcon.Information,
            1500,
        )

    def _tray_log_move(self):
        if not self.running or self.paused:
            return
        self.log_move()
        self.tray.showMessage(
            t(self.settings.language, "tray_tooltip"),
            t(self.settings.language, "logged_move"),
            QSystemTrayIcon.Information,
            1500,
        )

    def _rebuild_tray_menu(self):
        menu = QMenu()
        act_show = menu.addAction(t(self.settings.language, "show"))
        act_show.triggered.connect(self._show_normal)

        self.act_pause_resume = menu.addAction(t(self.settings.language, "pause"))
        self.act_pause_resume.triggered.connect(self.toggle_pause)

        # 新增：托盘直接“记录一口 / 记录活动”
        act_log_sip = menu.addAction(t(self.settings.language, "log_sip"))
        act_log_sip.triggered.connect(self._tray_log_sip)

        act_log_move = menu.addAction(t(self.settings.language, "log_move"))
        act_log_move.triggered.connect(self._tray_log_move)

        act_quit = menu.addAction(t(self.settings.language, "quit"))
        act_quit.triggered.connect(lambda: QApplication.instance().quit())

        self.tray.setContextMenu(menu)
    
    def on_tray_activated(self, reason):
        # 仅在双击托盘图标时显示主窗口
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_normal()

    def _show_normal(self):
        self.show()
        self.raise_()
        self.activateWindow()

    # ---------- Actions ----------
    def start_reminders(self):
        # —— 本次会话开始：清空所有会话统计 —— #
        self.water_times.clear()
        self.move_times.clear()
        self._clear_activity_ui()
        self.settings.water_progress = 0
        self._update_progress_bar()

        # 保存当前设定并锁定输入
        self.settings.goal = self.goal_spin.value()
        self.settings.sip_size = self.sip_spin.value()
        self.settings.interval_min = int(self.get_sedentary_interval_sec() / 60)
        self.settings.water_progress = 0
        self.settings.last_reset = str(datetime.now().date())
        self.settings.save()

        self.paused_at = None
        self.paused_accum = 0.0
        self.start_time = datetime.now()
        self.elapsed_label.setText("00:00:00")
        self.elapsed_timer.start(1000)

        # 用当前下拉框计算间隔（秒）
        self.water_interval_sec = self.get_water_interval_sec()
        self.sedentary_interval_sec = self.get_sedentary_interval_sec()
        self.next_water_due = self.water_interval_sec
        self.next_move_due = self.sedentary_interval_sec

        self.running = True
        self.paused = False
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.log_btn.setEnabled(True)
        self.pause_btn.setText(t(self.settings.language, "pause"))
        self.act_pause_resume.setText(t(self.settings.language, "pause"))

        self._set_inputs_enabled(False)
        self._update_progress_bar()
        self._update_state_label()   # ← 新增：更新状态文字

        self.tray.showMessage(
            t(self.settings.language, "tray_tooltip"),
            t(self.settings.language, "started"),
            QSystemTrayIcon.Information,
            2000,
        )

        # 启动时先弹一次喝水提醒（可用于测试）
        self.water_reminder()
        self.log_move_btn.setEnabled(True)
        self.finish_btn.setEnabled(True)

    def toggle_pause(self):
        if not self.running:
            return

        self.paused = not self.paused
        if self.paused:
            # 进入暂停：停止“活动时间”计时器，记录暂停起点
            self.elapsed_timer.stop()
            self.paused_at = datetime.now()
            self.pause_btn.setText(t(self.settings.language, "resume"))
            self.act_pause_resume.setText(t(self.settings.language, "resume"))
            self.tray.showMessage(
                t(self.settings.language, "tray_tooltip"),
                t(self.settings.language, "paused"),
                QSystemTrayIcon.Information,
                1500,
            )
        else:
            # 结束暂停：把这段暂停时间加入累计
            if self.paused_at is not None:
                self.paused_accum += (datetime.now() - self.paused_at).total_seconds()
                self.paused_at = None
            if self.start_time is not None:
                self.elapsed_timer.start(1000)

            self.pause_btn.setText(t(self.settings.language, "pause"))
            self.act_pause_resume.setText(t(self.settings.language, "pause"))
            self.tray.showMessage(
                t(self.settings.language, "tray_tooltip"),
                t(self.settings.language, "resumed"),
                QSystemTrayIcon.Information,
                1500,
            )
        # 无论暂停还是恢复，都更新一下状态文字
        self._update_state_label()

    def reset_form(self):
        self.paused_at = None
        self.paused_accum = 0.0

        # 保留 stop 调用（虽然不再依赖这两个 QTimer 做逻辑）
        self.elapsed_timer.stop()

        self.running = False
        self.paused = False
        self.start_time = None

        # 基于活动时间的调度清零
        self.next_water_due = None
        self.next_move_due = None

        self._set_inputs_enabled(True)

        self.settings.water_progress = 0
        self._update_progress_bar()
        self.water_times.clear()
        self.move_times.clear()
        self._clear_activity_ui()

        self.elapsed_label.setText("00:00:00")
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.log_btn.setEnabled(False)
        self.log_move_btn.setEnabled(False)
        self.finish_btn.setEnabled(False)
        self._update_state_label()   # ← 新增
        self.tray.showMessage(
            t(self.settings.language, "reset_title"),
            t(self.settings.language, "reset_msg"),
            QSystemTrayIcon.Information,
            1500,
        )

    def log_sip(self):
        if not self.running or self.paused:
            return
        self.settings.water_progress += self.settings.sip_size
        self.settings.save()
        self._update_progress_bar()
        self.water_times.append(datetime.now())
        if self.settings.water_progress >= self.settings.goal:
            self.tray.showMessage(
                t(self.settings.language, "tray_tooltip"),
                t(self.settings.language, "goal_done"),
                QSystemTrayIcon.Information,
                3000,
            )

    def log_move(self):
        if not self.running or self.paused:
            return
        lbl = QLabel()
        mv = QMovie(resource_path("images/sit.gif"))
        mv.setScaledSize(QSize(65, 65))
        lbl.setMovie(mv)
        mv.start()
        self.moves_row.addWidget(lbl)
        self.move_icons.append((lbl, mv))

        self.move_count += 1
        self.move_count_label.setText(
            t(self.settings.language, "activity_count_fmt").format(self.move_count)
        )
        self.move_times.append(datetime.now())

    def _build_report_text(self, end_time: datetime) -> str:
        start_str = self.start_time.strftime("%Y-%m-%d %H:%M:%S") if self.start_time else "-"
        end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")

        elapsed = self._elapsed_seconds_now()

        def fmt_hm(sec: float) -> str:
            sec = int(max(0, sec))
            h, r = divmod(sec, 3600)
            m, _ = divmod(r, 60)
            return f"{h}小时{m}分钟 / {h}h {m}min"

        sips_cnt = len(self.water_times)
        sip_size = self.settings.sip_size
        total_ml = self.settings.water_progress
        goal_ml = self.settings.goal
        remain_ml = max(0, goal_ml - total_ml)

        move_times = list(self.move_times)
        gaps: List[float] = []
        if self.start_time is not None:
            prev = self.start_time
            for t in move_times:
                gaps.append((t - prev).total_seconds())
                prev = t
            gaps.append((end_time - prev).total_seconds())

        if gaps:
            longest_gap = max(gaps)
            if len(move_times) >= 2:
                pair_gaps = [
                    (move_times[i + 1] - move_times[i]).total_seconds()
                    for i in range(len(move_times) - 1)
                ]
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
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setWindowIcon(QIcon(resource_path("images/logo.png")))
        dlg.setFixedSize(650, 650)
        v = QVBoxLayout(dlg)

        img_label = QLabel()
        if img_path.endswith(".gif"):
            movie = QMovie(resource_path(img_path))
            movie.setScaledSize(QSize(500, 500))
            img_label.setMovie(movie)
            movie.start()
        else:
            pix = QPixmap(resource_path(img_path))
            img_label.setPixmap(
                pix.scaled(475, 475, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        v.addWidget(img_label, alignment=Qt.AlignCenter)

        if hydration:
            # 喝水弹窗：进度 + 进度条 + “记录一口”
            live = QLabel(self._progress_text())
            v.addWidget(live, alignment=Qt.AlignCenter)

            bar = QProgressBar()
            bar.setValue(self.progress_bar.value())
            v.addWidget(bar)

            btn = QPushButton(t(self.settings.language, "log_sip"))

            def _log_and_update():
                self.log_sip()
                live.setText(self._progress_text())
                bar.setValue(self.progress_bar.value())

            btn.clicked.connect(_log_and_update)
            v.addWidget(btn, alignment=Qt.AlignCenter)
        else:
            # 活动弹窗：提示文字 + “记录活动”按钮
            msg = QLabel(t(self.settings.language, "move_msg"))
            msg.setWordWrap(True)
            v.addWidget(msg, alignment=Qt.AlignCenter)

            btn = QPushButton(t(self.settings.language, "log_move"))

            def _log_move_and_close():
                self.log_move()
                dlg.accept()   # 记录完顺手关掉弹窗

            btn.clicked.connect(_log_move_and_close)
            v.addWidget(btn, alignment=Qt.AlignCenter)

        QTimer.singleShot(auto_close_ms, dlg.accept)
        dlg.exec_()
    def _show_joboff_dialog(self):
        """结束/下班 时弹出的图片窗口（images/joboff.jpg）"""
        dlg = QDialog(self)
        dlg.setWindowTitle("下班啦")
        dlg.setWindowIcon(QIcon(resource_path("images/logo.png")))
        dlg.setFixedSize(650, 650)

        layout = QVBoxLayout(dlg)

        label = QLabel()
        pix = QPixmap(resource_path("images/joboff.jpg"))
        if not pix.isNull():
            pix = pix.scaled(600, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(pix)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        # 自动 3 秒后关闭，也可以手动点 ×
        QTimer.singleShot(7000, dlg.accept)
        dlg.exec_()


    def water_reminder(self):
        self._show_image_dialog(
            t(self.settings.language, "hydrate_time"),
            "images/water_remind.jpg",
            5000,
            hydration=True,
        )

    def sedentary_reminder(self):
        self._show_image_dialog(
            t(self.settings.language, "move_break"),
            "images/sit.gif",
            7000,
            hydration=False,
        )

    def finish_and_report(self):
        # 先弹出“下班”图片窗口
        self._show_joboff_dialog()   # ← 新增这一行
        end_time = datetime.now()
        text = self._build_report_text(end_time)

        APP_DIR.mkdir(parents=True, exist_ok=True)
        path = APP_DIR / f"health_report_{end_time:%Y-%m-%d}.txt"
        path.write_text(text, encoding="utf-8")

        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
        except Exception:
            pass

        QMessageBox.information(
            self,
            t(self.settings.language, "report_title"),
            t(self.settings.language, "report_saved").format(str(path)),
        )

        self.reset_form()

    # ---------- Window ----------
    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage(
            t(self.settings.language, "tray_tooltip"),
            "窗口已隐藏到托盘。",
            QSystemTrayIcon.Information,
            1500,
        )


# --------------------------------- Main --------------------------------- #
def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setStyleSheet(STYLE_QSS)

    app.setWindowIcon(QIcon(resource_path("images/logo.png")))
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

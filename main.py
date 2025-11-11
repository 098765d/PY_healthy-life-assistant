
import json
from datetime import datetime
from dataclasses import dataclass, asdict
import sys, os
from pathlib import Path

DEBUG_TEST_BUTTONS = False
def resource_path(rel_path: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel_path)


from PyQt5.QtCore import Qt, QTimer,QSize
from PyQt5.QtGui import QIcon, QPixmap, QMovie
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QSpinBox, QComboBox, QPushButton, QProgressBar, QDialog,
    QMessageBox, QSystemTrayIcon, QMenu, QStyle, QGroupBox, QScrollArea, QSizePolicy
)

# ----------------------------- Translations ----------------------------- #
TRANSLATIONS = {
    "EN": {
        "app_name": "Healthy Life Assistant — Hydration & Anti-sedentary",
        "title": "Health Reminder",
        "settings_title": "Health Settings",
        "settings_hint": (
            "Enter your daily water goal and sip size, choose the break interval, then click “Start”. "
            "The app will pop up reminders based on your settings. Closing the window hides it to the tray; "
            "to fully exit, right-click the tray icon and choose “Quit”."
        ),
        "progress_section": "Progress",
        "water_goal": "Daily Water Goal (ml)",
        "sip_size": "Sip Size (ml)",
        "interval": "Sedentary Break Interval",
        "start": "Start",
        "pause": "Pause",
        "resume": "Resume",
        "log_sip": "Log Sip",
        "move_break": "Move Break!",
        "hydrate_time": "Hydration Time!",
        "progress": "You've drank {}/{} ml",
        "move_msg": "Stand up and stretch — good for blood flow and spine!",
        "quit": "Quit",
        "reset_msg": "Defaults applied.",
        "language": "Language",
        "show": "Show",
        "started": "Reminders started.",
        "paused": "Reminders paused.",
        "resumed": "Reminders resumed.",
        "goal_done": "Goal Achieved!",
        "tray_tooltip": "Health Reminder",
        "reset_title": "Reset",
        "tray_log_sip": "Log Sip Now",
        "test_water": "Test Water Popup",
        "test_sit": "Test Sit Popup",
        "tip_hide": "Window hidden to tray. Reminders keep running.",
        "sed_title": "Why Break Up Sitting",
        "sed_text": (
            "<ul>"
            "<li><b>Vascular/Cardio</b>: Standing up every 60 min can improve endothelial function and lower CVD risk.</li>"
            "<li><b>Spine/Muscles</b>: Brief hourly movement reduces neck and low-back discomfort.</li>"
            "<li><b>Metabolism</b>: ~6 min of light activity each hour helps lower post-meal glucose and insulin.</li>"
            "</ul>"
        ),

        # New for recommendation panel
        "reco_title": "Daily Water Intake Recommendation",
        "reco_text": (
            "In general conditions, the Chinese Dietary Guidelines (2022) suggest "
            "about <b>1700 ml</b> per day for adult men and <b>1500 ml</b> for adult women. "
            'See details: <a href="http://dg.cnsoc.org/article/04/wDCyy7cWSJCN6pwKHOo5Dw.html">Chinese Dietary Guidelines (2022)</a>'
        ),
    },


    "ZH": {
        "app_name": "健康生活小助手：提醒喝水·避免久坐",
        "title": "健康生活小助手",
        "settings_title": "健康设定",
        "settings_hint": (
            "输入每日饮水目标和每次饮水量，选择久坐提醒间隔(饮水提醒间隔固定为1.5小时)，点击“开始”即可开始记录。"
            "应用会按您的设定定时弹窗提醒。关闭窗口将最小化到托盘；要完全退出，请右键托盘图标选择“退出”。"
        ),
        "progress_section": "进度",
        "water_goal": "每日饮水目标 (ml)",
        "sip_size": "每次饮水量 (ml)",
        "interval": "久坐提醒间隔",
        "start": "开始",
        "pause": "暂停",
        "resume": "继续",
        "log_sip": "记录一口",
        "move_break": "动一动！",
        "hydrate_time": "喝水时间！",
        "progress": "已饮 {}/{} ml",
        "move_msg": "来活动活动！",
        "quit": "退出",
        "reset_msg": "欢迎使用健康生活小助手（默认设置）",
        "language": "语言",
        "show": "显示主界面",
        "started": "提醒已启动。",
        "paused": "提醒已暂停。",
        "resumed": "提醒已继续。",
        "goal_done": "目标达成！",
        "tray_tooltip": "健康提醒",
        "reset_title": "重置",
        "tray_log_sip": "立刻记录一口",
        "test_water": "测试喝水弹窗",
        "test_sit": "测试久坐弹窗",
        "tip_hide": "窗口已隐藏到托盘，提醒继续运行。",
        "sed_title": "避免久坐",
        "sed_text": (
            "<ul>"
            "<li><b>心血管健康</b>：定时活动，可改善血管内皮功能，促进血液循环，减少心血管疾病风险。</li>"
            "<li><b>腰椎/颈椎健康</b>：每小时短暂活动能显著缓解腰部和颈部的僵硬，缓解酸痛。</li>"
            "<li><b>增强代谢</b>：每小时进行轻度活动，有助于降低餐后血糖与胰岛素水平。</li>"
            "</ul>"
        ),

        # 新增：推荐面板
        "reco_title": "每日饮水",
        "reco_text": (
            '<a href="http://dg.cnsoc.org/article/04/wDCyy7cWSJCN6pwKHOo5Dw.html">中国居民膳食指南（2022）</a>建议，在一般情况下，'
            "成年男性每天应饮水约<b>1700毫升</b>，成年女性每天应饮水约<b>1500毫升</b>。"
            '健康的饮水频率应以<b>少量多次</b>为原则，避免一次性大量饮水导致胃部不适或电解质失衡。总体目标是均匀分布在一天中，确保总摄入量达到个人需求'
            "<ul>"
            "<li><b>代谢提升</b>：饮水促进新陈代谢率上升，帮助控制体重和血糖水平。</li>"
            "<li><b>肾脏保护</b>：规律饮水有助于排出废物，预防肾结石和尿路感染风险。</li>"
            "</ul>"        
        ),
    }   
}

def t(lang, key):
    return TRANSLATIONS.get(lang, TRANSLATIONS["EN"]).get(key, key)

# ------------------------------- Settings ------------------------------- #
APP_DIR = Path(os.getenv("APPDATA", Path.home())) / "HealthyLifeAssistant"
APP_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_PATH = APP_DIR / "settings.json"

@dataclass
class Settings:
    goal: int = 1700
    sip_size: int = 250
    interval_min: int = 60
    water_progress: int = 0
    last_reset: str = str(datetime.now().date())
    language: str = "ZH"  # "EN" or "ZH"

    @staticmethod
    def load_and_force_defaults() -> "Settings":
        # Keep the original "reset to defaults on launch" behavior
        if SETTINGS_PATH.exists():
            try:
                _ = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass
        s = Settings()
        s.save()
        return s

    def save(self):
        SETTINGS_PATH.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")

# ------------------------------ Main Window ----------------------------- #
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings.load_and_force_defaults()
        self.running = False
        self.paused = False

        self.setWindowTitle(t(self.settings.language, "title"))
        self.resize(1600, 1250)                             # <-- allow user resize
        self.setMinimumSize(1000, 650)  

        # --- central widget -> QScrollArea + content page ---
        scroll = QScrollArea(self)                         # <-- new: scrollable container
        scroll.setWidgetResizable(True)
        page = QWidget()                                   # content page inside the scroll area
        scroll.setWidget(page)
        self.setCentralWidget(scroll)

        outer = QVBoxLayout(page)                          # <-- attach layout to the page (not self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        # Language row
        lang_row = QHBoxLayout()
        lang_label = QLabel(t(self.settings.language, "language"))
        self.lang_box = QComboBox()
        self.lang_box.addItems(["English", "中文"])
        self.lang_box.setCurrentIndex(1 if self.settings.language == "ZH" else 0)
        self.lang_box.currentIndexChanged.connect(self.on_lang_change)
        lang_row.addWidget(lang_label)
        lang_row.addStretch(1)
        lang_row.addWidget(self.lang_box)
        outer.addLayout(lang_row)

        # --- Header: Logo (left) + Title (right) in one row ---
        header = QHBoxLayout()
        header.setContentsMargins(0, 8, 0, 8)

        logo_label = QLabel()
        pix = QPixmap(resource_path("images/logo.png"))
        if pix.isNull():
            logo_label.setText("images/logo.png missing")
        else:
            logo_label.setPixmap(pix.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setFixedSize(100, 100)
        logo_label.setObjectName("AppLogo")

        self.title_label = QLabel(t(self.settings.language, "app_name"))
        self.title_label.setObjectName("AppTitle")
        self.title_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        header.addWidget(logo_label)
        header.addSpacing(12)
        header.addWidget(self.title_label, 1)   # 伸展，占满剩余空间
        outer.addLayout(header)


        # Recommendation card (with clickable link)
        # --- Daily water: title outside, plain card
        self.reco_title_lbl = QLabel(t(self.settings.language, "reco_title"))
        self.reco_title_lbl.setObjectName("SectionTitleBlue")
        outer.addWidget(self.reco_title_lbl)

        reco_group = QGroupBox()                # no built-in title now
        reco_group.setObjectName("CardBlue")
        r = QVBoxLayout(reco_group)

        self.reco_label = QLabel()
        self.reco_label.setTextFormat(Qt.RichText)
        self.reco_label.setOpenExternalLinks(True)
        self.reco_label.setWordWrap(True)
        self.reco_label.setText(t(self.settings.language, "reco_text"))
        r.addWidget(self.reco_label)

        outer.addWidget(reco_group)


        # --- Anti-sedentary: title outside, plain card
        self.sed_title_lbl = QLabel(t(self.settings.language, "sed_title"))
        self.sed_title_lbl.setObjectName("SectionTitleBlue")
        outer.addWidget(self.sed_title_lbl)

        sed_group = QGroupBox()
        sed_group.setObjectName("CardBlue")     # reuse your blue card styling if you like
        sed_layout = QVBoxLayout(sed_group)

        self.sed_label = QLabel()
        self.sed_label.setTextFormat(Qt.RichText)
        self.sed_label.setWordWrap(True)
        self.sed_label.setText(t(self.settings.language, "sed_text"))
        sed_layout.addWidget(self.sed_label)

        outer.addWidget(sed_group)


       # --- Settings: title outside, plain card
        self.settings_title_lbl = QLabel(t(self.settings.language, "settings_title"))
        self.settings_title_lbl.setObjectName("SectionTitleGreen")
        outer.addWidget(self.settings_title_lbl)

        self.form_group = QGroupBox()           # no built-in title
        self.form_group.setObjectName("CardGreen")

        form_wrap = QVBoxLayout(self.form_group)
        form = QFormLayout()
        form_wrap.addLayout(form)

        # hint (first row)
        self.settings_hint = QLabel(t(self.settings.language, "settings_hint"))
        self.settings_hint.setObjectName("SettingsHint")
        self.settings_hint.setWordWrap(True)
        form.addRow(self.settings_hint)

        # >>> CREATE INPUTS FIRST
        self.goal_spin = QSpinBox()
        self.goal_spin.setRange(1500, 3000)
        self.goal_spin.setSingleStep(100)
        self.goal_spin.setValue(self.settings.goal)

        self.sip_spin = QSpinBox()
        self.sip_spin.setRange(50, 1000)
        self.sip_spin.setSingleStep(50)
        self.sip_spin.setValue(self.settings.sip_size)

        self.interval_box = QComboBox()
        self.interval_options = {
            "EN": ["45 Min", "1 Hour", "1 Hour 15 Min", "1 Hour 30 Min"],
            "ZH": ["45分钟", "1小时", "1小时15分", "1小时30分"]
        }
        self._refresh_interval_options()

        # >>> THEN ADD ROWS USING THOSE INPUTS
        self.lbl_goal = QLabel(t(self.settings.language, "water_goal"))
        self.lbl_sip  = QLabel(t(self.settings.language, "sip_size"))
        self.lbl_intv = QLabel(t(self.settings.language, "interval"))

        form.addRow(self.lbl_goal, self.goal_spin)
        form.addRow(self.lbl_sip,  self.sip_spin)
        form.addRow(self.lbl_intv, self.interval_box)

        outer.addWidget(self.form_group)



        # Progress card
        self.progress_title_lbl = QLabel(t(self.settings.language, "progress_section"))
        self.progress_title_lbl.setObjectName("SectionTitleGray")
        outer.addWidget(self.progress_title_lbl)
        
        progress_group = QGroupBox()
        progress_group.setObjectName("CardGray") 
        p = QVBoxLayout(progress_group)
     

        self.progress_label = QLabel(self._progress_text())
        self.start_time = None  # 记录开始时间
        self.elapsed_label = QLabel("00:00:00")   # 显示已用时
        p.addWidget(self.elapsed_label)           # 放在“已饮 XXX ml”正下方
        # 计时器
        self.elapsed_timer = QTimer(self)
        self.elapsed_timer.timeout.connect(self._tick_elapsed)

        self.progress_bar = QProgressBar()
        self._update_progress_bar()
        p.addWidget(self.progress_label)
        p.addWidget(self.progress_bar)
        outer.addWidget(progress_group)


        # Controls
        btn_row1 = QHBoxLayout()
        self.start_btn = QPushButton(t(self.settings.language, "start"))
        self.start_btn.clicked.connect(self.start_reminders)
        self.pause_btn = QPushButton(t(self.settings.language, "pause"))
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.log_btn = QPushButton(t(self.settings.language, "log_sip"))
        self.log_btn.setEnabled(False)
        self.log_btn.clicked.connect(self.log_sip)
        self.reset_btn = QPushButton(t(self.settings.language, "reset_title"))
        self.reset_btn.clicked.connect(self.reset_form)
        btn_row1.addWidget(self.reset_btn)
        btn_row1.addWidget(self.start_btn)
        btn_row1.addWidget(self.pause_btn)
        btn_row1.addWidget(self.log_btn)
        outer.addLayout(btn_row1)

        # Dev test buttons (popups)
        if DEBUG_TEST_BUTTONS:
            btn_row2 = QHBoxLayout()
            self.test_water_btn = QPushButton(t(self.settings.language, "test_water"))
            self.test_water_btn.clicked.connect(self.water_reminder)
            self.test_sit_btn = QPushButton(t(self.settings.language, "test_sit"))
            self.test_sit_btn.clicked.connect(self.sedentary_reminder)
            btn_row2.addWidget(self.test_water_btn)
            btn_row2.addWidget(self.test_sit_btn)
            outer.addLayout(btn_row2)

        # Timers
        self.water_timer = QTimer(self)
        self.water_timer.timeout.connect(self.water_reminder)

        self.sedentary_timer = QTimer(self)
        self.sedentary_timer.timeout.connect(self.sedentary_reminder)

        # Tray
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(QIcon(resource_path("images/logo.png")))
        

        self.tray.setToolTip(t(self.settings.language, "tray_tooltip"))
        self._build_tray_menu()
        self.tray.show()

        # Inform defaults applied
        QMessageBox.information(self, t(self.settings.language, "reset_title"), t(self.settings.language, "reset_msg"))

        # Keep running in tray even if window closed
        QApplication.setQuitOnLastWindowClosed(False)

    def _format_hms(self, total_seconds: int) -> str:
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _tick_elapsed(self):
        if self.start_time is None:
            return
        secs = int((datetime.now() - self.start_time).total_seconds())
        if secs < 0:
            secs = 0
        self.elapsed_label.setText(self._format_hms(secs))
    def _set_inputs_enabled(self, enabled: bool):
        self.goal_spin.setEnabled(enabled)
        self.sip_spin.setEnabled(enabled)
        self.interval_box.setEnabled(enabled)

    def reset_form(self):
        # stop everything
        self.water_timer.stop()
        self.sedentary_timer.stop()
        self.elapsed_timer.stop()

        # state
        self.running = False
        self.paused = False
        self.start_time = None

        # unlock inputs and clear progress/time
        self._set_inputs_enabled(True)
        self.settings.water_progress = 0
        self._update_progress_bar()
        self.elapsed_label.setText("00:00:00")

        # buttons
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.log_btn.setEnabled(False)

        # optional: inform user (uses your existing strings)
        self.tray.showMessage(
            t(self.settings.language, "reset_title"),
            t(self.settings.language, "reset_msg"),
            QSystemTrayIcon.Information, 2000
        )
    # ---------------------- window/tray lifecycle ---------------------- #
    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage(
            t(self.settings.language, "tray_tooltip"),
            t(self.settings.language, "tip_hide"),
            QSystemTrayIcon.Information, 2000
        )

    def _build_tray_menu(self):
        menu = QMenu()
        act_show = menu.addAction(t(self.settings.language, "show"))
        act_show.triggered.connect(self._show_normal)

        act_log = menu.addAction(t(self.settings.language, "tray_log_sip"))
        act_log.triggered.connect(self.log_sip)

        self.act_pause_resume = menu.addAction(t(self.settings.language, "pause"))
        self.act_pause_resume.triggered.connect(self.toggle_pause)

        act_quit = menu.addAction(t(self.settings.language, "quit"))
        def do_quit():
            self.water_timer.stop()
            self.sedentary_timer.stop()
            self.tray.hide()
            QApplication.instance().quit()
        act_quit.triggered.connect(do_quit)

        self.tray.setContextMenu(menu)

    def _show_normal(self):
        self.show()
        self.raise_()
        self.activateWindow()

    # --------------------------- helpers/labels ------------------------ #
    def _progress_text(self):
        return t(self.settings.language, "progress").format(self.settings.water_progress, self.settings.goal)

    def _update_progress_bar(self):
        self.settings.water_progress = max(0, self.settings.water_progress)
        pct = int(round((self.settings.water_progress / max(1, self.settings.goal)) * 100))
        pct = max(0, min(100, pct))
        self.progress_bar.setValue(pct)
        self.progress_label.setText(self._progress_text())

    def _refresh_interval_options(self):
        self.interval_box.blockSignals(True)
        self.interval_box.clear()
        opts = self.interval_options.get(self.settings.language, self.interval_options["EN"])
        self.interval_box.addItems(opts)
        self.interval_box.setCurrentIndex(0)
        self.interval_box.blockSignals(False)

    # ------------------------------ state ------------------------------ #
    def on_lang_change(self, idx: int):
        # 1) switch language
        lang = "ZH" if idx == 1 else "EN"
        self.settings.language = lang

        # 2) app titles / headings
        self.title_label.setText(t(lang, "app_name"))
        self.setWindowTitle(t(lang, "title"))
        self.reco_title_lbl.setText(t(lang, "reco_title"))
        self.sed_title_lbl.setText(t(lang, "sed_title"))
        self.settings_title_lbl.setText(t(lang, "settings_title"))
        self.progress_title_lbl.setText(t(lang, "progress_section"))

        # 3) rich-text bodies
        self.settings_hint.setText(t(lang, "settings_hint"))
        self.sed_label.setText(t(lang, "sed_text"))
        self.reco_label.setText(t(lang, "reco_text"))
        self.reco_label.setOpenExternalLinks(True)
        self.reco_label.setTextFormat(Qt.RichText)
        self.reco_label.setWordWrap(True)

        # 4) buttons
        self.start_btn.setText(t(lang, "start") if not self.running else t(lang, "started"))
        self.pause_btn.setText(t(lang, "pause") if not self.paused else t(lang, "resume"))
        self.log_btn.setText(t(lang, "log_sip"))
        if DEBUG_TEST_BUTTONS:
            self.test_water_btn.setText(t(lang, "test_water"))
            self.test_sit_btn.setText(t(lang, "test_sit"))

        # 5) form field labels — these must be stored when you build the form:
        # self.lbl_goal, self.lbl_sip, self.lbl_intv
        self.lbl_goal.setText(t(lang, "water_goal"))
        self.lbl_sip.setText(t(lang, "sip_size"))
        self.lbl_intv.setText(t(lang, "interval"))

        # 6) rebuild interval options but KEEP the same minutes selected
        minutes = self.settings.interval_min
        self._refresh_interval_options()  # repopulates texts for current language
        text_by_min = {
            "EN": {45: "45 Min", 60: "1 Hour", 75: "1 Hour 15 Min", 90: "1 Hour 30 Min"},
            "ZH": {45: "45分钟", 60: "1小时", 75: "1小时15分", 90: "1小时30分"},
        }
        want = text_by_min[lang].get(minutes)
        if want is not None:
            i = self.interval_box.findText(want)
            if i != -1:
                self.interval_box.setCurrentIndex(i)

        # 7) progress text, tray/menu, save
        self._update_progress_bar()
        self._build_tray_menu()
        self.tray.setToolTip(t(lang, "tray_tooltip"))
        self.settings.save()

    def start_reminders(self):
        self.settings.goal = self.goal_spin.value()
        self.settings.sip_size = self.sip_spin.value()
        self.start_time = datetime.now()
        self.elapsed_label.setText("00:00:00")
        self.elapsed_timer.start(1000)  # 每秒更新一次


        interval_text = self.interval_box.currentText()
        map_min = {
            "45 Min": 45, "45分钟":45,
            "1 Hour": 60, "1小时": 60,
            "1 Hour 15 Min": 75, "1小时15分": 75,
            "1 Hour 30 Min": 90, "1小时30分": 90
        }
        self.settings.interval_min = map_min.get(interval_text, 60)

        self.settings.water_progress = 0
        self.settings.last_reset = str(datetime.now().date())
        self.settings.save()
        self._update_progress_bar()

        self.running = True
        self.paused = False

        self.water_timer.start(int(1.5 * 60 * 60 * 1000))  # 1.5 hours
        self.sedentary_timer.start(self.settings.interval_min * 60 * 1000)

        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.log_btn.setEnabled(True)

        self.tray.showMessage(
            t(self.settings.language, "tray_tooltip"),
            t(self.settings.language, "started"),
            QSystemTrayIcon.Information, 2000
        )
        self._set_inputs_enabled(False)
        self.water_reminder()          # 立即弹一次喝水
        # self.sedentary_reminder()      # 立即弹一次久坐


    def toggle_pause(self):
        if not self.running:
            return
        self.paused = not self.paused
        if self.paused:
            self.water_timer.stop()
            self.sedentary_timer.stop()
            self.elapsed_timer.stop()
            self.pause_btn.setText(t(self.settings.language, "resume"))
            self.act_pause_resume.setText(t(self.settings.language, "resume"))
            self.tray.showMessage(
                t(self.settings.language, "tray_tooltip"),
                t(self.settings.language, "paused"),
                QSystemTrayIcon.Information, 1500
            )
        else:
            self.water_timer.start(2 * 60 * 60 * 1000)
            self.sedentary_timer.start(self.settings.interval_min * 60 * 1000)
            if self.start_time is not None:
                self.elapsed_timer.start(1000)
            self.pause_btn.setText(t(self.settings.language, "pause"))
            self.act_pause_resume.setText(t(self.settings.language, "pause"))
            self.tray.showMessage(
                t(self.settings.language, "tray_tooltip"),
                t(self.settings.language, "resumed"),
                QSystemTrayIcon.Information, 1500
            )

    def log_sip(self):
        if not self.running or self.paused:
            return
        self.settings.water_progress += self.settings.sip_size
        self.settings.save()
        self._update_progress_bar()
        if self.settings.water_progress >= self.settings.goal:
            self.tray.showMessage(
                t(self.settings.language, "tray_tooltip"),
                t(self.settings.language, "goal_done"),
                QSystemTrayIcon.Information, 3000
            )

    # --------------------------- reminder UIs -------------------------- #
    def _show_image_dialog(self, title: str, text: str, img_path: str, is_gif: bool, auto_close_ms: int):
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setWindowIcon(QIcon(resource_path("images/logo.png")))
        dlg.setFixedSize(650, 650)
        v = QVBoxLayout(dlg)

        img_label = QLabel()
        if is_gif:
            movie = QMovie(resource_path("images/sit.gif"))
            movie.setScaledSize(QSize(500, 500))
            if not movie.isValid():
                img_label.setText(f"Missing GIF: {img_path}")
            else:
                img_label.setMovie(movie)
                movie.start()
        else:
            pix = QPixmap(resource_path(img_path)) 
            if pix.isNull():
                img_label.setText(f"Missing image: {img_path}")
            else:
                img_label.setPixmap(pix.scaled(475, 475, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        v.addWidget(img_label, alignment=Qt.AlignCenter)

        v.addWidget(QLabel(text), alignment=Qt.AlignCenter)

        if "Hydration" in title or "喝水" in title:
            live = QLabel(self._progress_text())
            v.addWidget(live, alignment=Qt.AlignCenter)
            bar = QProgressBar()
            pct = int(round((self.settings.water_progress / max(1, self.settings.goal)) * 100))
            bar.setValue(max(0, min(100, pct)))
            v.addWidget(bar)
            btn = QPushButton(t(self.settings.language, "log_sip"))
            def _log_and_update():
                self.log_sip()
                live.setText(self._progress_text())
                p2 = int(round((self.settings.water_progress / max(1, self.settings.goal)) * 100))
                bar.setValue(max(0, min(100, p2)))
            btn.clicked.connect(_log_and_update)
            v.addWidget(btn, alignment=Qt.AlignCenter)

        QTimer.singleShot(auto_close_ms, dlg.accept)
        dlg.exec_()

    def water_reminder(self):
        # allow manual test even if not running
        self._show_image_dialog(
            title=t(self.settings.language, "hydrate_time"),
            text=t(self.settings.language, "progress").format(self.settings.water_progress, self.settings.goal),
            img_path="images/water_remind.jpg",
            is_gif=False,
            auto_close_ms=5000
        )

    def sedentary_reminder(self):
        # allow manual test even if not running
        self._show_image_dialog(
            title=t(self.settings.language, "move_break"),
            text=t(self.settings.language, "move_msg"),
            img_path="images/sit.gif",
            is_gif=True,
            auto_close_ms=7000
        )

# --------------------------------- Main --------------------------------- #
def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    app.setApplicationName("健康生活小助手")
    app.setApplicationDisplayName("健康生活小助手")

    # Simple modern stylesheet (fonts, colors, buttons, progress bars)
    app.setStyleSheet("""
        QWidget {
            font-family: 'Microsoft YaHei', 'PingFang SC', 'Segoe UI', sans-serif;
            font-size: 12pt;
        }
        QMainWindow {
            background: #f7fbff;
        }
        
        #AppTitle {
            font-size: 18pt;
            font-weight: 700;
            color: #1b273a;
            padding: 6px 0 2px 0;
        }
        /* 基础：所有卡片的通用外观 */
        QGroupBox {
            background: #ffffff;             /* 纯白卡片 */
            border: 1px solid #e5eaf1;
            border-radius: 12px;
            margin-top: 14px;                /* 与上方间距 */
            padding: 14px 14px 12px 14px;    /* 内边距 */
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 2px 8px;
            font-weight: 600;
            color: #334155;                  /* 默认标题色 */
            background: transparent;         /* 保持透明，靠左侧色条区分 */
        }

        /* 蓝色卡：每日饮水 */
        #CardBlue {
            background: #f0f6ff;
            border: 1px solid #d7e3ff;
            border-left: 5px solid #3b82f6;  /* 左侧强调色条 */
        }
        #CardBlue::title {
            color: #1d4ed8;
        }
                      
        #SettingsGroup::title {        /* 仅作用于这个分组的标题 */
            font-weight: bold;
            color: #000000;
        }
        
        #CardGreen {
            background: #ecfdf5;             /* light green background */
            border: 1px solid #a7f3d0;
            border-left: 5px solid #10b981;  /* emerald stripe */
        }
        #CardGreen::title {
            color: #065f46;                   /* deep green title */
            font-weight: 700;
        }
        /* 灰色卡：进度条区域 */
        #CardGray {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-left: 5px solid #64748b;
        }
        #CardGray::title {
            color: #334155;}
                      
        /* Outside section headings (simple + clear) */
        #SectionTitleBlue  { font-size: 14pt; font-weight: 700; color: #1d4ed8; padding: 6px 2px 2px; }
        #SectionTitleGreen { font-size: 14pt; font-weight: 700; color: #15803d; padding: 6px 2px 2px; }
        #SectionTitleGray  { font-size: 14pt; font-weight: 700; color: #334155; padding: 6px 2px 2px; }

                    
        QPushButton {
            padding: 8px 14px;
            border-radius: 10px;
            background: #2b5aa6;
            color: #ffffff;
            border: 0;
        }
        QPushButton:hover { background: #3a6edc; }
        QPushButton:disabled { background: #aab7c4; }
        QProgressBar {
            height: 16px;
            border: 1px solid #c9d6ea;
            border-radius: 8px;
            text-align: center;
            background: #eef4ff;
        }
        QProgressBar::chunk {
            border-radius: 8px;
            background-color: #4aa3ff;
        }
        QLabel {
            color: #1b273a;
        }
    """)

    app.setWindowIcon(QIcon(resource_path("images/logo.png")))

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

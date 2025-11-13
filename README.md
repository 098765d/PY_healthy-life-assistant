# Desk Health Reminder （健康生活小助手）
[![release](https://img.shields.io/github/v/release/098765d/PY_healthy-life-assistant?label=release)](https://github.com/098765d/PY_healthy-life-assistant/releases)
[![license](https://img.shields.io/github/license/098765d/PY_healthy-life-assistant)](LICENSE)
![python](https://img.shields.io/badge/Python-3.x-blue)
![pyqt5](https://img.shields.io/badge/PyQt-5-brightgreen)
![platform](https://img.shields.io/badge/Platform-Windows-informational)
[![Bilibili](https://img.shields.io/badge/Video-Bilibili-ff69b4)](https://www.bilibili.com/video/BV1W7kkBcEuX/?share_source=copy_web&vd_source=f23fdab1cf57871b257305ebe143b9c2)


A lightweight Windows desktop app (PyQt5) that reminds you to **drink water** and **take standing/moving breaks**.  
一个轻量的 Windows 桌面应用（PyQt5），用于**提醒喝水**与**久坐起身活动**，支持中英双语、进度记录、**活动记录**与**当日记录报告**。

**Download / 小助手下载：**  
➡️ [Click to download app.exe](https://github.com/098765d/PY_healthy-life-assistant/releases/download/v0.0.2/default.exe)

---

## ✨ Features | 功能

- ⏱️ **Hydration reminder** with image popup  
  **喝水提醒**（弹窗）
- 🪑 **Anti-sedentary reminder** with GIF popup (**custom interval**)  
  **久坐提醒**（弹窗，间隔可选）
- 📈 **Progress tracking**: daily target + sip size + live bar  
  **进度记录**：每日饮水目标 / 每次饮水量 / 实时进度条
- 🚶 **Activity Log**: one-click “Log Activity” adds a small GIF & counter  
  **活动记录**：点击“记录活动”，增加图标与计数
- 📝 **Daily Report (TXT)**: press **结束/下班** to export a concise report  
  **当日报告（TXT）**：点击**结束/下班**导出当日饮水&活动报告
- ▶️/⏸️ **Accurate pause/resume** (elapsed time excludes pause)  
  **暂停/继续**计时准确（暂停时长不计入运行时间）
- 🛟 **System tray**: Show / Pause / Quit  
  **系统托盘**：显示 / 暂停 / 退出
- 🌐 **Bilingual UI** (中文 / English)  

---
## 🎬 Demo| 演示

[【自制软件】办公久坐救星！Python做的桌面健康小助手：提醒喝水＋久坐弹窗＋进度统计](https://www.bilibili.com/video/BV1W7kkBcEuX/?share_source=copy_web&vd_source=f23fdab1cf57871b257305ebe143b9c2)

![App Screenshot](https://github.com/098765d/PY_healthy-life-assistant/blob/2fea5563fe65d1bfbb45f20aa494f3860aeba6a0/%E6%88%AA%E5%9B%BE.png)

## 🧭 Quick Start | 使用
1. **Set goals / 设定**  
   - 输入每日饮水目标（ml）与每次饮水量（ml）  
   - 选择久坐提醒间隔（45/60/75/90 分钟）
2. **Click Start / 点击开始**  
   - 开始后，输入区域将锁定；若需修改，点击**重置**  
   - 右上角 **X** 仅最小化到托盘，不会退出
3. **Log / 记录**  
   - **记录一口**：累计饮水进度  
   - **记录活动**：增加一次活动计数，并在进度卡片下方显示小图标
4. **Pause / Resume / 暂停与继续**  
   - 暂停后计时冻结；继续后计时准确衔接
5. **Popups / 弹窗提醒**  
   - 喝水弹窗持续 **5 秒**，久坐弹窗持续 **7 秒**（可手动关闭或自动消失）
6. **End of day / 结束当日**  
   - 点击 **结束/下班** 导出 TXT 报告（文件名示例：`健康报告report_20251112.txt`）
     

## 📚 参考资料 / References

1) 中国营养学会. (2022). 《中国居民膳食指南（2022）》
   取自 http://dg.cnsoc.org/article/04/wDCyy7cWSJCN6pwKHOo5Dw.html

2) World Health Organization. (2020). Guidelines on physical activity and sedentary behaviour.
   https://www.who.int/publications/i/item/9789240015128

3) EFSA Panel on Dietetic Products, Nutrition and Allergies (NDA). (2010). Scientific Opinion on Dietary Reference Values for water. *EFSA Journal, 8*(3), 1459. 
   https://efsa.onlinelibrary.wiley.com/doi/10.2903/j.efsa.2010.1459

4) Biswas, A., Oh, P. I., Faulkner, G. E., Bajaj, R. R., Silver, M. A., Mitchell, M. S., & Alter, D. A. (2015). Sedentary time and its association with risk for disease incidence, mortality, and hospitalization in adults: A systematic review and meta-analysis. *Annals of Internal Medicine, 162*(2), 123–132. 
   https://doi.org/10.7326/M14-1651

5) Young, Deborah Rohm, et al. "Sedentary behavior and cardiovascular morbidity and mortality: a science advisory from the American Heart Association." Circulation 134.13 (2016): e262-e279. https://www.ahajournals.org/doi/full/10.1161/CIR.0000000000000440



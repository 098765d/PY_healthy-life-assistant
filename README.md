# Desk Health Reminder （健康生活小助手）

[![license](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
![python]( https://img.shields.io/badge/Python-3.13.1-blue)
![pyqt5]( https://img.shields.io/badge/PyQt-5.15.11-brightgreen)
![platform]( https://img.shields.io/badge/Platform-Windows-informational)
[![Bilibili](https://img.shields.io/badge/Video-演示视频-ff69b4)]( https://www.bilibili.com/video/BV1W7kkBcEuX/?share_source=copy_web&vd_source=f23fdab1cf57871b257305ebe143b9c2)
![GitHub Repo stars]( https://img.shields.io/github/stars/098765d/PY_healthy-life-assistant?style=social)


A lightweight Windows desktop app (PyQt5) that reminds you to **drink water** and **take standing/moving breaks**.  
一个轻量的 Windows 桌面应用（PyQt5），用于**提醒喝水**与**久坐起身活动**，支持中英双语、进度记录、**活动记录**与**当日记录报告**。

**Download / 健康生活小助手App下载 (Windows应用)：**  
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

1. Jacques, P. F., Rogers, G., Stookey, J. D., & Perrier, E. T. (2021). Water intake and markers of hydration are related to cardiometabolic risk biomarkers in community-dwelling older adults: a cross-sectional analysis. The Journal of Nutrition, 151(10), 3205-3213.
2. Ku, P. W., Steptoe, A., Liao, Y., Hsueh, M. C., & Chen, L. J. (2019). A threshold of objectively-assessed daily sedentary time for all-cause mortality in older adults: a meta-regression of prospective cohort studies. Journal of clinical medicine, 8(4), 564.
3. Mazaheri-Tehrani, S., Arefian, M., Abhari, A. P., Riahi, R., Vahdatpour, B., Mahdavi, S. B., & Kelishadi, R. (2023). Sedentary behavior and neck pain in adults: A systematic review and meta-analysis. Preventive Medicine, 175, 107711.
4. Wittbrodt, M. T., & Millard-Stafford, M. (2018). Dehydration impairs cognitive performance: a meta-analysis. Med Sci Sports Exerc, 50 (11), 2360-2368.
5. Wilmot, E. G., Edwardson, C. L., Achana, F. A., Davies, M. J., Gorely, T., Gray, L. J., ... & Biddle, S. J. (2012). Sedentary time in adults and the association with diabetes, cardiovascular disease and death: systematic review and meta-analysis. Diabetologia, 55(11), 2895-2905.
6. Young, D. R., Hivert, M. F., Alhassan, S., Camhi, S. M., Ferguson, J. F., Katzmarzyk, P. T., ... & Yong, C. M. (2016). Sedentary behavior and cardiovascular morbidity and mortality: a science advisory from the American Heart Association. Circulation, 134(13), e262-e279.
7. Wang, J. S., Chiang, H. Y., Chen, H. L., Flores, M., Navas-Acien, A., & Kuo, C. C. (2022). Association of water intake and hydration status with risk of kidney stone formation based on NHANES 2009–2012 cycles. Public Health Nutrition, 25(9), 2403-2414.
8. 中国营养学会. (2022). 《中国居民膳食指南（2022）》 取自 http://dg.cnsoc.org/article/04/wDCyy7cWSJCN6pwKHOo5Dw.html




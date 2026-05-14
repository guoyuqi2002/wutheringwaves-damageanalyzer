# DamageAnalyzer

一个独立的视觉伤害统计悬浮窗工具。

目标：不读取游戏内存、不注入、不 Hook，只通过截图识别伤害数字，实时统计战斗中的总伤害、DPS，并逐步支持 1/2/3 号位归因。

## 技术路线

- 截图：`mss` / 后续可替换为 `dxcam`
- 图像处理：`opencv-python`
- OCR：先预留接口，后续接入 PaddleOCR / ONNXOCR / 自训练数字模型
- 悬浮窗：`PySide6`
- 统计逻辑：多帧追踪、去重、归因

`mss` 是跨平台截图库，支持和 NumPy/OpenCV 配合使用；PySide6/Qt 可用 `WindowStaysOnTopHint` 实现置顶窗口；OpenCV 可用于灰度、阈值化等预处理。  
参考：mss 文档、Qt for Python 文档、OpenCV threshold 文档。

## 项目结构

```text
DamageAnalyzer/
├─ main.py
├─ config.py
├─ capture/
│  └─ window_capture.py
├─ detect/
│  └─ damage_ocr.py
├─ track/
│  └─ damage_tracker.py
├─ logic/
│  └─ attribution.py
├─ ui/
│  └─ overlay.py
└─ README.md
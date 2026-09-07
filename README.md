# 表情镜像头盔（鹤望兰号 Strelizia 风格）

内部红外摄像头识别佩戴者表情 → 外部大屏显示「红色动漫发光眼 + 发光嘴」。
完整技术方案见 `表情镜像头盔方案.md`。

## 当前进度：M3（占位发光眼 + 发光嘴渲染）

## 环境
- 开发机：Windows（OpenCV + MediaPipe + pygame，跨平台）
- 最终部署：树莓派 5（后续用 picamera2 替换采集层）

## 安装
```bash
pip install -r requirements.txt
```
> 首次运行会自动下载 MediaPipe 人脸模型 `face_landmarker.task`（约 4MB，需联网）。
> 若 `import pygame` 失败，可 `pip install pygame-ce`（import 名不变）。

## 运行
```bash
python main.py             # 摄像头驱动 + 手动按键
python main.py --demo      # 自动循环展示所有表情（无需摄像头）
python main.py --no-camera # 仅手动按键，不读摄像头
python main.py --camera 1  # 指定摄像头
```

## 操作
- 自动（人脸识别）：无表情 / 微笑 / 惊讶(张嘴) / 生气(皱眉) / 眨眼
- 手动按键：1无表情 2大笑 3害羞 4坏笑
- `d`：切换演示循环
- `q` 或 `ESC`：退出

## 文件说明
- `capture.py` — 采集封装（opencv，后续加 picamera2）
- `face.py` — MediaPipe Face Landmarker + 模型下载
- `expression.py` — 自动表情检测（眨眼/惊讶/生气/微笑）
- `render.py` — 发光眼 + 发光嘴渲染（占位矢量版）
- `main.py` — 主循环

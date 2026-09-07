"""MediaPipe Face Landmarker 封装（新版 Tasks API）。

输出 478 个关键点（468 + 10 iris），以及表情 blendshape 系数（M2 直接用）。
"""
import os
import urllib.request

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)
MODEL_PATH = "face_landmarker.task"


def ensure_model():
    """模型文件不存在时自动下载。"""
    if os.path.exists(MODEL_PATH):
        return MODEL_PATH
    print("未找到模型 face_landmarker.task，正在下载（约 4MB）...")
    try:
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("模型下载完成。")
    except Exception as e:
        print(f"下载失败：{e}")
        print(f"请手动下载模型并放到当前目录，命名为 {MODEL_PATH}。")
        print(f"下载地址：{MODEL_URL}")
        raise
    return MODEL_PATH


class FaceLandmarker:
    """封装 MediaPipe Face Landmarker（VIDEO 模式，实时视频流）。"""

    def __init__(self, num_faces=1):
        model = ensure_model()
        options = vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=num_faces,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=False,
        )
        self._detector = vision.FaceLandmarker.create_from_options(options)
        self._frame_id = 0

    def process(self, bgr_frame):
        """返回 FaceLandmarkerResult（含 face_landmarks / face_blendshapes）。"""
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        self._frame_id += 1  # VIDEO 模式要求时间戳单调递增，帧序号即可
        return self._detector.detect_for_video(mp_image, self._frame_id)

    @staticmethod
    def landmarks_to_array(landmarks):
        """478 个关键点 → numpy (N, 3)，列 = [x, y, z]，归一化坐标。"""
        return np.array([[p.x, p.y, p.z] for p in landmarks])

    @staticmethod
    def blendshapes_to_dict(blendshapes):
        """blendshape 列表 → {名称: 分数} 字典。"""
        return {c.category_name: c.score for c in blendshapes}

    def close(self):
        self._detector.close()

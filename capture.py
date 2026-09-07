"""摄像头采集封装。

Windows / 通用平台用 OpenCV；树莓派上后续在此处切换到 picamera2。
业务逻辑（face.py / main.py）不感知采集后端，切换平台只改这个文件。
"""
import cv2


class OpenCVCapture:
    """基于 OpenCV 的摄像头采集（Windows 内置/USB 摄像头）。"""

    def __init__(self, index=0, width=640, height=480):
        self._cap = cv2.VideoCapture(index)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if not self._cap.isOpened():
            raise RuntimeError(
                f"无法打开摄像头 index={index}，请检查设备，或用 --camera 指定其它索引"
            )

    def read(self):
        """返回 (ok, bgr_frame)。"""
        return self._cap.read()

    def release(self):
        self._cap.release()


def create_capture(backend="opencv", index=0, width=640, height=480):
    """统一采集入口。后续加 picamera2 分支时只改这里。"""
    if backend == "opencv":
        return OpenCVCapture(index=index, width=width, height=height)
    # elif backend == "picamera2":
    #     return Picamera2Capture(...)  # 树莓派阶段再加
    raise ValueError(f"未知采集后端: {backend}")

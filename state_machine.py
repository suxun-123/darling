"""表情状态机：去抖 + 滞后，避免阈值附近来回跳变（闪烁）。"""


class ExpressionStateMachine:
    """同一新表情连续出现 N 帧才切换，防止抖动；瞬时表情立即切换。"""

    def __init__(self, hold_frames=4):
        self.current = "neutral"
        self._candidate = "neutral"
        self._count = 0
        self.hold_frames = hold_frames
        self.transient = {"blink", "wink"}  # 眨眼很短，不能被去抖吃掉

    def update(self, label):
        """输入每帧分类结果，返回 (稳定表情, 是否变化)。"""
        # 瞬时表情（眨眼/坏笑）立即切换
        if label in self.transient:
            changed = label != self.current
            self.current = label
            self._candidate = label
            self._count = 0
            return self.current, changed

        if label == self._candidate:
            self._count += 1
        else:
            self._candidate = label
            self._count = 1

        if self._count >= self.hold_frames and self._candidate != self.current:
            self.current = self._candidate
            return self.current, True
        return self.current, False

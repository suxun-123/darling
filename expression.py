"""自动表情检测：无表情 / 惊讶 / 生气 / 眨眼 / 微笑（其余表情手动切换）。

优先级：眨眼 > 惊讶 > 生气 > 微笑 > 无（返回 None 时用手动基础表情）。
"""


class AutoExpressionDetector:
    """从 blendshape 检测自动表情，带迟滞/去抖避免抖动。"""

    TH_BLINK = 0.45        # 眨眼
    TH_SMILE = 0.35        # 微笑
    TH_JAW_OPEN = 0.45     # 张嘴=惊讶（触发）
    TH_JAW_CLOSE = 0.28    # 张嘴（回落，迟滞）
    TH_BROW_DOWN = 0.22    # 生气：眉下压
    TH_EYE_SQUINT = 0.40   # 生气辅助：眯眼
    ANGRY_HOLD = 3         # 生气去抖帧数

    def __init__(self):
        self._mouth_open = False
        self._angry_count = 0

    def detect(self, bs):
        """返回自动表情标签之一：blink / surprised / angry / smile / None。"""
        blink_l = bs.get("eyeBlinkLeft", 0.0)
        blink_r = bs.get("eyeBlinkRight", 0.0)
        jaw = bs.get("jawOpen", 0.0)
        brow_down = max(bs.get("browDownLeft", 0.0), bs.get("browDownRight", 0.0))
        eye_squint = max(bs.get("eyeSquintLeft", 0.0), bs.get("eyeSquintRight", 0.0))
        smile = max(bs.get("mouthSmileLeft", 0.0), bs.get("mouthSmileRight", 0.0))

        # 1) 眨眼（最高优先级，瞬时）
        if max(blink_l, blink_r) > self.TH_BLINK:
            return "blink"

        # 2) 惊讶：张嘴（带迟滞）
        if not self._mouth_open and jaw > self.TH_JAW_OPEN:
            self._mouth_open = True
        elif self._mouth_open and jaw < self.TH_JAW_CLOSE:
            self._mouth_open = False
        if self._mouth_open:
            return "surprised"

        # 3) 生气：眉下压（或 + 眯眼），带去抖
        is_angry = brow_down > self.TH_BROW_DOWN or (
            brow_down > self.TH_BROW_DOWN * 0.6 and eye_squint > self.TH_EYE_SQUINT
        )
        if is_angry:
            self._angry_count = min(self._angry_count + 1, self.ANGRY_HOLD + 2)
        else:
            self._angry_count = max(self._angry_count - 1, 0)
        if self._angry_count >= self.ANGRY_HOLD:
            return "angry"

        # 4) 微笑
        if smile > self.TH_SMILE:
            return "smile"

        return None  # 无自动表情 → 用手动基础表情


def blendshapes_to_params(bs):
    """blendshape 系数 → 连续渲染参数（VTuber 式，无离散跳转）。

    MediaPipe 输出 52 个 ARKit blendshape 系数（0~1），这里把关键几个
    直接连续映射成渲染参数，而不是先分类成某个表情再跳转：

      eye_open_l / eye_open_r : 左右眼开合 0~1.3（眨眼=闭、eyeWide=瞪大、eyeSquint=眯）
      eye_curve               : 眼角弧度 -1~1（负=眉下压/怒，0=平）
      mouth_open              : 张嘴 0~1（jawOpen 连续）
      mouth_curve             : 嘴角弧度 -1~1（正=微笑上翘，负=下撇）
      blush                   : 0（脸红由手动叠加，见 main.py）
    """
    def avg(*names):
        return sum(bs.get(n, 0.0) for n in names) / len(names)

    blink_l = bs.get("eyeBlinkLeft", 0.0)
    blink_r = bs.get("eyeBlinkRight", 0.0)
    squint = avg("eyeSquintLeft", "eyeSquintRight")
    wide = avg("eyeWideLeft", "eyeWideRight")
    brow = avg("browDownLeft", "browDownRight")
    jaw = bs.get("jawOpen", 0.0)
    smile = avg("mouthSmileLeft", "mouthSmileRight")
    frown = avg("mouthFrownLeft", "mouthFrownRight")

    def eye_open(blink):
        v = 1.0 + 0.35 * wide - 1.0 * blink - 0.4 * squint
        return max(0.0, min(1.35, v))

    eye_curve = max(-1.0, min(1.0, -0.9 * brow - 0.4 * squint))
    mouth_open = max(0.0, min(1.0, jaw))
    mouth_curve = max(-1.0, min(1.0, smile - frown))

    return dict(
        eye_open_l=eye_open(blink_l),
        eye_open_r=eye_open(blink_r),
        eye_curve=eye_curve,
        mouth_open=mouth_open,
        mouth_curve=mouth_curve,
        blush=0.0,
    )

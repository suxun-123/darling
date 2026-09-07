"""发光眼 + 发光嘴渲染（M4，鹤望兰号风格 · 橙黄发光）。

分层渲染（自上而下）：
  1. 白色背景
  2. 面甲底图（assets/face/faceplate.png，可选）—— 整张面甲完整还原
  3. 盖住面甲上烘烤的眼/嘴（白色补丁）
  4. 眼睛（AI 图或矢量占位，橙黄发光）
  5. 嘴（AI 图或矢量占位）
  6. 脸红 / 光晕（程序化）

接口：renderer.set_expression(expr, blink) → renderer.step() → renderer.draw(surface)
AI 素材缺失时自动回退到矢量占位，且眼/嘴/面甲各自独立可选。
"""
import json
import math
import os

import pygame

# 每个表情的目标参数
#   eye_open:   0=闭 1=睁 >1=瞪大
#   eye_curve:  <0 怒/垂，0 平，>0 笑眼上弯
#   mouth_open: 0=闭 1=大张
#   mouth_curve:<0 下撇，0 平，>0 上翘(笑)
#   blush:      0~1 脸红程度
EXPRESSION_TARGETS = {
    "neutral":   dict(eye_open_l=0.90, eye_open_r=0.90, eye_curve=0.0,  mouth_open=0.10, mouth_curve=0.0,  blush=0.0),
    "smile":     dict(eye_open_l=0.85, eye_open_r=0.85, eye_curve=0.0,  mouth_open=0.20, mouth_curve=0.7,  blush=0.0),
    "surprised": dict(eye_open_l=1.30, eye_open_r=1.30, eye_curve=0.0,  mouth_open=0.85, mouth_curve=0.0,  blush=0.0),
    "angry":     dict(eye_open_l=0.45, eye_open_r=0.45, eye_curve=-0.7, mouth_open=0.15, mouth_curve=-0.5, blush=0.0),
    "blink":     dict(eye_open_l=0.0,  eye_open_r=0.0,  eye_curve=0.0,  mouth_open=0.10, mouth_curve=0.0,  blush=0.0),
    "laugh":     dict(eye_open_l=0.90, eye_open_r=0.90, eye_curve=0.0,  mouth_open=0.90, mouth_curve=1.0,  blush=0.0),
    "blush":     dict(eye_open_l=0.80, eye_open_r=0.80, eye_curve=0.0,  mouth_open=0.25, mouth_curve=0.5,  blush=1.0),
    "wink":      dict(eye_open_l=0.0,  eye_open_r=0.85, eye_curve=0.0,  mouth_open=0.25, mouth_curve=0.5,  blush=0.0),
}

EYE_COLOR = (255, 150, 20)    # 鹤望兰号橙黄眼
MOUTH_COLOR = (255, 150, 20)  # 鹤望兰号橙黄嘴

# 素材文件名约定
ASSET_EYES = {
    "neutral": "eye_neutral.png",
    "angry":   "eye_angry.png",
    "wide":    "eye_wide.png",
}
ASSET_MOUTH = {
    "neutral": "mouth_neutral.png",
    "smile":   "mouth_smile.png",
    "open":    "mouth_open.png",
    "frown":   "mouth_frown.png",
}

# 布局（眼/嘴在整张面甲图上的位置与大小；头部特写带头盔时，可按键校准）
_HERE = os.path.dirname(os.path.abspath(__file__))
LAYOUT_PATH = os.path.join(_HERE, "layout.json")

DEFAULT_LAYOUT = {
    "eye_y": 0.36,       # 眼睛中心高度（占屏高比例）
    "eye_dx": 0.17,      # 眼睛水平间距一半（占屏宽比例）
    "mouth_y": 0.66,     # 嘴中心高度（占屏高比例）
    "eye_scale": 1.0,    # 眼睛大小倍率
    "mouth_scale": 1.0,  # 嘴大小倍率
}


def load_layout(path=LAYOUT_PATH):
    d = dict(DEFAULT_LAYOUT)
    try:
        with open(path, "r", encoding="utf-8") as f:
            d.update(json.load(f))
    except Exception:
        pass
    return d


def save_layout(d, path=LAYOUT_PATH):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)


def _load_png(path):
    if os.path.exists(path):
        try:
            return pygame.image.load(path).convert_alpha()
        except Exception:
            return None
    return None


def load_assets(assets_dir="assets"):
    """按需加载：面甲/眼/嘴各自独立可选，缺啥就回退啥。"""
    assets = {}
    fp = _load_png(os.path.join(assets_dir, "face", "faceplate.png"))
    if fp is not None:
        assets["faceplate"] = fp
    eyes = {k: _load_png(os.path.join(assets_dir, "eyes", fn))
            for k, fn in ASSET_EYES.items()}
    eyes = {k: v for k, v in eyes.items() if v is not None}
    if eyes:
        assets["eyes"] = eyes
    mouths = {k: _load_png(os.path.join(assets_dir, "mouth", fn))
              for k, fn in ASSET_MOUTH.items()}
    mouths = {k: v for k, v in mouths.items() if v is not None}
    if mouths:
        assets["mouths"] = mouths
    return assets


class FaceRenderer:
    def __init__(self, size=(600, 900), assets_dir="assets"):
        self.size = size
        self.bg = (255, 255, 255)
        self.assets = load_assets(assets_dir)
        self.layout = load_layout()
        # 面甲按比例居中显示（不拉伸），无面甲则整窗
        fp = self.assets.get("faceplate")
        if fp is None:
            self._face_rect = (0, 0, size[0], size[1])
        else:
            iw, ih = fp.get_size()
            s = min(size[0] / iw, size[1] / ih)
            nw, nh = int(iw * s), int(ih * s)
            self._face_rect = ((size[0] - nw) // 2, (size[1] - nh) // 2, nw, nh)
        self.face_w = self._face_rect[2]
        self.face_h = self._face_rect[3]
        # 连续模式：眼/嘴用程序化曲线（嘴角眼角连续跟随），面甲仍可叠 AI 图
        self.continuous = False
        # 当前平滑参数（初始 neutral）
        self.params = dict(EXPRESSION_TARGETS["neutral"])
        self._target = dict(self.params)
        self._rates = {
            "eye_open_l": 0.45, "eye_open_r": 0.45, "eye_curve": 0.18,
            "mouth_open": 0.22, "mouth_curve": 0.22, "blush": 0.12,
        }
        # AI 素材的变体过渡状态
        self._eye_cur = "neutral"
        self._eye_prev = "neutral"
        self._eye_blend = 1.0
        self._mouth_cur = "neutral"
        self._mouth_prev = "neutral"
        self._mouth_blend = 1.0

    def set_expression(self, expression, blink=0.0):
        t = EXPRESSION_TARGETS.get(expression, EXPRESSION_TARGETS["neutral"])
        for k, v in t.items():
            self._target[k] = v
        if blink:
            self._target["eye_open_l"] *= max(0.0, 1.0 - blink)
            self._target["eye_open_r"] *= max(0.0, 1.0 - blink)

    def set_params(self, params):
        """连续模式：直接把连续参数写入目标（VTuber 式，无离散跳转）。"""
        for k, v in params.items():
            self._target[k] = v

    def step(self):
        for k, v in self._target.items():
            self.params[k] += (v - self.params[k]) * self._rates.get(k, 0.2)

    def draw(self, surface):
        surface.fill(self.bg)
        w, h = surface.get_size()
        fx, fy, fw, fh = self._face_rect
        cx = fx + fw // 2
        eye_y = fy + int(fh * self.layout["eye_y"])
        eye_dx = int(fw * self.layout["eye_dx"])
        mouth_y = fy + int(fh * self.layout["mouth_y"])
        p = self.params
        left_open = p["eye_open_l"]

        if self.assets.get("faceplate"):
            self._draw_faceplate(surface)
            self._blank_sockets(surface, cx, eye_y, eye_dx, mouth_y)

        use_ai_eyes = (not self.continuous) and bool(self.assets.get("eyes"))
        if use_ai_eyes:
            self._draw_eyes_ai(surface, cx, eye_y, eye_dx, left_open)
        else:
            self._draw_eyes_procedural(surface, cx, eye_y, eye_dx, left_open)

        use_ai_mouth = (not self.continuous) and bool(self.assets.get("mouths"))
        if use_ai_mouth:
            self._draw_mouth_ai(surface, cx, mouth_y)
        else:
            self._draw_mouth_procedural(surface, cx, mouth_y)

        if p["blush"] > 0.05:
            self._draw_blush(surface, cx - eye_dx, eye_y, p["blush"])
            self._draw_blush(surface, cx + eye_dx, eye_y, p["blush"])

    # ============ 面甲 ============

    def _draw_faceplate(self, surface):
        fx, fy, fw, fh = self._face_rect
        img = self.assets["faceplate"]
        surface.blit(pygame.transform.smoothscale(img, (fw, fh)), (fx, fy))

    def _blank_sockets(self, surface, cx, eye_y, eye_dx, mouth_y):
        """用白色补丁盖住面甲上烘烤的眼/嘴，避免与动画层重影。"""
        w = self.face_w
        tw = int(w * 0.16 * self.layout["eye_scale"])
        for ex in (cx - eye_dx, cx + eye_dx):
            pygame.draw.ellipse(surface, self.bg,
                                pygame.Rect(ex - tw // 2, eye_y - tw // 2, tw, tw))
        mw = int(w * 0.20 * self.layout["mouth_scale"])
        pygame.draw.ellipse(surface, self.bg,
                            pygame.Rect(cx - mw // 2, mouth_y - mw // 3, mw, mw * 2 // 3))

    # ============ AI 素材路径 ============

    def _eye_img(self, key):
        eyes = self.assets.get("eyes", {})
        return eyes.get(key) or eyes.get("neutral")

    def _mouth_img(self, key):
        mouths = self.assets.get("mouths", {})
        return mouths.get(key) or mouths.get("neutral")

    def _pick_eye_variant(self, openness, curve):
        if curve < -0.3:
            return "angry"
        if openness > 1.1:
            return "wide"
        return "neutral"

    def _pick_mouth_variant(self, openness, curve):
        if openness > 0.45:
            return "open"
        if curve > 0.25:
            return "smile"
        if curve < -0.25:
            return "frown"
        return "neutral"

    def _advance(self, new_var, cur_attr, prev_attr, blend_attr):
        cur = getattr(self, cur_attr)
        if new_var != cur:
            setattr(self, prev_attr, cur)
            setattr(self, cur_attr, new_var)
            setattr(self, blend_attr, 0.0)
        else:
            b = getattr(self, blend_attr)
            setattr(self, blend_attr, min(1.0, b + 0.15))

    def _draw_eyes_ai(self, surface, cx, eye_y, eye_dx, left_open):
        p = self.params
        ev = self._pick_eye_variant(p["eye_open_l"], p["eye_curve"])
        self._advance(ev, "_eye_cur", "_eye_prev", "_eye_blend")
        w = surface.get_width()
        for ex, op in ((cx - eye_dx, left_open), (cx + eye_dx, p["eye_open_r"])):
            self._glow(surface, (ex, eye_y), int(w * 0.10), EYE_COLOR,
                       0.6 if op > 1.1 else 0.4)
            self._blit_with_fade(surface, ex, eye_y,
                                 self._eye_img(self._eye_prev),
                                 self._eye_img(self._eye_cur),
                                 self._eye_blend, op, width_ratio=0.15, mouth=False)

    def _draw_mouth_ai(self, surface, cx, mouth_y):
        p = self.params
        mv = self._pick_mouth_variant(p["mouth_open"], p["mouth_curve"])
        self._advance(mv, "_mouth_cur", "_mouth_prev", "_mouth_blend")
        self._glow(surface, (cx, mouth_y), int(surface.get_width() * 0.10), MOUTH_COLOR, 0.4)
        self._blit_with_fade(surface, cx, mouth_y,
                             self._mouth_img(self._mouth_prev),
                             self._mouth_img(self._mouth_cur),
                             self._mouth_blend, p["mouth_open"], width_ratio=0.18, mouth=True)

    def _blit_with_fade(self, surface, cx, cy, prev_img, cur_img, blend, openness, width_ratio, mouth):
        if prev_img is not None and blend < 1.0:
            self._blit_part(surface, cx, cy, prev_img, openness, width_ratio, mouth, alpha=1.0 - blend)
        if cur_img is not None:
            self._blit_part(surface, cx, cy, cur_img, openness, width_ratio, mouth, alpha=blend)

    def _blit_part(self, surface, cx, cy, img, openness, width_ratio, mouth, alpha):
        if openness <= 0.03:
            return
        iw, ih = img.get_size()
        tw = int(self.size[0] * width_ratio)
        if mouth and openness > 0.45:
            scale = max(0.5, openness)
        else:
            scale = openness
        th = max(1, int(tw * (ih / iw) * scale))
        scaled = pygame.transform.smoothscale(img, (tw, th))
        if alpha < 1.0:
            scaled.set_alpha(int(255 * alpha))
        surface.blit(scaled, (cx - tw // 2, cy - th // 2))

    # ============ 矢量占位路径（无素材时兜底） ============

    def _draw_eyes_procedural(self, surface, cx, eye_y, eye_dx, left_open):
        p = self.params
        self._draw_eye(surface, cx - eye_dx, eye_y, left_open, p["eye_curve"])
        self._draw_eye(surface, cx + eye_dx, eye_y, p["eye_open_r"], p["eye_curve"])

    def _draw_mouth_procedural(self, surface, cx, mouth_y):
        p = self.params
        self._draw_mouth(surface, cx, mouth_y, p["mouth_open"], p["mouth_curve"])

    # ============ 共用 ============

    def _glow(self, surface, center, radius, color, intensity=1.0):
        if radius <= 0:
            return
        r = int(radius)
        glow = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        c = r + 1
        steps = 10
        for i in range(steps, 0, -1):
            rr = int(r * i / steps)
            a = int(70 * intensity * (i / steps) ** 2)
            pygame.draw.circle(glow, (*color, a), (c, c), rr)
        surface.blit(glow, (center[0] - c, center[1] - c))

    def _draw_eye(self, surface, cx, cy, openness, curve):
        base_w = int(self.face_w * 0.11 * self.layout["eye_scale"])
        base_h = int(self.face_w * 0.032 * self.layout["eye_scale"])
        color = EYE_COLOR

        if openness <= 0.03:
            return

        hh = max(1, int(base_h * openness * 2))
        ww = int(base_w * (1.25 if openness > 1.1 else 1.0))
        glow_r = int(base_w * 0.9)

        self._glow(surface, (cx, cy), glow_r, color, 0.9 if openness > 1.1 else 0.6)

        if curve < -0.3:
            pygame.draw.line(surface, color,
                             (cx - ww // 2, cy), (cx + ww // 2, cy - hh), max(3, hh))
            pygame.draw.line(surface, color,
                             (cx - ww // 2, cy - hh - int(base_h * 1.6)),
                             (cx + ww // 2, cy - hh - int(base_h * 0.6)), 3)
        elif openness > 1.1:
            pygame.draw.circle(surface, color, (cx, cy), max(hh, ww // 2))
        else:
            pygame.draw.ellipse(surface, color,
                                pygame.Rect(cx - ww // 2, cy - hh // 2, ww, hh))

    def _draw_mouth(self, surface, cx, cy, openness, curve):
        mw = int(self.face_w * 0.13 * self.layout["mouth_scale"])
        mh = int(self.face_w * 0.035 * self.layout["mouth_scale"])
        color = MOUTH_COLOR

        self._glow(surface, (cx, cy), int(mw * 0.7), color, 0.5)

        if openness > 0.45:
            oh = max(2, int(mh * openness * 3))
            ow = int(mw * (0.55 if openness > 0.75 else 0.8))
            pygame.draw.ellipse(surface, color, pygame.Rect(cx - ow // 2, cy - oh // 2, ow, oh))
        elif abs(curve) < 0.25:
            pygame.draw.line(surface, color, (cx - mw // 2, cy), (cx + mw // 2, cy), 3)
        elif curve > 0:
            rect = pygame.Rect(cx - mw // 2, cy - mh, mw, mh * 2)
            pygame.draw.arc(surface, color, rect, math.pi, 2 * math.pi, 3)
        else:
            rect = pygame.Rect(cx - mw // 2, cy - mh, mw, mh * 2)
            pygame.draw.arc(surface, color, rect, 0, math.pi, 3)

    def _draw_blush(self, surface, cx, cy, amount):
        color = (255, 120, 130)
        rw = int(self.face_w * 0.06)
        rh = int(self.face_w * 0.035)
        bx = cx
        by = cy + int(self.face_h * 0.14)
        blush = pygame.Surface((rw * 2, rh * 2), pygame.SRCALPHA)
        a = int(120 * amount)
        pygame.draw.ellipse(blush, (*color, a), (0, 0, rw * 2, rh * 2))
        surface.blit(blush, (bx - rw, by - rh))

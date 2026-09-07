"""无窗口预览：把 8 种表情各渲染一张合成图到 previews/ 目录，直接看图验收。
用法：python preview.py
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
from render import FaceRenderer

EXPRS = ["neutral", "smile", "surprised", "angry",
         "blink", "laugh", "blush", "wink"]

SIZE = (960, 540)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "previews")
os.makedirs(OUT, exist_ok=True)


def main():
    pygame.init()
    pygame.display.set_mode((1, 1))

    r = FaceRenderer(SIZE, "assets")
    r.continuous = True  # 用程序化连续眼/嘴，只叠 AI 面甲
    print("加载到素材：", {k: (list(v) if isinstance(v, dict) else "OK")
                           for k, v in r.assets.items()})

    surf = pygame.Surface(SIZE)
    for expr in EXPRS:
        r.set_expression(expr)
        for _ in range(40):
            r.step()
        r.draw(surf)
        path = os.path.join(OUT, f"{expr}.png")
        pygame.image.save(surf, path)
        print("已保存", path)

    pygame.quit()
    print("完成，去 previews/ 目录看图。")


if __name__ == "__main__":
    main()

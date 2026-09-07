"""M3 — 发光眼 + 发光嘴渲染（占位矢量版）。

用法：
    python main.py             # 摄像头驱动 + 手动按键
    python main.py --demo      # 自动循环展示所有表情（无需摄像头）
    python main.py --no-camera # 仅手动按键，不读摄像头
    python main.py --camera 1  # 指定摄像头

按键：
    1=无表情 2=大笑 3=害羞 4=坏笑（手动基础表情）
    d=切换演示循环
    q / ESC = 退出
"""
import argparse
import os
import time

import cv2
import pygame

from capture import create_capture
from face import FaceLandmarker
from expression import blendshapes_to_params
from render import FaceRenderer, save_layout

EXPRESSION_NAMES = {
    "neutral": "无表情",
    "smile": "微笑(自动)",
    "surprised": "惊讶(自动)",
    "angry": "生气(自动)",
    "blink": "眨眼(自动)",
    "laugh": "大笑",
    "blush": "害羞",
    "wink": "坏笑",
}

# 演示模式自动循环的顺序
ALL_EXPRESSIONS = ["neutral", "smile", "surprised", "angry",
                   "blink", "laugh", "blush", "wink"]
# 手动按键映射（1~4）
MANUAL_EXPRESSIONS = ["neutral", "laugh", "blush", "wink"]
KEY_MAP = {
    pygame.K_1: "neutral",
    pygame.K_2: "laugh",
    pygame.K_4: "wink",
}

WIN_SIZE = (960, 540)


def load_font(size):
    """直接按路径加载中文字体，绕过 pygame.SysFont 在 Python 3.13 的枚举 bug。"""
    for path in (
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyh.ttf",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ):
        if os.path.exists(path):
            try:
                return pygame.font.Font(path, size)
            except Exception:
                continue
    return pygame.font.Font(None, size)  # 兜底：英文默认字体


def handle_calibration(renderer, key):
    """校准眼/嘴位置与大小；返回 True 表示该按键已处理。"""
    L = renderer.layout
    handled = True
    if key == pygame.K_UP:
        L["eye_y"] -= 0.01; L["mouth_y"] -= 0.01
    elif key == pygame.K_DOWN:
        L["eye_y"] += 0.01; L["mouth_y"] += 0.01
    elif key == pygame.K_LEFT:
        L["eye_dx"] -= 0.01
    elif key == pygame.K_RIGHT:
        L["eye_dx"] += 0.01
    elif key == pygame.K_w:
        L["mouth_y"] -= 0.01
    elif key == pygame.K_s:
        L["mouth_y"] += 0.01
    elif key == pygame.K_LEFTBRACKET:
        L["eye_scale"] -= 0.05
    elif key == pygame.K_RIGHTBRACKET:
        L["eye_scale"] += 0.05
    elif key == pygame.K_MINUS:
        L["mouth_scale"] -= 0.05
    elif key == pygame.K_EQUALS:
        L["mouth_scale"] += 0.05
    elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        save_layout(L)
        print("布局已保存 ->", L)
    else:
        handled = False
    if handled:
        L["eye_y"] = max(0.0, min(1.0, L["eye_y"]))
        L["eye_dx"] = max(0.0, min(0.5, L["eye_dx"]))
        L["mouth_y"] = max(0.0, min(1.0, L["mouth_y"]))
        L["eye_scale"] = max(0.2, min(3.0, L["eye_scale"]))
        L["mouth_scale"] = max(0.2, min(3.0, L["mouth_scale"]))
    return handled


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--demo", action="store_true", help="自动循环展示所有表情")
    parser.add_argument("--no-camera", action="store_true", help="不读摄像头")
    args = parser.parse_args()

    # 摄像头（demo / no-camera 模式下不打开）
    cap = None
    landmarker = None
    if not args.demo and not args.no_camera:
        try:
            cap = create_capture(index=args.camera, width=args.width, height=args.height)
            landmarker = FaceLandmarker()
        except Exception as e:
            print(f"摄像头不可用，进入手动模式：{e}")
            cap = None
            landmarker = None

    pygame.init()
    screen = pygame.display.set_mode(WIN_SIZE)
    pygame.display.set_caption("Helmet M3 - Glow Eyes")
    clock = pygame.time.Clock()
    font = load_font(28)
    small = load_font(18)

    renderer = FaceRenderer(WIN_SIZE)
    renderer.continuous = True  # 连续 VTuber 式追踪（眼/嘴程序化曲线 + AI 面甲）

    manual = "neutral"
    blush_on = False  # 手动脸红开关（按键 3）
    demo = args.demo
    demo_idx = 0
    demo_timer = time.time()

    print("按键：1无表情 2大笑 3脸红 4坏笑；d=演示循环；q/ESC=退出")
    print("校准：↑↓移眼+嘴 ←→眼距 w/s移嘴 [ ]眼大小 - =嘴大小 回车保存")

    running = True
    while running:
        # 事件
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    running = False
                elif event.key == pygame.K_d:
                    demo = not demo
                    print("演示循环:", "开" if demo else "关")
                elif event.key == pygame.K_3:
                    blush_on = not blush_on
                    manual = "blush"
                    print("脸红:", "开" if blush_on else "关")
                elif handle_calibration(renderer, event.key):
                    pass
                elif event.key in KEY_MAP:
                    manual = KEY_MAP[event.key]
                    print("手动表情 ->", EXPRESSION_NAMES[manual])

        # 确定渲染参数：摄像头→连续追踪；demo/手动→离散表情
        expression = manual
        if demo:
            if time.time() - demo_timer > 1.2:
                demo_idx = (demo_idx + 1) % len(ALL_EXPRESSIONS)
                demo_timer = time.time()
            expression = ALL_EXPRESSIONS[demo_idx]
            renderer.set_expression(expression)
        elif cap is not None:
            ok, frame = cap.read()
            if ok:
                frame = cv2.flip(frame, 1)
                result = landmarker.process(frame)
                if result.face_blendshapes:
                    bs = landmarker.blendshapes_to_dict(result.face_blendshapes[0])
                    params = blendshapes_to_params(bs)
                    params["blush"] = 1.0 if blush_on else 0.0
                    renderer.set_params(params)
        else:
            renderer.set_expression(expression)
            renderer.set_params({"blush": 1.0 if blush_on else 0.0})

        # 渲染
        renderer.step()
        renderer.draw(screen)

        # 状态文字
        if demo:
            name = EXPRESSION_NAMES.get(expression, expression)
            mode = "DEMO"
        elif cap is None:
            name = EXPRESSION_NAMES.get(expression, expression)
            mode = "MANUAL"
        else:
            name = "连续追踪 LIVE"
            mode = (f"口角{renderer.params['mouth_curve']:+.2f} "
                    f"张嘴{renderer.params['mouth_open']:.2f} "
                    f"眼{renderer.params['eye_open_l']:.2f}")
        screen.blit(font.render(name, True, (130, 130, 130)), (12, 12))
        screen.blit(small.render(f"FPS {clock.get_fps():.0f}", True, (130, 130, 130)), (12, 52))
        screen.blit(small.render(mode, True, (160, 160, 160)), (12, 76))
        L = renderer.layout
        lay = (f"布局 眼y{L['eye_y']:.2f} 眼距{L['eye_dx']:.2f} 嘴y{L['mouth_y']:.2f} "
               f"眼倍{L['eye_scale']:.2f} 嘴倍{L['mouth_scale']:.2f}")
        screen.blit(small.render(lay, True, (170, 170, 170)), (12, screen.get_height() - 26))

        pygame.display.flip()
        clock.tick(60)

    if landmarker is not None:
        landmarker.close()
    if cap is not None:
        cap.release()
    pygame.quit()


if __name__ == "__main__":
    main()

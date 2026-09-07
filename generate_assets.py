"""批量生成鹤望兰号 8 张素材（本地 GPU + diffusers，白底→透明→裁剪一步到位）。

用法（用 AI venv 的 python 跑）：
    D:\\helmet-ai\\venv\\Scripts\\python.exe generate_assets.py [--model 模型ID] [--seed 42]

首次运行自动从 hf-mirror 下载模型（约 2~4GB，缓存在 D 盘）。
输出直接写入 assets/ 对应目录（透明背景，眼/嘴已自动裁剪到内容外框）。
"""
import argparse
import os
from collections import deque

import numpy as np
from PIL import Image

# 8 张素材定义（按顺序；变体从 base 图 img2img 派生，保证位置/大小一致）
# prompt 用英文（SD 模型对英文更稳）
PREFIX = ("glowing bright orange-yellow, mecha anime style, sharp clean lineart, "
          "high contrast, front view, centered, plain pure white background, "
          "no text, no watermark")

ASSETS = [
    # (相对路径, 尺寸, base路径或None, 是否裁剪到内容, 追加描述)
    ("face/faceplate.png", (512, 768), None, False,
     "white mecha faceplate with red markings, angular visor design, nose ridge, "
     "calm neutral glowing eyes, neutral straight mouth"),
    ("eyes/eye_neutral.png", (512, 512), None, True,
     "single glowing mecha eye, calm open almond shape"),
    ("eyes/eye_angry.png", (512, 512), "eyes/eye_neutral.png", True,
     "single glowing mecha eye, sharp slanted eyelid, furrowed, aggressive"),
    ("eyes/eye_wide.png", (512, 512), "eyes/eye_neutral.png", True,
     "single glowing mecha eye, wide open round iris, shocked"),
    ("mouth/mouth_neutral.png", (512, 512), None, True,
     "single mecha mouth, thin straight horizontal line, neutral"),
    ("mouth/mouth_smile.png", (512, 512), "mouth/mouth_neutral.png", True,
     "single mecha mouth, corners curved upward, gentle smile"),
    ("mouth/mouth_open.png", (512, 512), "mouth/mouth_neutral.png", True,
     "single mecha mouth, open oval, shouting"),
    ("mouth/mouth_frown.png", (512, 512), "mouth/mouth_neutral.png", True,
     "single mecha mouth, corners curved downward"),
]

NEGATIVE = ("lowres, bad anatomy, bad hands, text, watermark, signature, "
            "two eyes, pair of eyes, face, extra eye, extra mouth, "
            "worst quality, low quality")

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def white_to_transparent(rgba, thresh=240):
    """把与边缘连通的近白底置为透明（保留内部高光白点）。"""
    h, w = rgba.shape[:2]
    b, g, r = rgba[..., 0], rgba[..., 1], rgba[..., 2]
    near_white = (b >= thresh) & (g >= thresh) & (r >= thresh)
    visited = np.zeros((h, w), bool)
    q = deque()
    for y in range(h):
        for x in (0, w - 1):
            if near_white[y, x]:
                visited[y, x] = True
                q.append((y, x))
    for x in range(w):
        for y in (0, h - 1):
            if near_white[y, x] and not visited[y, x]:
                visited[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and near_white[ny, nx] and not visited[ny, nx]:
                visited[ny, nx] = True
                q.append((ny, nx))
    rgba[visited] = (0, 0, 0, 0)
    return rgba


def crop_to_alpha(rgba, pad=8):
    """裁剪到非透明区域的外接框。"""
    alpha = rgba[..., 3]
    ys, xs = np.where(alpha > 0)
    if len(xs) == 0:
        return rgba
    x0, x1 = max(0, xs.min() - pad), min(rgba.shape[1], xs.max() + pad)
    y0, y1 = max(0, ys.min() - pad), min(rgba.shape[0], ys.max() + pad)
    return rgba[y0:y1 + 1, x0:x1 + 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="dreamlike-art/dreamlike-anime-1.0")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--strength", type=float, default=0.45, help="img2img 强度（变体）")
    ap.add_argument("--steps", type=int, default=28)
    args = ap.parse_args()

    # 走国内镜像 + 缓存放 D 盘
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    os.environ.setdefault("HF_HOME", "D:/helmet-ai/hf")

    import torch
    from diffusers import StableDiffusionImg2ImgPipeline

    print("加载模型:", args.model)
    pipe = StableDiffusionImg2ImgPipeline.from_pretrained(
        args.model, torch_dtype=torch.float16, safety_checker=None)
    pipe = pipe.to("cuda")
    gen = torch.Generator("cuda").manual_seed(args.seed)

    os.makedirs(OUT_DIR, exist_ok=True)
    base_imgs = {}

    for rel, size, base, crop, desc in ASSETS:
        prompt = f"{PREFIX}, {desc}"
        full = os.path.join(OUT_DIR, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)

        if base is None:
            init = Image.new("RGB", size, (255, 255, 255))
            strength = 1.0
        else:
            init = base_imgs[base]
            strength = args.strength
        init = init.resize(size)

        print(f"[生成] {rel}  (strength={strength})")
        out = pipe(prompt=prompt, negative_prompt=NEGATIVE, image=init,
                   strength=strength, num_inference_steps=args.steps,
                   guidance_scale=7.0, generator=gen).images[0]

        if base is None:
            base_imgs[rel] = out

        rgba = np.array(out.convert("RGBA"))
        rgba = white_to_transparent(rgba)
        if crop:
            rgba = crop_to_alpha(rgba)
        Image.fromarray(rgba).save(full)
        print(f"[保存] {full}")

    print("全部完成。跑 python main.py --demo 看效果。")


if __name__ == "__main__":
    main()

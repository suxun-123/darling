"""把白底 AI 图转成透明 PNG（供 render.py 使用）。

AI 出图往往给纯白底、没有透明通道，直接用会盖住我们的白背景。
本脚本从图像边缘开始「洪水填充」，把与边缘连通的近白色区域置为透明，
保留眼睛内部不连通的高光白点。

用法：
    python make_transparent.py 输入.png [输出.png]
输出默认是 输入名_alpha.png。
"""
import sys
from collections import deque

import cv2
import numpy as np


def white_to_transparent(src, dst=None, thresh=240):
    img = cv2.imread(src, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise SystemExit(f"读不到 {src}")
    if img.shape[2] == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)

    h, w = img.shape[:2]
    b, g, r = img[..., 0], img[..., 1], img[..., 2]
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

    img[visited] = (0, 0, 0, 0)

    out = dst or (src.rsplit(".", 1)[0] + "_alpha.png")
    cv2.imwrite(out, img)
    print("已保存:", out)
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("用法：python make_transparent.py 输入.png [输出.png]")
    white_to_transparent(sys.argv[1], *sys.argv[2:3])

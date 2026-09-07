# 美术素材规格（M4 · 鹤望兰号完全还原）

目标：**整张面甲完整还原鹤望兰号的脸**，眼睛为**橙黄色发光**。
实现方式：分层渲染——1 张面甲底图 + 可动的橙黄眼/嘴层，这样眨眼和变表情才能干净地动起来。

你要生成 **8 张图**：1 张面甲 + 3 张眼睛 + 4 张嘴。生成后放进对应文件夹，`render.py` 自动检测使用。

## 目录结构（文件名必须完全一致）

```
assets/
├── face/
│   └── faceplate.png       # 整张面甲底图（静态）
├── eyes/                   # 橙黄发光眼，每张只画一只（左右镜像用同一张）
│   ├── eye_neutral.png     # 正常睁眼
│   ├── eye_angry.png       # 怒眼（下压/斜，战斗）
│   └── eye_wide.png        # 惊讶大眼
└── mouth/                  # 橙黄嘴
    ├── mouth_neutral.png   # 细横线
    ├── mouth_smile.png     # 上翘（微笑）
    ├── mouth_open.png      # 张嘴 O 形（惊讶/大喊）
    └── mouth_frown.png     # 下撇（生气）
```

## 图片要求

- **格式**：PNG，**透明背景**最好；AI 只给白底就生成后转透明：
  ```bash
  python make_transparent.py 你的白底图.png
  ```
- **颜色**：统一**橙黄色发光**（`bright orange-yellow glow, #FF9614` 左右）。
- **风格**：机甲动漫风，参考鹤望兰号（Strelizia / 02 的机甲）。
- **眼睛**：建议 512×512，**每张只画一只眼**，居中，四周留白；三张眼睛的**大小、角度、位置要一致**（这样切换/眨眼不跳）。
- **嘴**：建议 512×256，居中。
- **面甲**：建议 1024×1280（竖版，接近脸部比例），**整张脸特写、铺满画面、正面正对**，白底。**不要画身体/肩膀/半身/全身/带人物的图，就一张脸占满画面。**眼睛和嘴要画在标准位置（眼在偏上 1/3、左右对称；嘴在中下），这样我的动画层能对上。
- **一致性**：8 张同一模型、同一 seed、同一套风格词。

## 面甲底图特别说明（重要）

面甲底图要包含：白色面甲 + 红色纹路 + 鼻梁结构，**眼睛和嘴可以先画成中性状态**。
程序运行时会在眼窝/嘴的位置打白补丁盖住底图里的眼嘴，再叠上会动的橙黄眼/嘴层。
所以底图里的眼睛嘴只要**大致位置对**即可，动画层会覆盖它。

> 天线和侧发是 3D 打印头盔外壳的一部分，**不用画进面甲图**（脸部屏幕放不下）。

## 工具建议（你来做图）

> 面部图你自己生成（在线或本地都行），做好后按上面的文件名放进对应文件夹即可，程序自动识别。

- **首选 哩布哩布（LiblibAI）**：国内直连、每天有免费点数，SD 内核，可搜「鹤望兰 / 机甲 / 发光眼」现成模型或 LoRA。**英文提示词最稳**（下面给了），中文也能用。
- **备选 即梦（Dreamina）/ 通义万相**：中文友好，**用中文提示词**即可。
- 不建议 Midjourney（要翻墙 + 付费 + 出不了透明背景）。

## 生成提示词（中英两份，任选）

> 想更还原，可在描述里加「鹤望兰号，《DARLING in the FRANXX》」（若拦截版权就删掉，只留描述）。

### 统一风格前缀

**中文**：
```
机甲动漫风格，橙黄色发光，线条干净锐利，高对比度，正面视角，居中构图，纯白背景，无文字，无水印
```

**英文**：
```
glowing bright orange-yellow, mecha anime style, sharp clean lineart,
high contrast, front view, centered, isolated on plain pure white background,
no text, no watermark
```

### 面甲（1 张）

| 文件 | 中文描述 | 英文描述 |
|---|---|---|
| faceplate.png | 白色机甲面甲，带红色纹路，棱角分明的面罩造型，有鼻梁结构，平静的中性发光橙黄眼，中性的细直嘴 | `white mecha faceplate with red markings, angular visor design, nose ridge, calm neutral glowing eyes, neutral straight mouth` |

### 眼睛（3 张）

| 文件 | 中文描述 | 英文描述 |
|---|---|---|
| eye_neutral.png | 单只发光的机甲眼睛，平静的杏仁形睁眼 | `single glowing mecha eye, calm open almond shape` |
| eye_angry.png | 单只发光的机甲眼睛，锐利上斜的眼睑，眉头下压，凶狠愤怒 | `single glowing mecha eye, sharp slanted eyelid, furrowed, aggressive` |
| eye_wide.png | 单只发光的机甲眼睛，睁大的圆形虹膜，惊讶震惊 | `single glowing mecha eye, wide open round iris, shocked` |

### 嘴（4 张）

| 文件 | 中文描述 | 英文描述 |
|---|---|---|
| mouth_neutral.png | 单张机甲嘴，细直横线，中性 | `single mecha mouth, thin straight line, neutral` |
| mouth_smile.png | 单张机甲嘴，嘴角上翘，温柔的微笑 | `single mecha mouth, corners curved upward, gentle smile` |
| mouth_open.png | 单张机甲嘴，张开的椭圆形，呐喊 | `single mecha mouth, open oval, shouting` |
| mouth_frown.png | 单张机甲嘴，嘴角下撇 | `single mecha mouth, corners curved downward` |

## 生成后

放进目录，跑 `python main.py --demo` 看效果。哪张不像、颜色不对、眼睛位置对不上面甲，随时告诉我，我调代码或改提示词。

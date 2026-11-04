# 星璃 Hoshiri 桌宠 · 素材生成规格 v1

> 目标：一张能拆帧做动画的 Q 版素材集。规格卡死，否则后期对不齐。

## 1. 角色基准（照这两张图锁定）

| 部位 | 特征 | 参考色 |
|---|---|---|
| 头发 | 金色长卷发，发尾微卷，刘海分缝 | `#F2D98D` / 暗部 `#D9B45F` |
| 眼睛 | 大蓝瞳，上眼睑有睫毛，高光偏冷 | `#4AA3E8` / 高光 `#BFE4FF` |
| 头饰 | 金色小星冠（斜戴，勿太大） | `#E8C36A` |
| 服装 | 白→浅蓝→深蓝渐变，多层荷叶边短裙 | `#FFFFFF` `#A9C9F2` `#2B4C8C` |
| 靴子 | 白色过膝靴，脚踝蓝宝石 | `#FFFFFF` + `#2B6FD6` |
| 武器 | 细银色刺剑（可省略） | `#D8DEE6` |
| 氛围元素 | 月牙、四角星屑、细碎光点 | `#FFE9A8` `#CFE3FF` |

## 2. 画风约束

- **2.5 头身** Q 版（头大身小，腿短）
- 赛璐璐平涂 + 一层柔和阴影，**不要厚涂、不要 3D**
- 线稿干净，描边用深棕 `#4A3B2E`，不要纯黑
- **正面视角**，身体微微 15° 侧转，不要大透视
- 背景**纯白 `#FFFFFF`**（或纯品红 `#FF00FF`），不要渐变、不要投影
- 四周留白 ≥ 64px，脚不要被裁

## 3. 素材清单

| # | 文件名 | 内容 | 尺寸 | 关键要求 |
|---|---|---|---|---|
| 1 | `chibi_idle.png` | 站立，双手自然下垂 | 1024×1536 | **基准姿势，其余全部由它派生** |
| 2 | `chibi_blink.png` | 同姿势，闭眼 | 同上 | 只有眼睛不同 |
| 3 | `chibi_talk.png` | 同姿势，嘴微张 | 同上 | 只有嘴不同 |
| 4 | `chibi_happy.png` | 同姿势，笑眼 | 同上 | 表情变化 |
| 5 | `chibi_think.png` | 手托下巴，头顶问号 | 同上 | 手部允许变化 |
| 6 | `chibi_drag.png` | 被拎起，惊讶张嘴，手脚微张 | 同上 | 用于拖拽 |
| 7 | `chibi_sleep.png` | 坐姿打盹，闭眼 | 同上 | 可换姿势 |
| 8 | `head_idle.png` | 胸像头像（用于对话气泡） | 1024×1024 | 圆形构图友好 |

> **1–6 必须是同一姿势、同一视角、同一缩放**，只改表情和手。否则切换会「跳」。

## 4. 提示词

### 4.1 英文（Stable Diffusion / Midjourney / Niji）

**正向**：

```
1girl, chibi, 2.5 head tall, solo, full body, standing, front view,
long wavy blonde hair, bright blue eyes, small gold star tiara,
sleeveless white and sky-blue gradient dress, layered ruffled skirt,
white thigh-high boots with blue gemstone, holding a thin silver rapier,
crescent moon and star sparkle motifs, cel shading, clean lineart,
pastel color palette, plain white background, character reference sheet,
high quality, masterpiece, sharp focus
```

**负向**：

```
lowres, worst quality, 3d, realistic, photorealistic, multiple views,
extra limbs, extra fingers, fused fingers, bad hands, deformed face,
text, watermark, signature, logo, background shadow, gradient background,
cropped, out of frame, frame, border
```

**参数**：`832×1216`，Steps `30`，CFG `6.5`，Sampler `DPM++ 2M Karras`，**固定 Seed**。

### 4.2 中文（即梦 / 可灵 / 通义万相）

```
Q版二头身少女，单人全身站姿，正面视角，金色长卷发，蓝色大眼睛，
头顶戴金色小星冠，白色到天蓝色渐变的荷叶边层叠短裙，
白色过膝长靴带蓝宝石，手持细银色刺剑，月牙与四角星屑装饰，
赛璐璐平涂上色，干净线稿，柔和低饱和配色，纯白背景，
角色设定图，高清，线条清晰
```

**负向**：`多视图，文字，水印，投影，渐变背景，写实，3D，手部畸形，裁切，边框`

## 5. 一致性技巧（重点）

1. **垫图最稳**：即梦/可灵/SD 都支持「参考图」，直接把 `立绘2.jpeg` 传进去当参考，再用上面的提示词 —— 脸和配色会比纯文字准得多。
2. **先生成 1 张 `chibi_idle`，满意后把它作为基底**，用图生图（img2img）改表情，**重绘幅度 0.25–0.35**，Seed 保持不变。
3. 每张出图后检查三件事：背景是不是纯白、脚有没有被裁、四周留白够不够。
4. 一次出 4 张挑一张，不要一次只出一张。

## 6. 交付

放到 `assets/raw/`，文件名按第 3 节的表来。我拿到后会做：

- 白底抠图 → 透明 PNG（发丝级羽化）
- 统一裁切到同一画布、同一锚点
- 生成动画所需的分层（身体 / 头发 / 眼睛）
- 输出到 `assets/out/`

如果暂时没有素材，我会先用 `立绘2.jpeg` 转成的占位图把框架跑通，你随时替换。
## 7. 桌宠专用 · 趴边形态（重点）

桌宠要的是**趴在屏幕边缘、只有上半身露出来**的姿势，不是站立全身。生成时请锁定：

- 姿势：**俯卧 / 侧趴**，双手交叠扒在画面下边缘，下巴或侧脸靠着手臂
- 构图：**只画到胸腰位置**，下半身不出现（会被屏幕边缘挡住）
- 视角：正面偏 15°，视线看向画面外（朝用户）
- 表情：放松、微困、或轻轻笑

**英文提示词**：

```
1girl, chibi, 2.5 head tall, lying prone on a surface, upper body only,
both hands resting on the bottom edge of the frame, chin on hands,
looking at viewer, relaxed sleepy smile,
long wavy blonde hair splayed out, bright blue eyes, gold star tiara,
white and sky-blue gradient dress with ruffled neckline,
cel shading, clean lineart, pastel palette, plain white background,
desktop pet sprite, front view, high quality
```

**负向**：`full body, legs, feet, standing, multiple views, text, watermark, 3d, realistic, complex background`

**中文**：

```
Q版二头身少女，俯卧趴在画面前边缘，只露出上半身，双手交叠搭在下边缘，下巴搁在手背上，
看向镜头，慵懒微笑，金色长卷发散开，蓝眼睛，金色小星冠，白蓝渐变荷叶边领口，
赛璐璐平涂，干净线稿，柔和配色，纯白背景，桌宠立绘，正面视角
```

### 需要的帧

| 文件 | 状态 |
|---|---|
| `prone_idle.png` | 睁眼、放松（基准） |
| `prone_sleep.png` | 闭眼打盹 |
| `prone_talk.png` | 嘴微张 |
| `prone_happy.png` | 笑眼 |

出图后放进 `assets/raw/`，我把它们处理成 `assets/out/` 下同尺寸的透明 PNG，
再在右键菜单「形象」里加一项就能切换。
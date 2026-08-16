# PaddleOCR 本地配置

## 适用范围

阶段一只需要通用中文图片文字识别，不需要文档解析、表格理解或模型训练，因此安装基础 `paddleocr` 推理包即可，不安装 `paddleocr[all]`。

## Python 版本

项目使用 `.python-version` 固定 Python 3.11。先确认：

```bash
uv python install 3.11
uv sync --project backend --python 3.11 --extra ocr
uv run --project backend python --version
```

最后一条应显示 Python 3.11.x。不要使用系统自带 Python 3.9，也暂不使用 Python 3.13 运行 PaddleOCR。

## 安装方式

本项目阶段一不使用 Docker，推荐 CPU 推理。

### macOS / CPU

先尝试在项目环境安装 PaddlePaddle 与 PaddleOCR：

```bash
uv sync --project backend --python 3.11 --extra ocr
```

若 PaddlePaddle 官方没有与你的 macOS 架构匹配的 wheel，优先在 Linux CPU 环境运行 OCR Worker；不要从非官方来源安装未知 wheel。

### Linux / CPU

官方文档给出的 CPU 安装源：

```bash
uv pip install --python backend/.venv/bin/python \
  paddlepaddle==3.2.0 \
  --index-url https://www.paddlepaddle.org.cn/packages/stable/cpu/
uv pip install --python backend/.venv/bin/python paddleocr
```

### Linux / NVIDIA GPU

GPU 包必须按 CUDA 版本选择。以 CUDA 11.8 为例：

```bash
uv pip install --python backend/.venv/bin/python \
  paddlepaddle-gpu==3.2.0 \
  --index-url https://www.paddlepaddle.org.cn/packages/stable/cu118/
uv pip install --python backend/.venv/bin/python paddleocr
```

## `.env` 配置

```bash
OCR_ENABLED=true
OCR_LANGUAGE=ch
OCR_MIN_CONFIDENCE=0.5
OCR_USE_DOC_ORIENTATION_CLASSIFY=false
OCR_USE_DOC_UNWARPING=false
OCR_USE_TEXTLINE_ORIENTATION=false
# paddleocr 3.x 通过环境变量决定模型缓存位置（Settings 启动时自动 setdefault）
PADDLE_PDX_CACHE_HOME=./data/paddlex
HF_HOME=./data/huggingface
```

- `OCR_LANGUAGE=ch`：中文场景。
- `OCR_MIN_CONFIDENCE`：低于该置信度的文字被过滤。
- 三个方向/矫正开关默认关闭，减少本机 CPU 开销；海报倾斜或旋转明显时再开启。
- 模型缓存目录 `data/paddlex/official_models/` 不会提交到 Git。首次运行会下载模型，需要网络。`PADDLE_PDX_CACHE_HOME` 由 `get_settings()` 在进程启动时设置,无需手动 export(之前只靠 `scripts/dev-worker.sh` 的 export,直接跑 uvicorn/celery 会缺失)。

## 安装验证

```bash
uv run --project backend --extra ocr python -c "import paddle; print(paddle.__version__)"
uv run --project backend --extra ocr paddleocr --help
```

对一张图片做最小识别：

```bash
uv run --project backend --extra ocr paddleocr ocr \
  -i ./path/to/test.jpg \
  --use_doc_orientation_classify false \
  --use_doc_unwarping false \
  --use_textline_orientation false
```

## 项目接入方式

业务代码只依赖 `OCRService` 的引擎接口。PaddleOCR 初始化应在 Celery Worker 进程内惰性执行并复用单例，不能为每张图片重复加载模型。测试环境继续使用轻量假引擎，不下载模型。

处理链路固定为：

```text
PaddleOCR 提取图片原始文字
  -> 合并笔记标题、正文与 OCR 文本
  -> MiniMax-M3 提取活动名称、时间、地点、费用、类型和摘要
```

MiniMax-M3 文本接口不作为 PaddleOCR 的直接替代。PaddleOCR 保证逐字识别可复现且无按次调用成本；MiniMax-M3 负责理解文本语义和结构化字段。未来若引入独立的图片理解接口，只作为 OCR 失败时的可选兜底。

官方参考：[PaddleOCR 安装文档](https://www.paddleocr.ai/main/en/version3.x/installation.html)、[PaddleOCR Quick Start](https://www.paddleocr.ai/main/en/quick_start.html)。

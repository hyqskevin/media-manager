#!/bin/bash
set -e

# OCR 增强包打包脚本:产出 paddleocr-addon-<version>-<os>-<arch>.zip
# 用法: ./scripts/package-ocr-addon.sh <os> <arch> <version>
# 平台支持: macos-arm64 / macos-x86_64 / windows-x64
# 依赖: 当前环境已装 Python 3.11 + pip

OS=${1:?"用法: ./scripts/package-ocr-addon.sh <os> <arch> <version>"}
ARCH=${2:?"用法: ./scripts/package-ocr-addon.sh <os> <arch> <version>"}
VERSION=${3:?"用法: ./scripts/package-ocr-addon.sh <os> <arch> <version>"}

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
BUILD_DIR=$ROOT_DIR/dist/ocr-addon-build
WHEELS_DIR=$BUILD_DIR/wheels
MODELS_DIR=$BUILD_DIR/data/paddlex/official_models

echo "==> 打包 OCR 增强包 $OS-$ARCH v$VERSION"

# 0. 清理旧构建
rm -rf $BUILD_DIR
mkdir -p $WHEELS_DIR $MODELS_DIR

# 1. 确定 wheel 平台标签
case "$OS-$ARCH" in
  macos-arm64)
    WHEEL_PLATFORM_TAG="macosx_11_0_arm64"
    PADDLE_PLATFORM="macosx_11_0_arm64"
    ;;
  macos-x86_64)
    WHEEL_PLATFORM_TAG="macosx_10_9_x86_64"
    PADDLE_PLATFORM="macosx_10_9_x86_64"
    ;;
  windows-x64)
    WHEEL_PLATFORM_TAG="win_amd64"
    PADDLE_PLATFORM="win_amd64"
    ;;
  *)
    echo "错误: 不支持的平台 $OS-$ARCH"
    echo "支持: macos-arm64 / macos-x86_64 / windows-x64"
    exit 1
    ;;
esac

# 2. 下载 paddleocr wheel(纯 Python,平台无关)
echo "==> 下载 paddleocr wheel..."
pip download paddleocr==$VERSION \
  --no-deps \
  -d $WHEELS_DIR/

# 3. 下载 paddlepaddle wheel(平台相关)
echo "==> 下载 paddlepaddle wheel..."
pip download paddlepaddle==3.3.1 \
  --platform $PADDLE_PLATFORM \
  --only-binary=:all: \
  --no-deps \
  -d $WHEELS_DIR/

# 4. 下载 paddleocr 依赖 wheel(跨平台)
echo "==> 下载 paddleocr 依赖 wheel..."
pip download paddleocr==$VERSION \
  -d $WHEELS_DIR/

# 5. 安装 wheels 到当前 Python 环境(临时,仅为触发模型下载)
echo "==> 安装 wheels 以触发模型下载..."
pip install --no-index --find-links=$WHEELS_DIR/ \
  paddleocr==$VERSION paddlepaddle==3.3.1

# 6. 触发模型下载到指定目录
echo "==> 下载 OCR 模型文件..."
PADDLE_PDX_CACHE_HOME=$BUILD_DIR/data/paddlex python -c "
import os
os.environ['PADDLE_PDX_CACHE_HOME'] = '$BUILD_DIR/data/paddlex'
from paddleocr import PaddleOCR
# 初始化触发模型下载到 \$PADDLE_PDX_CACHE_HOME/official_models
ocr = PaddleOCR(
    lang='ch',
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
)
print('模型下载完成')
"

# 7. 写 VERSION 文件
echo "version: $VERSION" > $BUILD_DIR/VERSION
echo "built_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> $BUILD_DIR/VERSION
echo "platform: $OS-$ARCH" >> $BUILD_DIR/VERSION

# 8. 压缩
echo "==> 压缩产物..."
cd $ROOT_DIR/dist
zip -r paddleocr-addon-$VERSION-$OS-$ARCH.zip ocr-addon-build

echo "==> 完成: $ROOT_DIR/dist/paddleocr-addon-$VERSION-$OS-$ARCH.zip"

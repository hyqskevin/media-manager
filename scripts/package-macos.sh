#!/bin/bash
set -e

# macOS 打包脚本:产出 xhs-info-crawl-<version>-macos.zip
# 用法: ./scripts/package-macos.sh <version>
# 依赖: frontend/dist 和 launcher/ui/dist 已构建完成
# Python: python-build-standalone cpython-3.11.9 (astral-sh)

VERSION=${1:?"用法: ./scripts/package-macos.sh <version>"}
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
BUILD_DIR=$ROOT_DIR/dist/build
PKG_DIR=$BUILD_DIR/xhs-info-crawl
# python-build-standalone 用 triple 命名: aarch64-apple-darwin (不是 darwin-arm64)
PYTHON_VERSION="cpython-3.11.9+20240415"
PYTHON_ARCHIVE="$PYTHON_VERSION-aarch64-apple-darwin-install_only.tar.gz"
PYTHON_URL="https://github.com/astral-sh/python-build-standalone/releases/download/20240415/$PYTHON_ARCHIVE"

echo "==> 打包 macOS v$VERSION"
echo "项目根目录: $ROOT_DIR"

# 0. 清理旧构建
rm -rf $BUILD_DIR
mkdir -p $PKG_DIR

# 1. 下载便携版 Python 3.11.9(python-build-standalone)
echo "==> 下载便携版 Python..."
PYTHON_TGZ=$BUILD_DIR/python.tar.gz
curl -fL $PYTHON_URL -o $PYTHON_TGZ
echo "==> 解压 Python..."
tar xzf $PYTHON_TGZ -C $BUILD_DIR
echo "解压后 BUILD_DIR 顶层内容:"
ls -la $BUILD_DIR/
# 查找解压后的 python 目录
# python-build-standalone install_only 解压后标准布局是 $BUILD_DIR/python/bin/python3
# 优先检查标准路径,fallback 用 shell glob 查找
PYTHON_SRC="$BUILD_DIR/python"
if [ ! -x "$PYTHON_SRC/bin/python3" ]; then
    echo "标准路径 $PYTHON_SRC/bin/python3 不存在,用 glob 查找..."
    for pybin in "$BUILD_DIR"/*/bin/python3; do
        if [ -x "$pybin" ]; then
            PYTHON_SRC=$(dirname $(dirname "$pybin"))
            break
        fi
    done
fi
if [ ! -x "$PYTHON_SRC/bin/python3" ]; then
    echo "错误:未找到含 bin/python3 的目录"
    echo "BUILD_DIR 内容:"
    ls -la "$BUILD_DIR/"
    exit 1
fi
echo "找到 Python 目录: $PYTHON_SRC"
mkdir -p $PKG_DIR/runtime
mv "$PYTHON_SRC" $PKG_DIR/runtime/python
rm -f $PYTHON_TGZ

# 2. 创建 venv 并安装依赖(不含 ocr extra)
echo "==> 创建 venv 并安装依赖..."
# 不用 --copies:python-build-standalone 的 ensurepip 在 --copies 模式下 SIGABRT。
# 默认创建 symlink,然后第 8 步 mv 之后我们手动把 symlink 替换为真实 copy。
$PKG_DIR/runtime/python/bin/python3 -m venv $PKG_DIR/runtime/venv
$PKG_DIR/runtime/venv/bin/pip install --upgrade pip
$PKG_DIR/runtime/venv/bin/pip install -r $ROOT_DIR/backend/requirements-runtime.txt
$PKG_DIR/runtime/venv/bin/pip install -r $ROOT_DIR/launcher/requirements.txt

# 修复 venv 缺少 libpython3.11.dylib 问题:
# python-build-standalone 解压后创建的 venv/lib 下没有 libpython,
# venv/bin/python 启动时报 Library not loaded 错误。
# 解决:把 base python 的 libpython 复制到 venv/lib/
echo "==> 修复 venv libpython..."
cp $PKG_DIR/runtime/python/lib/libpython3.11.dylib $PKG_DIR/runtime/venv/lib/libpython3.11.dylib 2>&1

# 3. 复制后端源码(排除测试代码)
echo "==> 复制后端源码(排除 tests)..."
mkdir -p $PKG_DIR/app/backend
rsync -a --exclude='tests/' --exclude='__pycache__/' --exclude='.pytest_cache/' \
  --exclude='.coverage' --exclude='htmlcov/' \
  $ROOT_DIR/backend/ $PKG_DIR/app/backend/

# 4. 复制前端构建产物
echo "==> 复制前端构建产物..."
mkdir -p $PKG_DIR/app/frontend/dist
cp -r $ROOT_DIR/frontend/dist/* $PKG_DIR/app/frontend/dist/

# 5. 复制启动器(不含 ui/src 和 node_modules)
echo "==> 复制启动器..."
mkdir -p $PKG_DIR/launcher/ui/dist
cp $ROOT_DIR/launcher/*.py $PKG_DIR/launcher/
cp $ROOT_DIR/launcher/requirements.txt $PKG_DIR/launcher/
cp -r $ROOT_DIR/launcher/ui/dist/* $PKG_DIR/launcher/ui/dist/

# 修复 index.html 的绝对路径为相对路径,
# 否则 PyWebView 用 file:// 加载时找不到 /assets/... (会白屏)
# 把 <script src="/assets/..."> 改为 <script src="./assets/...">
if [ -f "$PKG_DIR/launcher/ui/dist/index.html" ]; then
    echo "==> 修复 index.html 资源路径为相对路径..."
    sed -i '' 's|src="/assets/|src="./assets/|g; s|href="/assets/|href="./assets/|g' \
        "$PKG_DIR/launcher/ui/dist/index.html"
fi

# 6. 复制 .env.example
cp $ROOT_DIR/.env.example $PKG_DIR/.env.example

# 7. 创建空 data 目录(含 paddlex 占位,OCR 增强包安装后填充)
echo "==> 创建 data 目录..."
mkdir -p $PKG_DIR/data/logs $PKG_DIR/data/images $PKG_DIR/data/exports $PKG_DIR/data/celery
mkdir -p $PKG_DIR/data/paddlex/official_models
mkdir -p $PKG_DIR/data/huggingface
mkdir -p $PKG_DIR/data/tmp
mkdir -p $PKG_DIR/data/run
mkdir -p $PKG_DIR/data/archive
mkdir -p $PKG_DIR/data/backups

# 8. 打 .app bundle
echo "==> 创建 .app bundle..."
mkdir -p $BUILD_DIR/xhs-info-crawl.app/Contents/MacOS
mkdir -p $BUILD_DIR/xhs-info-crawl.app/Contents/Resources
# 把所有运行数据放到 .app/Contents/Resources/ 下,
# 这样 Finder 双击 .app 时 macOS AppTranslocation 会把整个 .app(含数据)
# 一起复制到 /private/var/folders/.../T/AppTranslocation/.../ 沙盒,
# start.sh 才能找到 runtime/venv/bin/python
echo "==> 移动运行数据到 .app/Contents/Resources/xhs-info-crawl/..."
mv $PKG_DIR $BUILD_DIR/xhs-info-crawl.app/Contents/Resources/xhs-info-crawl
PKG_DIR="$BUILD_DIR/xhs-info-crawl.app/Contents/Resources/xhs-info-crawl"

# 8.1 替换 venv/bin/ 里的 python 符号链接为真实 copy
# macOS venv 默认 symlink bin/python -> ../python/bin/python3,
# mv 之后 symlink 路径失效。手动删除 symlink,copy base python 进去。
echo "==> 替换 venv/bin/python* symlink 为真实 copy..."
for binfile in $PKG_DIR/runtime/venv/bin/python python3 python3.11; do
    src="$PKG_DIR/runtime/venv/bin/$binfile"
    if [ -L "$src" ]; then
        rm "$src"
        cp "$PKG_DIR/runtime/python/bin/$(basename $binfile)" "$src"
    fi
done

cat > $BUILD_DIR/xhs-info-crawl.app/Contents/Info.plist <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>小红书活动信息抓取系统</string>
  <key>CFBundleDisplayName</key><string>小红书活动信息抓取系统</string>
  <key>CFBundleExecutable</key><string>start.sh</string>
  <key>CFBundleVersion</key><string>$VERSION</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleSignature</key><string>????</string>
</dict>
</plist>
EOF
cat > $BUILD_DIR/xhs-info-crawl.app/Contents/MacOS/start.sh <<'EOF'
#!/bin/bash
# .app 启动入口:调用 launcher/main.py
# 用 realpath 找脚本真实位置,不依赖 cwd(macOS GUI 双击 .app 时 cwd 是 /)
SCRIPT="$(realpath "$0")"
# start.sh 在 .app/Contents/MacOS/start.sh,
# 数据目录在 .app/Contents/Resources/xhs-info-crawl/(包内资源,
# Finder AppTranslocation 会随 .app 整体复制,不会丢)
APP_DIR="$(dirname "$(dirname "$(dirname "$SCRIPT")")")"
DATA_DIR="$APP_DIR/Contents/Resources/xhs-info-crawl"
# python-build-standalone 的 Python 二进制硬编码 /install 作为 base prefix,
# 需要设 PYTHONHOME 指向 runtime/python,并把 runtime/python/lib 加到 DYLD_LIBRARY_PATH
# 同时把 libpython 复制到 venv/lib/(避免 venv/bin/python 启动时找不到 libpython)
export PYTHONHOME="$DATA_DIR/runtime/python"
export DYLD_LIBRARY_PATH="$DATA_DIR/runtime/python/lib:${DYLD_LIBRARY_PATH}"
# 把父目录加入 PYTHONPATH,让 launcher 模块可导入
export PYTHONPATH="$DATA_DIR:$PYTHONPATH"
cd "$DATA_DIR/launcher"
exec "$DATA_DIR/runtime/venv/bin/python" "$DATA_DIR/launcher/main.py"
EOF
chmod +x $BUILD_DIR/xhs-info-crawl.app/Contents/MacOS/start.sh

# 8.5 Adhoc 签名整个 .app(避免 Gatekeeper 弹"Apple 无法验证 python")
# 用 codesign --force --deep --sign - 给所有 binary 打临时签名,
# 包括 venv/bin/python、venv/bin/python3 等。
echo "==> Adhoc 签名 .app..."
codesign --force --deep --sign - "$BUILD_DIR/xhs-info-crawl.app" 2>&1 | tail -3
# 验证签名
codesign --verify --verbose "$BUILD_DIR/xhs-info-crawl.app" 2>&1 | tail -2

# 9. 压缩
echo "==> 压缩产物..."
cd $BUILD_DIR
zip -r xhs-info-crawl-$VERSION-macos.zip xhs-info-crawl xhs-info-crawl.app

echo "==> 完成: $BUILD_DIR/xhs-info-crawl-$VERSION-macos.zip"

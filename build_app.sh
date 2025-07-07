#!/bin/bash

# SAU 自媒体发布系统一键构建脚本

set -e  # 遇到错误立即退出

echo "🚀 开始构建 SAU 自媒体自动化运营系统..."

# 全局变量
PKG_MANAGER=""

# 检查依赖
check_dependencies() {
    echo "🔍 检查构建依赖..."
    
    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python3 未安装"
        exit 1
    fi
    
    # 检查虚拟环境
    if [ ! -d ".env" ]; then
        echo "❌ 未找到 .env 虚拟环境目录"
        exit 1
    fi
    
    # 检查 Node.js
    if ! command -v node &> /dev/null; then
        echo "❌ Node.js 未安装"
        exit 1
    fi
    
    # 检查包管理器 (优先使用 yarn)
    if command -v yarn &> /dev/null; then
        PKG_MANAGER="yarn"
        echo "📦 使用 yarn 作为包管理器"
    elif command -v npm &> /dev/null; then
        PKG_MANAGER="npm"
        echo "📦 使用 npm 作为包管理器"
    else
        echo "❌ 未找到 npm 或 yarn"
        exit 1
    fi
    
    # 检查配置文件
    if [ ! -f "conf.py" ]; then
        if [ -f "conf.example.py" ]; then
            echo "⚠️ 未找到 conf.py，请复制 conf.example.py 并重命名为 conf.py"
            exit 1
        else
            echo "❌ 未找到配置文件"
            exit 1
        fi
    fi
    
    echo "✅ 依赖检查通过"
}

# 激活虚拟环境
activate_venv() {
    echo "🐍 激活 Python 虚拟环境..."
    source .env/bin/activate
    echo "✅ 虚拟环境已激活"
}

# 安装后端依赖
install_backend_deps() {
    echo "📦 检查后端依赖..."
    
    # 检查 playwright 是否已安装浏览器
    if ! python3 -c "import playwright" &> /dev/null; then
        echo "⚠️ 未找到 playwright，请确保已在虚拟环境中安装"
    fi
    
    # 检查可用的包管理器
    if command -v uv &> /dev/null; then
        echo "📦 使用 uv pip 安装 PyInstaller..."
        uv pip install pyinstaller
    elif command -v pip &> /dev/null; then
        echo "📦 使用 pip 安装 PyInstaller..."
        pip install pyinstaller
    else
        echo "❌ 未找到可用的 Python 包管理器"
        exit 1
    fi
    
    echo "✅ 后端依赖检查完成"
}

# 构建前端
build_frontend() {
    echo "🎨 构建前端..."
    cd sau_frontend
    
    # 确保依赖已安装
    if [ ! -d "node_modules" ]; then
        echo "📦 安装前端依赖..."
        if [ "$PKG_MANAGER" = "yarn" ]; then
            yarn install
        else
            npm install
        fi
    fi
    
    # 检查是否已有 Electron 依赖
    if [ "$PKG_MANAGER" = "yarn" ]; then
        if ! yarn list electron &> /dev/null; then
            echo "📦 安装 Electron 构建依赖..."
            # 使用固定版本避免依赖冲突
            yarn add -D electron@28.0.0 electron-builder@24.6.4 concurrently@8.2.0 wait-on@7.0.1
        fi
    else
        if ! npm list electron &> /dev/null; then
            echo "📦 安装 Electron 构建依赖..."
            npm install --save-dev electron@28.0.0 electron-builder@24.6.4 concurrently@8.2.0 wait-on@7.0.1
        fi
    fi
    
    # 创建必要的目录
    mkdir -p electron
    mkdir -p build
    
    # 构建前端静态文件
    echo "🔨 构建前端静态文件..."
    if [ "$PKG_MANAGER" = "yarn" ]; then
        yarn build
    else
        npm run build
    fi
    
    cd ..
    echo "✅ 前端构建完成"
}

# 构建后端
build_backend() {
    echo "🐍 构建 Python 后端..."
    
    # 确保在虚拟环境中
    activate_venv
    
    # 安装后端构建依赖
    install_backend_deps
    
    # 运行后端构建脚本
    python3 build_backend.py
    
    echo "✅ 后端构建完成"
}

# 构建 Electron 应用
build_electron() {
    echo "⚡ 构建 Electron 应用..."
    cd sau_frontend
    
    # 构建 macOS 应用
    if [ "$PKG_MANAGER" = "yarn" ]; then
        yarn build:electron
    else
        npm run build:electron
    fi
    
    cd ..
    echo "✅ Electron 应用构建完成"
}

# 创建最终分发包
create_distribution() {
    echo "📦 创建分发包..."
    
    # 创建分发目录
    mkdir -p final-dist
    
    # 复制 Electron 应用
    if [ -d "sau_frontend/dist-electron" ]; then
        cp -r sau_frontend/dist-electron/* final-dist/
        echo "✅ 已复制 Electron 应用到 final-dist/"
    fi
    
    # 检查是否有 .dmg 文件
    if ls final-dist/*.dmg 1> /dev/null 2>&1; then
        echo "🎉 构建成功！"
        echo "📁 分发文件位置: final-dist/"
        echo "💿 macOS 安装包: $(ls final-dist/*.dmg)"
        echo ""
        echo "📋 使用说明:"
        echo "  1. 双击 .dmg 文件"
        echo "  2. 拖拽应用到 Applications 文件夹"
        echo "  3. 首次运行可能需要在系统偏好设置中允许运行"
        echo "  4. 应用会自动启动后端服务并打开浏览器界面"
    else
        echo "⚠️  未找到 .dmg 文件，请检查构建日志"
    fi
}

# 清理临时文件
cleanup() {
    echo "🧹 清理临时文件..."
    
    # 清理 Python 构建文件
    rm -rf build/
    rm -rf dist/
    rm -f sau_backend.spec
    
    # 清理后端分发目录
    rm -rf backend-dist/
    
    echo "✅ 清理完成"
}

# 检查 Playwright 浏览器
check_playwright() {
    echo "🌐 检查 Playwright 浏览器..."
    activate_venv
    
    if python3 -c "from playwright.sync_api import sync_playwright; sync_playwright().start()" &> /dev/null; then
        echo "✅ Playwright 浏览器已安装"
    else
        echo "⚠️ Playwright 浏览器未安装或损坏"
        echo "💡 建议运行: playwright install chromium"
    fi
}

# 主函数
main() {
    echo "======================================"
    echo "  SAU 自媒体自动化运营系统"
    echo "        一键构建工具"
    echo "======================================"
    
    # 检查是否在项目根目录
    if [ ! -f "sau_backend.py" ] || [ ! -d "sau_frontend" ]; then
        echo "❌ 请在项目根目录运行此脚本"
        exit 1
    fi
    
    check_dependencies
    check_playwright
    build_frontend
    build_backend
    build_electron
    create_distribution
    
    echo ""
    echo "🎉🎉🎉 构建完成！🎉🎉🎉"
    echo ""
    echo "🚀 现在可以在任何 macOS 设备上一键安装运行了！"
}

# 如果提供了 --clean 参数，先清理
if [ "$1" = "--clean" ]; then
    cleanup
    echo "清理完成，如需构建请重新运行脚本"
    exit 0
fi

# 运行主函数
main

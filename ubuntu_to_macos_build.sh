#!/bin/bash

# SAU Ubuntu 到 macOS 跨平台构建脚本

set -e

echo "🚀 Ubuntu 环境构建 macOS 应用..."

# 安装跨平台构建所需的依赖
install_build_deps() {
    echo "📦 安装构建依赖..."
    cd sau_frontend
    
    # 确保有基础依赖
    if [ ! -d "node_modules" ]; then
        if command -v yarn &> /dev/null; then
            yarn install
        else
            npm install
        fi
    fi
    
    # 安装跨平台构建依赖（避免 DMG 相关问题）
    echo "安装 electron-builder 和相关依赖..."
    
    if command -v yarn &> /dev/null; then
        yarn add -D electron-builder@24.6.4
        # 不安装 dmg-license，改为构建目录格式
    else
        npm install --save-dev electron-builder@24.6.4
    fi
    
    cd ..
}

# 更新 package.json 配置
update_package_config() {
    echo "⚙️ 更新 package.json 配置..."
    cd sau_frontend
    
    # 使用简化的配置避免 DMG 相关问题
    cat > temp_build_config.json << 'EOF'
{
  "appId": "com.sau.media.automation",
  "productName": "SAU自媒体自动化运营系统",
  "directories": {
    "output": "dist-electron"
  },
  "files": [
    "dist/**/*",
    "electron/**/*",
    "resources/**/*"
  ],
  "extraResources": [
    {
      "from": "resources/backend",
      "to": "backend"
    }
  ],
  "mac": {
    "target": [
      {
        "target": "dir",
        "arch": ["x64"]
      }
    ]
  }
}
EOF

    # 更新 package.json
    node -e "
    const fs = require('fs');
    const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
    const buildConfig = JSON.parse(fs.readFileSync('temp_build_config.json', 'utf8'));
    
    pkg.main = 'electron/main.js';
    pkg.homepage = './';
    pkg.build = buildConfig;
    
    fs.writeFileSync('package.json', JSON.stringify(pkg, null, 2));
    "
    
    rm temp_build_config.json
    cd ..
    echo "✅ package.json 已更新"
}

# 构建后端
build_backend() {
    echo "🐍 构建后端..."
    source .env/bin/activate
    python3 build_backend.py
}

# 构建前端
build_frontend() {
    echo "🎨 构建前端..."
    cd sau_frontend
    if command -v yarn &> /dev/null; then
        yarn build
    else
        npm run build
    fi
    cd ..
}

# 准备资源
prepare_resources() {
    echo "📦 准备应用资源..."
    mkdir -p sau_frontend/resources/backend
    if [ -d "backend-dist" ]; then
        cp -r backend-dist/* sau_frontend/resources/backend/
        echo "✅ 后端资源已准备"
    else
        echo "❌ 后端构建失败"
        exit 1
    fi
}

# 构建 Electron（避免 DMG）
build_electron_dir() {
    echo "⚡ 构建 Electron 应用（目录格式）..."
    cd sau_frontend
    
    # 设置环境变量
    export CSC_IDENTITY_AUTO_DISCOVERY=false
    export ELECTRON_BUILDER_ALLOW_UNRESOLVED_DEPENDENCIES=true
    
    # 直接使用 electron-builder 构建目录格式
    npx electron-builder --mac --x64 --dir --publish=never
    
    cd ..
    echo "✅ Electron 应用构建完成"
}

# 创建可移植的应用包
create_portable_app() {
    echo "📦 创建可移植应用包..."
    
    mkdir -p final-dist
    
    if [ -d "sau_frontend/dist-electron/mac" ]; then
        # 找到 .app 文件
        APP_FILE=$(find sau_frontend/dist-electron/mac -name "*.app" -type d | head -1)
        
        if [ -n "$APP_FILE" ]; then
            APP_NAME=$(basename "$APP_FILE" .app)
            
            # 创建分发包
            echo "📱 打包应用: $APP_NAME"
            
            # 复制到最终目录
            cp -r "$APP_FILE" final-dist/
            
            # 创建压缩包
            cd final-dist
            tar -czf "${APP_NAME}.tar.gz" "$(basename "$APP_FILE")"
            cd ..
            
            # 创建安装说明
            cat > final-dist/安装说明.txt << 'EOF'
# SAU 自媒体自动化运营系统 - macOS 安装说明

## 安装步骤:

1. 解压 .tar.gz 文件:
   tar -xzf *.tar.gz

2. 将 .app 文件拖拽到 Applications 文件夹

3. 首次运行前，安装 Playwright 浏览器驱动:
   pip3 install playwright
   playwright install chromium

4. 右键点击应用，选择"打开"（绕过安全限制）

## 注意事项:

- 确保 macOS 版本 10.14 或更高
- 需要 Python 3.8+ 环境
- 首次启动可能需要几分钟来初始化后端服务
- 应用启动后会在浏览器中打开管理界面

## 故障排除:

如果应用无法启动，请检查:
1. 控制台应用中的错误日志
2. 确保 Python 和 Playwright 正确安装
3. 检查防火墙设置是否阻止了本地服务

技术支持: 查看应用内的日志文件
EOF

            echo "🎉 构建成功！"
            echo "📁 应用包位置: final-dist/"
            echo "📦 压缩包: final-dist/${APP_NAME}.tar.gz"
            echo "📄 安装说明: final-dist/安装说明.txt"
            
        else
            echo "❌ 未找到 .app 文件"
            exit 1
        fi
    else
        echo "❌ 未找到构建结果"
        exit 1
    fi
}

# 主函数
main() {
    echo "======================================"
    echo "  SAU Ubuntu→macOS 跨平台构建"
    echo "======================================"
    
    # 检查环境
    if [ ! -f "sau_backend.py" ] || [ ! -d "sau_frontend" ]; then
        echo "❌ 请在项目根目录运行此脚本"
        exit 1
    fi
    
    if [ ! -d ".env" ]; then
        echo "❌ 未找到 Python 虚拟环境"
        exit 1
    fi
    
    if [ ! -f "conf.py" ]; then
        echo "❌ 请先配置 conf.py 文件"
        exit 1
    fi
    
    # 执行构建
    install_build_deps
    update_package_config
    build_backend
    build_frontend
    prepare_resources
    build_electron_dir
    create_portable_app
    
    echo ""
    echo "🎉🎉🎉 构建完成！🎉🎉🎉"
    echo ""
    echo "将 final-dist/ 目录中的文件传输到 macOS 设备即可安装使用"
}

# 清理函数
cleanup() {
    echo "🧹 清理构建文件..."
    rm -rf build/ dist/ *.spec backend-dist/
    rm -rf sau_frontend/dist-electron/ sau_frontend/resources/
    echo "✅ 清理完成"
}

# 处理参数
if [ "$1" = "--clean" ]; then
    cleanup
    exit 0
fi

# 运行主函数
main
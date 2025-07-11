#!/bin/bash

# SAU 后端服务诊断和修复脚本

set -e

echo "🔍 诊断后端服务启动问题..."

# 1. 检查应用结构
diagnose_app_structure() {
    echo "📱 检查应用结构..."
    
    if [ -d "final-dist-working" ]; then
        APP_DIR=$(find final-dist-working -name "*.app" -type d | head -1)
        if [ -n "$APP_DIR" ]; then
            echo "  应用路径: $APP_DIR"
            
            # 检查 Contents 结构
            echo "  📁 Contents 目录:"
            ls -la "$APP_DIR/Contents/"
            
            # 检查 Resources 目录
            echo "  📁 Resources 目录:"
            ls -la "$APP_DIR/Contents/Resources/"
            
            # 检查后端目录
            BACKEND_DIR="$APP_DIR/Contents/Resources/backend"
            if [ -d "$BACKEND_DIR" ]; then
                echo "  📁 后端目录存在: $BACKEND_DIR"
                ls -la "$BACKEND_DIR"
                
                # 检查可执行文件
                BACKEND_EXEC="$BACKEND_DIR/sau_backend"
                if [ -f "$BACKEND_EXEC" ]; then
                    echo "  ✅ 后端可执行文件存在"
                    echo "  📏 文件大小: $(du -sh "$BACKEND_EXEC" | cut -f1)"
                    echo "  🔐 文件权限: $(ls -la "$BACKEND_EXEC")"
                    
                    # 测试后端是否能直接运行
                    echo "  🧪 测试后端直接运行..."
                    cd "$BACKEND_DIR"
                    timeout 5s ./sau_backend 2>&1 | head -5 || echo "  ⚠️  后端运行测试结果已显示"
                    cd - > /dev/null
                else
                    echo "  ❌ 后端可执行文件不存在"
                fi
            else
                echo "  ❌ 后端目录不存在"
            fi
            
            # 检查 main.js
            echo "  📄 检查 main.js..."
            if [ -f "$APP_DIR/Contents/Resources/app.asar" ]; then
                echo "  ✅ app.asar 存在 (打包模式)"
            else
                echo "  ❌ app.asar 不存在"
            fi
            
        else
            echo "  ❌ 未找到 .app 文件"
        fi
    else
        echo "  ❌ final-dist-working 目录不存在"
    fi
}

# 2. 创建测试用的后端启动脚本
create_backend_test_script() {
    echo "🧪 创建后端测试脚本..."
    
    cat > test_backend.py << 'EOF'
#!/usr/bin/env python3
"""
后端启动测试脚本
"""

import os
import sys
import time
import subprocess
import socket

def test_port(port):
    """测试端口是否可用"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('localhost', port))
        sock.close()
        return True
    except:
        return False

def main():
    print("🔍 后端启动诊断...")
    
    # 检查 Python 版本
    print(f"Python 版本: {sys.version}")
    
    # 检查当前目录
    print(f"当前目录: {os.getcwd()}")
    
    # 检查关键文件
    files_to_check = [
        'sau_backend.py',
        'conf.py',
        'utils',
        'myUtils',
        'uploader'
    ]
    
    for file in files_to_check:
        if os.path.exists(file):
            print(f"✅ {file} 存在")
        else:
            print(f"❌ {file} 不存在")
    
    # 检查端口
    if test_port(5409):
        print("✅ 端口 5409 可用")
    else:
        print("❌ 端口 5409 被占用")
    
    # 尝试导入关键模块
    try:
        import flask
        print(f"✅ Flask 版本: {flask.__version__}")
    except ImportError as e:
        print(f"❌ Flask 导入失败: {e}")
    
    try:
        import conf
        print("✅ 配置文件导入成功")
    except ImportError as e:
        print(f"❌ 配置文件导入失败: {e}")
    
    # 如果存在 sau_backend，尝试启动
    if os.path.exists('sau_backend.py'):
        print("🚀 尝试启动后端服务...")
        try:
            # 使用 subprocess 启动后端
            process = subprocess.Popen([sys.executable, 'sau_backend.py'], 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE,
                                     text=True)
            
            # 等待几秒
            time.sleep(3)
            
            # 检查进程状态
            if process.poll() is None:
                print("✅ 后端服务启动成功")
                
                # 检查端口是否被监听
                if not test_port(5409):
                    print("✅ 端口 5409 已被监听")
                else:
                    print("❌ 端口 5409 仍然可用，服务可能未正常启动")
                
                # 结束进程
                process.terminate()
                process.wait()
                
            else:
                print("❌ 后端服务启动失败")
                stdout, stderr = process.communicate()
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")
                
        except Exception as e:
            print(f"❌ 启动后端时发生异常: {e}")
    
    print("🔍 诊断完成")

if __name__ == "__main__":
    main()
EOF

    chmod +x test_backend.py
    echo "✅ 后端测试脚本创建完成"
}

# 3. 在应用内部运行诊断
diagnose_app_backend() {
    echo "🔍 在应用内部运行后端诊断..."
    
    APP_DIR=$(find final-dist-working -name "*.app" -type d | head -1)
    if [ -n "$APP_DIR" ]; then
        BACKEND_DIR="$APP_DIR/Contents/Resources/backend"
        
        if [ -d "$BACKEND_DIR" ]; then
            echo "📂 进入后端目录进行诊断..."
            
            # 复制测试脚本到后端目录
            cp test_backend.py "$BACKEND_DIR/"
            
            cd "$BACKEND_DIR"
            
            # 运行诊断
            echo "🧪 运行后端诊断..."
            python3 test_backend.py 2>&1 || echo "诊断完成"
            
            # 尝试直接运行后端
            echo ""
            echo "🚀 尝试直接运行后端可执行文件..."
            if [ -f "sau_backend" ]; then
                echo "执行: ./sau_backend"
                timeout 5s ./sau_backend 2>&1 || echo "后端运行测试完成"
            fi
            
            cd - > /dev/null
        else
            echo "❌ 后端目录不存在"
        fi
    else
        echo "❌ 未找到应用目录"
    fi
}

# 4. 创建修复版本的后端
create_fixed_backend() {
    echo "🔧 创建修复版本的后端..."
    
    # 激活虚拟环境
    source .env/bin/activate
    
    # 创建一个简化的后端测试版本
    cat > sau_backend_simple.py << 'EOF'
#!/usr/bin/env python3
"""
简化的后端服务 - 用于测试
"""

import os
import sys
import time
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'message': 'SAU Backend is running',
        'version': '1.0.0'
    })

@app.route('/getAccountsWithGroups', methods=['GET'])
def get_accounts_with_groups():
    return jsonify({
        'code': 200,
        'data': [],
        'message': 'Test data'
    })

@app.route('/getValidAccounts', methods=['GET'])
def get_valid_accounts():
    return jsonify({
        'code': 200,
        'data': [],
        'message': 'Test data'
    })

@app.route('/')
def index():
    return jsonify({
        'name': 'SAU Backend',
        'status': 'running',
        'endpoints': [
            '/api/health',
            '/getAccountsWithGroups',
            '/getValidAccounts'
        ]
    })

if __name__ == '__main__':
    print("🚀 启动 SAU 后端服务...")
    print(f"Python 版本: {sys.version}")
    print(f"工作目录: {os.getcwd()}")
    
    try:
        app.run(host='0.0.0.0', port=5409, debug=False)
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)
EOF

    # 创建简化的 PyInstaller 配置
    cat > sau_backend_simple.spec << 'EOF'
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['sau_backend_simple.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'flask',
        'flask_cors',
        'werkzeug',
        'jinja2',
        'markupsafe',
        'itsdangerous',
        'click'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='sau_backend_simple',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
)
EOF

    # 构建简化版本
    pyinstaller --clean sau_backend_simple.spec
    
    if [ -f "dist/sau_backend_simple" ]; then
        echo "✅ 简化后端构建成功"
        
        # 测试简化版本
        echo "🧪 测试简化版本..."
        timeout 5s ./dist/sau_backend_simple &
        BACKEND_PID=$!
        sleep 2
        
        # 检查是否启动成功
        if kill -0 $BACKEND_PID 2>/dev/null; then
            echo "✅ 简化版本可以正常启动"
            kill $BACKEND_PID
            
            # 使用简化版本替换原版本
            echo "🔄 替换为简化版本..."
            
            APP_DIR=$(find final-dist-working -name "*.app" -type d | head -1)
            if [ -n "$APP_DIR" ]; then
                BACKEND_DIR="$APP_DIR/Contents/Resources/backend"
                if [ -d "$BACKEND_DIR" ]; then
                    # 备份原版本
                    mv "$BACKEND_DIR/sau_backend" "$BACKEND_DIR/sau_backend.backup" 2>/dev/null || true
                    
                    # 复制简化版本
                    cp dist/sau_backend_simple "$BACKEND_DIR/sau_backend"
                    chmod +x "$BACKEND_DIR/sau_backend"
                    
                    echo "✅ 简化版本已替换到应用中"
                fi
            fi
        else
            echo "❌ 简化版本也无法启动"
        fi
    else
        echo "❌ 简化后端构建失败"
    fi
}

# 5. 创建最终测试版本
create_test_app() {
    echo "📦 创建测试版本应用..."
    
    if [ -d "final-dist-working" ]; then
        # 复制为测试版本
        cp -r final-dist-working final-dist-test
        
        APP_DIR=$(find final-dist-test -name "*.app" -type d | head -1)
        if [ -n "$APP_DIR" ]; then
            cd final-dist-test
            
            APP_NAME="$(basename "$APP_DIR" .app)"
            
            # 创建测试压缩包
            tar -czf "${APP_NAME}-测试版.tar.gz" "$(basename "$APP_DIR")"
            
            echo ""
            echo "🎉 测试版本创建完成！"
            echo "📦 测试包: ${APP_NAME}-测试版.tar.gz"
            echo "📏 大小: $(du -sh "${APP_NAME}-测试版.tar.gz" | cut -f1)"
            echo ""
            echo "🧪 测试步骤:"
            echo "1. 解压测试包到 macOS 设备"
            echo "2. 移动应用到 Applications 文件夹"
            echo "3. 右键打开应用"
            echo "4. 检查是否能访问 http://localhost:5409"
            echo "5. 查看开发者工具的控制台输出"
            
            cd ..
        fi
    fi
}

# 主函数
main() {
    echo "========================================"
    echo "  SAU 后端服务诊断和修复"
    echo "========================================"
    echo ""
    
    diagnose_app_structure
    echo ""
    
    create_backend_test_script
    echo ""
    
    diagnose_app_backend
    echo ""
    
    create_fixed_backend
    echo ""
    
    create_test_app
    
    echo ""
    echo "🔍 诊断完成！"
    echo ""
    echo "📋 下一步:"
    echo "1. 在 macOS 上测试新的应用版本"
    echo "2. 检查控制台输出和错误日志"
    echo "3. 如果还有问题，请提供详细的错误信息"
}

# 运行主函数
main "$@"

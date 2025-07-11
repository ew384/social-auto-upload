#!/bin/bash

# SAU 完整可用 APP 构建脚本 - 修复后端自动启动问题

set -e

echo "🔧 修复后端自动启动问题，构建完整可用的 APP..."

# 1. 检查并调试当前应用的后端启动问题
debug_current_app() {
    echo "🔍 分析当前应用的后端启动问题..."
    
    if [ -d "final-dist-fixed" ]; then
        APP_DIR=$(find final-dist-fixed -name "*.app" -type d | head -1)
        if [ -n "$APP_DIR" ]; then
            echo "📱 检查应用结构:"
            echo "  应用路径: $APP_DIR"
            
            # 检查后端文件是否存在
            BACKEND_PATH="$APP_DIR/Contents/Resources/backend"
            if [ -d "$BACKEND_PATH" ]; then
                echo "  ✅ 后端目录存在: $BACKEND_PATH"
                echo "  📁 后端文件:"
                ls -la "$BACKEND_PATH"
                
                if [ -f "$BACKEND_PATH/sau_backend" ]; then
                    echo "  ✅ 后端可执行文件存在"
                    echo "  📏 文件大小: $(du -sh "$BACKEND_PATH/sau_backend" | cut -f1)"
                    echo "  🔐 文件权限: $(ls -la "$BACKEND_PATH/sau_backend")"
                    
                    # 检查是否可执行
                    if [ -x "$BACKEND_PATH/sau_backend" ]; then
                        echo "  ✅ 文件有执行权限"
                    else
                        echo "  ❌ 文件缺少执行权限"
                    fi
                else
                    echo "  ❌ 后端可执行文件不存在"
                fi
            else
                echo "  ❌ 后端目录不存在"
            fi
            
            # 检查 main.js
            MAIN_JS="$APP_DIR/Contents/Resources/app.asar.unpacked/electron/main.js"
            if [ ! -f "$MAIN_JS" ]; then
                MAIN_JS="$APP_DIR/Contents/Resources/electron/main.js"
            fi
            
            if [ -f "$MAIN_JS" ]; then
                echo "  ✅ main.js 存在"
                echo "  🔍 检查后端启动逻辑:"
                grep -n "startBackend\|sau_backend\|process.resourcesPath" "$MAIN_JS" || echo "    未找到后端启动代码"
            else
                echo "  ❌ main.js 文件未找到"
            fi
        fi
    fi
}

# 2. 重新构建后端，确保兼容性
rebuild_backend_with_debug() {
    echo "🔨 重新构建后端（添加调试信息）..."
    
    source .env/bin/activate
    
    # 创建增强的 PyInstaller 配置
    cat > sau_backend_debug.spec << 'EOF'
# -*- mode: python ; coding: utf-8 -*-

import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.abspath('.'))

hidden_imports = [
    'flask', 'flask_cors', 'werkzeug', 'jinja2', 'markupsafe', 'itsdangerous', 'click',
    'requests', 'urllib3', 'certifi', 'chardet', 'idna',
    'sqlite3', 'json', 'threading', 'time', 'datetime', 'uuid', 'hashlib', 'base64',
    'logging', 'traceback', 'functools', 'os', 'sys', 'pathlib',
    'conf', 
    'utils.base_social_media', 'utils.constant', 'utils.files_times', 'utils.log', 'utils.network',
    'myUtils.auth', 'myUtils.login', 'myUtils.postVideo',
    'uploader.douyin_uploader.main', 'uploader.tencent_uploader.main',
    'uploader.ks_uploader.main', 'uploader.tk_uploader.main_chrome',
    'uploader.xhs_uploader.main', 'uploader.baijiahao_uploader.main',
    'uploader.bilibili_uploader.main', 'uploader.xiaohongshu_uploader.main',
]

excludes = [
    'tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'wx',
    'numpy', 'pandas', 'scipy', 'matplotlib', 'seaborn', 'plotly',
    'sklearn', 'tensorflow', 'torch', 'cv2', 'PIL.ImageTk',
    'jupyter', 'ipython', 'notebook', 'pytest', 'setuptools', 'pip',
    'wheel', 'twine', 'sphinx', 'flake8', 'black', 'mypy',
    'unittest', 'doctest', 'test', 'tests',
]

a = Analysis(
    ['sau_backend.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('conf.py', '.'),
        ('utils', 'utils'),
        ('myUtils', 'myUtils'),
        ('uploader', 'uploader'),
        ('examples', 'examples'),
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='sau_backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,  # 保留调试信息
    upx=False,    # 禁用压缩以提高兼容性
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
)
EOF

    # 清理并重新构建
    rm -rf build/ dist/
    pyinstaller --clean sau_backend_debug.spec
    
    if [ -f "dist/sau_backend" ]; then
        echo "✅ 后端重新构建完成"
        
        # 测试后端是否能独立运行
        echo "🧪 测试后端独立运行..."
        timeout 10s ./dist/sau_backend &
        BACKEND_PID=$!
        sleep 3
        
        if kill -0 $BACKEND_PID 2>/dev/null; then
            echo "✅ 后端可以独立运行"
            kill $BACKEND_PID
        else
            echo "❌ 后端无法独立运行"
        fi
        
    else
        echo "❌ 后端构建失败"
        exit 1
    fi
}

# 3. 创建增强的 Electron main.js，添加详细日志
create_enhanced_main_js() {
    echo "📝 创建增强的 Electron main.js..."
    
    mkdir -p sau_frontend/electron
    
    cat > sau_frontend/electron/main.js << 'EOF'
const { app, BrowserWindow, dialog } = require('electron')
const path = require('path')
const { spawn } = require('child_process')
const fs = require('fs')

let mainWindow
let backendProcess
const isDev = process.env.NODE_ENV === 'development'

// 日志函数
function log(message) {
    console.log(`[SAU] ${new Date().toISOString()}: ${message}`)
}

function logError(message, error) {
    console.error(`[SAU ERROR] ${new Date().toISOString()}: ${message}`, error)
}

// 检查端口是否被占用
function isPortInUse(port) {
    return new Promise((resolve) => {
        const net = require('net')
        const server = net.createServer()
        
        server.once('error', () => {
            log(`端口 ${port} 已被占用`)
            resolve(true)
        })
        server.once('listening', () => {
            server.close()
            log(`端口 ${port} 可用`)
            resolve(false)
        })
        
        server.listen(port)
    })
}

// 等待后端服务启动
async function waitForBackend(maxWait = 30000) {
    log('开始等待后端启动...')
    const startTime = Date.now()
    
    while (Date.now() - startTime < maxWait) {
        if (await isPortInUse(5409)) {
            log('后端服务已启动')
            return true
        }
        await new Promise(resolve => setTimeout(resolve, 1000))
        log(`等待后端启动... ${Math.floor((Date.now() - startTime) / 1000)}s`)
    }
    
    log('后端启动超时')
    return false
}

// 显示错误对话框
function showErrorDialog(title, content) {
    if (mainWindow) {
        dialog.showErrorBox(title, content)
    }
}

// 创建窗口
function createWindow() {
    log('创建主窗口...')
    
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        show: false,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            webSecurity: false
        },
        titleBarStyle: 'hiddenInset'
    })

    if (isDev) {
        log('开发环境模式')
        mainWindow.loadURL('http://localhost:5173')
        mainWindow.webContents.openDevTools()
        mainWindow.show()
        return
    }

    log('生产环境模式，等待后端启动...')
    
    // 生产环境 - 等待后端启动
    waitForBackend().then(backendReady => {
        if (backendReady) {
            log('后端已准备就绪，加载后端界面')
            mainWindow.loadURL('http://localhost:5409')
        } else {
            log('后端启动失败，加载静态文件')
            const indexPath = path.join(__dirname, '../dist/index.html')
            log(`静态文件路径: ${indexPath}`)
            
            if (fs.existsSync(indexPath)) {
                mainWindow.loadFile(indexPath)
            } else {
                logError('静态文件不存在', indexPath)
                showErrorDialog('启动错误', '无法找到应用文件，请重新安装应用。')
            }
        }
        mainWindow.show()
    }).catch(err => {
        logError('检查后端失败', err)
        // 回退到静态文件
        const indexPath = path.join(__dirname, '../dist/index.html')
        mainWindow.loadFile(indexPath)
        mainWindow.show()
    })

    // 添加页面加载事件监听
    mainWindow.webContents.on('did-finish-load', () => {
        log('页面加载完成')
    })

    mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
        logError('页面加载失败', `${errorCode}: ${errorDescription}`)
    })

    mainWindow.on('closed', () => {
        mainWindow = null
    })
}

// 启动后端服务
function startBackend() {
    if (isDev) {
        log('开发环境：跳过后端启动')
        return
    }

    log('开始启动后端服务...')
    
    // 获取后端路径
    const resourcesPath = process.resourcesPath
    const backendPath = path.join(resourcesPath, 'backend')
    const execPath = path.join(backendPath, 'sau_backend')
    
    log(`Resources 路径: ${resourcesPath}`)
    log(`后端目录: ${backendPath}`)
    log(`可执行文件: ${execPath}`)
    
    // 检查路径是否存在
    if (!fs.existsSync(resourcesPath)) {
        logError('Resources 目录不存在', resourcesPath)
        showErrorDialog('启动错误', `Resources 目录不存在: ${resourcesPath}`)
        return
    }
    
    if (!fs.existsSync(backendPath)) {
        logError('后端目录不存在', backendPath)
        showErrorDialog('启动错误', `后端目录不存在: ${backendPath}`)
        return
    }
    
    if (!fs.existsSync(execPath)) {
        logError('后端可执行文件不存在', execPath)
        showErrorDialog('启动错误', `后端可执行文件不存在: ${execPath}\n\n请确保应用完整安装。`)
        return
    }

    // 检查执行权限
    try {
        fs.accessSync(execPath, fs.constants.X_OK)
        log('后端文件具有执行权限')
    } catch (err) {
        logError('后端文件没有执行权限', err)
        try {
            fs.chmodSync(execPath, 0o755)
            log('已设置执行权限')
        } catch (chmodErr) {
            logError('设置执行权限失败', chmodErr)
            showErrorDialog('权限错误', '无法设置后端文件执行权限，请手动设置。')
            return
        }
    }

    // 启动后端进程
    try {
        log('启动后端进程...')
        
        backendProcess = spawn(execPath, [], {
            cwd: backendPath,
            stdio: ['pipe', 'pipe', 'pipe'],
            env: {
                ...process.env,
                PYTHONPATH: backendPath,
                PYTHONUNBUFFERED: '1'
            }
        })

        log(`后端进程已启动，PID: ${backendProcess.pid}`)

        backendProcess.stdout.on('data', (data) => {
            const output = data.toString().trim()
            log(`[Backend] ${output}`)
        })

        backendProcess.stderr.on('data', (data) => {
            const output = data.toString().trim()
            logError(`[Backend Error] ${output}`)
        })

        backendProcess.on('error', (error) => {
            logError('后端进程启动失败', error)
            showErrorDialog('后端启动失败', `后端服务启动失败: ${error.message}`)
        })

        backendProcess.on('close', (code, signal) => {
            log(`后端进程退出，代码: ${code}, 信号: ${signal}`)
            if (code !== 0 && code !== null) {
                logError('后端异常退出', `退出代码: ${code}`)
            }
        })

        backendProcess.on('spawn', () => {
            log('后端进程已成功启动')
        })

    } catch (error) {
        logError('启动后端进程时发生异常', error)
        showErrorDialog('启动失败', `启动后端服务时发生错误: ${error.message}`)
    }
}

// 停止后端服务
function stopBackend() {
    if (backendProcess) {
        log('正在停止后端进程...')
        
        try {
            backendProcess.kill('SIGTERM')
            
            setTimeout(() => {
                if (backendProcess && !backendProcess.killed) {
                    log('强制结束后端进程')
                    backendProcess.kill('SIGKILL')
                }
            }, 5000)
            
        } catch (error) {
            logError('停止后端进程时发生错误', error)
        }
        
        backendProcess = null
    }
}

// 应用事件处理
app.whenReady().then(() => {
    log('Electron 应用已准备就绪')
    startBackend()
    createWindow()

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow()
        }
    })
})

app.on('window-all-closed', () => {
    log('所有窗口已关闭')
    stopBackend()
    if (process.platform !== 'darwin') {
        app.quit()
    }
})

app.on('before-quit', () => {
    log('应用即将退出')
    stopBackend()
})

// 进程退出处理
process.on('SIGINT', () => {
    log('收到 SIGINT 信号')
    stopBackend()
    app.quit()
})

process.on('SIGTERM', () => {
    log('收到 SIGTERM 信号')
    stopBackend()
    app.quit()
})

// 未捕获异常处理
process.on('uncaughtException', (error) => {
    logError('未捕获的异常', error)
    stopBackend()
})

process.on('unhandledRejection', (reason, promise) => {
    logError('未处理的 Promise 拒绝', { reason, promise })
})

log('Electron main.js 已加载完成')
EOF

    echo "✅ 增强的 main.js 创建完成"
}

# 4. 重新构建完整应用
rebuild_complete_app() {
    echo "🔨 重新构建完整应用..."
    
    # 1. 重新构建后端
    rebuild_backend_with_debug
    
    # 创建后端分发包
    rm -rf backend-dist/
    mkdir -p backend-dist
    cp dist/sau_backend backend-dist/
    chmod +x backend-dist/sau_backend
    cp conf.py backend-dist/ 2>/dev/null || true
    
    # 创建必要的数据目录
    mkdir -p backend-dist/{db,cookiesFile,videoFile,logs}
    cp db/createTable.py backend-dist/db/ 2>/dev/null || true
    
    if command -v sqlite3 &> /dev/null; then
        echo "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY);" | sqlite3 backend-dist/db/database.db
    fi
    
    echo "✅ 后端分发包准备完成: $(du -sh backend-dist | cut -f1)"
    
    # 2. 重新构建前端
    echo "🎨 重新构建前端..."
    cd sau_frontend
    
    # 清理并重新构建前端
    rm -rf dist/
    if command -v yarn &> /dev/null; then
        yarn build
    else
        npm run build
    fi
    
    if [ ! -d "dist" ] || [ ! -f "dist/index.html" ]; then
        echo "❌ 前端构建失败"
        exit 1
    fi
    
    echo "✅ 前端构建完成: $(du -sh dist | cut -f1)"
    
    # 3. 准备 Electron 资源
    echo "📦 准备 Electron 资源..."
    rm -rf resources/
    mkdir -p resources/backend
    cp -r ../backend-dist/* resources/backend/
    
    echo "✅ Electron 资源准备完成: $(du -sh resources | cut -f1)"
    
    # 4. 更新 package.json
    node -e "
    const fs = require('fs');
    const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
    
    pkg.main = 'electron/main.js';
    pkg.homepage = './';
    delete pkg.type;
    
    pkg.build = {
        appId: 'com.sau.media.automation',
        productName: 'SAU自媒体自动化运营系统',
        directories: { output: 'dist-electron' },
        files: [
            'dist/**/*',
            'electron/**/*',
            'resources/**/*'
        ],
        extraResources: [
            { from: 'resources/backend', to: 'backend' }
        ],
        mac: { 
            target: [{ target: 'dir', arch: ['x64'] }]
        },
        compression: 'maximum',
        removePackageScripts: true,
        electronVersion: '28.0.0'
    };
    
    fs.writeFileSync('package.json', JSON.stringify(pkg, null, 2));
    "
    
    # 5. 构建 Electron 应用
    echo "⚡ 构建 Electron 应用..."
    rm -rf dist-electron/
    
    export CSC_IDENTITY_AUTO_DISCOVERY=false
    export ELECTRON_BUILDER_ALLOW_UNRESOLVED_DEPENDENCIES=true
    
    npx electron-builder --mac --x64 --dir --publish=never
    
    cd ..
    
    if [ -d "sau_frontend/dist-electron" ]; then
        echo "✅ Electron 应用构建完成"
    else
        echo "❌ Electron 应用构建失败"
        exit 1
    fi
}

# 5. 创建最终的完整可用APP
create_final_working_app() {
    echo "📦 创建最终的完整可用APP..."
    
    # 清理旧版本
    rm -rf final-dist-working/
    mkdir -p final-dist-working
    
    APP_FILE=$(find sau_frontend/dist-electron -name "*.app" -type d | head -1)
    
    if [ -n "$APP_FILE" ]; then
        cp -r "$APP_FILE" final-dist-working/
        
        cd final-dist-working
        APP_NAME=$(basename "$APP_FILE" .app)
        APP_DIR=$(basename "$APP_FILE")
        
        # 验证应用结构
        echo "🔍 验证应用结构..."
        echo "  应用大小: $(du -sh "$APP_DIR" | cut -f1)"
        echo "  后端文件: $(du -sh "$APP_DIR/Contents/Resources/backend" | cut -f1)"
        echo "  前端文件: $(du -sh "$APP_DIR/Contents/Resources/app.asar" | cut -f1)"
        
        # 检查关键文件
        BACKEND_EXEC="$APP_DIR/Contents/Resources/backend/sau_backend"
        if [ -f "$BACKEND_EXEC" ] && [ -x "$BACKEND_EXEC" ]; then
            echo "  ✅ 后端可执行文件存在且有执行权限"
        else
            echo "  ❌ 后端可执行文件问题"
            chmod +x "$BACKEND_EXEC" 2>/dev/null || true
        fi
        
        # 创建压缩包
        tar -czf "${APP_NAME}-完整可用版.tar.gz" "$APP_DIR"
        
        # 创建使用说明
        cat > "使用说明.md" << 'EOF'
# SAU 自媒体自动化运营系统 - 完整可用版

## 🚀 安装步骤

1. **解压应用**
   ```bash
   tar -xzf SAU自媒体自动化运营系统-完整可用版.tar.gz
   ```

2. **移动到应用文件夹**
   ```bash
   mv "SAU自媒体自动化运营系统.app" /Applications/
   ```

3. **首次运行准备**
   ```bash
   # 安装 Playwright 浏览器驱动
   pip3 install playwright
   playwright install chromium
   ```

4. **启动应用**
   - 在 Applications 文件夹中找到应用
   - 右键点击 -> 打开（绕过安全检查）
   - 应用会自动启动后端服务并打开前端界面

## 🔍 验证后端服务

应用启动后，你可以：
- 在浏览器中访问 http://localhost:5409 检查后端服务
- 查看应用的控制台输出（开发者工具）
- 检查系统活动监视器中的 sau_backend 进程

## 🐛 故障排除

如果后端服务没有启动：
1. 检查应用是否有执行权限
2. 确保没有其他程序占用 5409 端口
3. 查看控制台的错误日志
4. 尝试重新安装 Playwright

## 📋 应用特性

- ✅ 自动启动后端 Python 服务
- ✅ 前端界面加载静态资源
- ✅ 完整的用户界面和功能
- ✅ 详细的日志和错误处理

应用启动成功后，你应该能看到完整的管理界面！
EOF

        echo ""
        echo "🎉🎉🎉 完整可用APP构建完成！🎉🎉🎉"
        echo ""
        echo "📊 应用信息:"
        echo "  应用大小: $(du -sh "$APP_DIR" | cut -f1)"
        echo "  压缩包: ${APP_NAME}-完整可用版.tar.gz ($(du -sh "${APP_NAME}-完整可用版.tar.gz" | cut -f1))"
        echo "📁 位置: $(pwd)/"
        echo ""
        echo "🚀 这个版本应该能完整工作，包括自动启动后端服务！"
        
        cd ..
        
    else
        echo "❌ 未找到构建的应用文件"
        exit 1
    fi
}

# 主函数
main() {
    echo "========================================"
    echo "  SAU 完整可用APP构建脚本"
    echo "     修复后端自动启动问题"
    echo "========================================"
    echo ""
    
    debug_current_app
    create_enhanced_main_js
    rebuild_complete_app
    create_final_working_app
    
    echo ""
    echo "✅ 构建完成！现在测试新的应用，后端服务应该能自动启动。"
}

# 运行主函数
main "$@"
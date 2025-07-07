#!/bin/bash

# SAU 自媒体发布系统一键构建脚本 (支持跨平台构建)

set -e  # 遇到错误立即退出

echo "🚀 开始构建 SAU 自媒体自动化运营系统..."

# 全局变量
PKG_MANAGER=""
TARGET_PLATFORM="darwin"  # 目标平台
TARGET_ARCH="x64"         # 目标架构

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

# 准备后端资源
prepare_backend_resources() {
    echo "📦 准备后端资源..."
    
    # 创建资源目录
    mkdir -p sau_frontend/resources/backend
    
    # 复制后端可执行文件和数据
    if [ -d "backend-dist" ]; then
        cp -r backend-dist/* sau_frontend/resources/backend/
        echo "✅ 后端资源已复制到 sau_frontend/resources/backend/"
    else
        echo "❌ 后端构建目录不存在"
        exit 1
    fi
}

# 创建或更新 package.json 中的 electron-builder 配置
update_electron_config() {
    echo "⚙️ 更新 Electron 配置..."
    cd sau_frontend
    
    # 使用 Node.js 更新 package.json
    node -e "
    const fs = require('fs');
    const path = require('path');
    
    const packagePath = './package.json';
    const pkg = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
    
    // 添加或更新 main 字段
    pkg.main = 'electron/main.js';
    
    // 添加或更新 homepage 字段
    pkg.homepage = './';
    
    // 添加或更新 scripts
    pkg.scripts = pkg.scripts || {};
    pkg.scripts['electron'] = 'electron .';
    pkg.scripts['electron:dev'] = 'concurrently \"npm run dev\" \"wait-on http://localhost:5173 && electron .\"';
    pkg.scripts['build:electron'] = 'electron-builder --mac --x64 --publish=never';
    pkg.scripts['build:electron:linux'] = 'electron-builder --linux --x64 --publish=never';
    pkg.scripts['build:electron:win'] = 'electron-builder --win --x64 --publish=never';
    
    // 添加或更新 build 配置
    pkg.build = {
        'appId': 'com.sau.media.automation',
        'productName': 'SAU自媒体自动化运营系统',
        'directories': {
            'output': 'dist-electron'
        },
        'files': [
            'dist/**/*',
            'electron/**/*',
            'resources/**/*'
        ],
        'extraResources': [
            {
                'from': 'resources/backend',
                'to': 'backend'
            }
        ],
        'mac': {
            'icon': 'public/vite.svg',
            'category': 'public.app-category.productivity',
            'target': [
                {
                    'target': 'dmg',
                    'arch': ['x64']
                }
            ]
        },
        'linux': {
            'icon': 'public/vite.svg',
            'category': 'Office',
            'target': [
                {
                    'target': 'AppImage',
                    'arch': ['x64']
                }
            ]
        },
        'win': {
            'icon': 'public/vite.svg',
            'target': [
                {
                    'target': 'nsis',
                    'arch': ['x64']
                }
            ]
        }
    };
    
    fs.writeFileSync(packagePath, JSON.stringify(pkg, null, 2));
    console.log('✅ package.json 已更新');
    "
    
    cd ..
}

# 修复 main.js 中的路径问题
fix_main_js() {
    echo "🔧 修复 main.js 路径问题..."
    
    cat > sau_frontend/electron/main.js << 'EOF'
const { app, BrowserWindow, Menu } = require('electron')
const path = require('path')
const { spawn } = require('child_process')
const net = require('net')

let mainWindow
let pythonProcess
const isDev = process.env.NODE_ENV === 'development'

// 检查端口是否被占用
function checkPort(port) {
  return new Promise((resolve) => {
    const server = net.createServer()
    server.listen(port, () => {
      server.once('close', () => resolve(true))
      server.close()
    })
    server.on('error', () => resolve(false))
  })
}

// 等待后端服务启动
function waitForBackend(maxRetries = 30) {
  return new Promise((resolve, reject) => {
    let retries = 0
    
    const check = () => {
      checkPort(5409).then(portAvailable => {
        if (!portAvailable) {
          console.log('✅ 后端服务已启动')
          resolve()
        } else if (retries < maxRetries) {
          retries++
          console.log(`⏳ 等待后端启动... (${retries}/${maxRetries})`)
          setTimeout(check, 1000)
        } else {
          reject(new Error('后端启动超时'))
        }
      })
    }
    
    check()
  })
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      webSecurity: false
    },
    titleBarStyle: 'hiddenInset',
    show: false,
    icon: path.join(__dirname, '../public/vite.svg')
  })

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
    mainWindow.show()
  } else {
    waitForBackend().then(() => {
      mainWindow.loadURL('http://localhost:5409')
      mainWindow.show()
    }).catch(err => {
      console.error('后端启动失败:', err)
      // 如果后端启动失败，加载静态文件
      mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
      mainWindow.show()
    })
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

function startPythonBackend() {
  if (isDev) {
    console.log('开发环境：跳过启动 Python 后端')
    return
  }

  // 修复后端路径
  const backendPath = path.join(process.resourcesPath, 'backend')
  let pythonExecutable = path.join(backendPath, 'sau_backend')
  
  // 检查可执行文件是否存在
  const fs = require('fs')
  if (!fs.existsSync(pythonExecutable)) {
    console.error('Python 后端可执行文件不存在:', pythonExecutable)
    return
  }

  console.log('启动 Python 后端:', pythonExecutable)
  console.log('工作目录:', backendPath)

  pythonProcess = spawn(pythonExecutable, [], {
    cwd: backendPath,
    stdio: ['pipe', 'pipe', 'pipe'],
    env: {
      ...process.env,
      PYTHONPATH: backendPath
    }
  })

  pythonProcess.stdout.on('data', (data) => {
    console.log(`[Backend] ${data.toString().trim()}`)
  })

  pythonProcess.stderr.on('data', (data) => {
    console.error(`[Backend Error] ${data.toString().trim()}`)
  })

  pythonProcess.on('close', (code) => {
    console.log(`Python 后端进程退出，代码: ${code}`)
  })

  pythonProcess.on('error', (err) => {
    console.error('Python 后端启动失败:', err)
  })
}

function stopPythonBackend() {
  if (pythonProcess) {
    console.log('正在停止 Python 后端...')
    pythonProcess.kill('SIGTERM')
    
    setTimeout(() => {
      if (pythonProcess && !pythonProcess.killed) {
        console.log('强制结束 Python 后端')
        pythonProcess.kill('SIGKILL')
      }
    }, 5000)
    
    pythonProcess = null
  }
}

function createMenu() {
  const template = [
    {
      label: 'SAU系统',
      submenu: [
        { role: 'about', label: '关于 SAU' },
        { type: 'separator' },
        { role: 'services', label: '服务' },
        { type: 'separator' },
        { role: 'hide', label: '隐藏' },
        { role: 'hideothers', label: '隐藏其他' },
        { role: 'unhide', label: '显示全部' },
        { type: 'separator' },
        { role: 'quit', label: '退出 SAU' }
      ]
    },
    {
      label: '编辑',
      submenu: [
        { role: 'undo', label: '撤销' },
        { role: 'redo', label: '重做' },
        { type: 'separator' },
        { role: 'cut', label: '剪切' },
        { role: 'copy', label: '复制' },
        { role: 'paste', label: '粘贴' },
        { role: 'selectall', label: '全选' }
      ]
    },
    {
      label: '视图',
      submenu: [
        { role: 'reload', label: '重新加载' },
        { role: 'forceReload', label: '强制重新加载' },
        { role: 'toggleDevTools', label: '开发者工具' },
        { type: 'separator' },
        { role: 'resetZoom', label: '实际大小' },
        { role: 'zoomIn', label: '放大' },
        { role: 'zoomOut', label: '缩小' },
        { type: 'separator' },
        { role: 'togglefullscreen', label: '切换全屏' }
      ]
    },
    {
      label: '窗口',
      submenu: [
        { role: 'minimize', label: '最小化' },
        { role: 'close', label: '关闭' }
      ]
    }
  ]

  const menu = Menu.buildFromTemplate(template)
  Menu.setApplicationMenu(menu)
}

app.whenReady().then(() => {
  createMenu()
  startPythonBackend()
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  stopPythonBackend()
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', () => {
  stopPythonBackend()
})

process.on('SIGINT', () => {
  stopPythonBackend()
  app.quit()
})

process.on('SIGTERM', () => {
  stopPythonBackend()
  app.quit()
})
EOF
    
    echo "✅ main.js 已修复"
}

# 构建 Electron 应用
build_electron() {
    echo "⚡ 构建 Electron 应用..."
    cd sau_frontend
    
    # 设置环境变量以支持跨平台构建
    export CSC_IDENTITY_AUTO_DISCOVERY=false
    
    # 构建应用
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
        echo "  1. 将 .dmg 文件传输到 macOS 设备"
        echo "  2. 双击 .dmg 文件"
        echo "  3. 拖拽应用到 Applications 文件夹"
        echo "  4. 首次运行可能需要在系统偏好设置中允许运行"
        echo "  5. 应用会自动启动后端服务并打开浏览器界面"
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
    
    # 清理前端资源
    rm -rf sau_frontend/resources/
    
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
    echo "    跨平台构建工具 (Ubuntu→macOS)"
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
    prepare_backend_resources
    update_electron_config
    fix_main_js
    build_electron
    create_distribution
    
    echo ""
    echo "🎉🎉🎉 构建完成！🎉🎉🎉"
    echo ""
    echo "🚀 现在可以在 macOS 设备上安装运行了！"
}

# 如果提供了 --clean 参数，先清理
if [ "$1" = "--clean" ]; then
    cleanup
    echo "清理完成，如需构建请重新运行脚本"
    exit 0
fi

# 运行主函数
main
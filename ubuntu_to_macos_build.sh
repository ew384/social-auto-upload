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

# 创建兼容的 main.js
create_main_js() {
    echo "🔧 创建 main.js..."
    mkdir -p sau_frontend/electron
    
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
    
    echo "✅ main.js 已创建"
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
    
    // 确保不设置 type: 'module'，保持 CommonJS 兼容性
    delete pkg.type;
    
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
    create_main_js
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
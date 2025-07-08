#!/bin/bash

# SAU 优化构建系统 - 从源头控制打包大小

set -e

echo "🚀 SAU 优化构建系统启动..."

# 分析当前项目依赖大小
analyze_dependencies() {
    echo "🔍 分析项目依赖大小..."
    
    echo "=== Python 虚拟环境分析 ==="
    if [ -d ".env" ]; then
        echo "虚拟环境总大小: $(du -sh .env | cut -f1)"
        echo "主要 Python 包:"
        source .env/bin/activate
        pip list --format=freeze | while read pkg; do
            pkg_name=$(echo $pkg | cut -d'=' -f1)
            pkg_path=$(python -c "import $pkg_name; print($pkg_name.__file__)" 2>/dev/null | xargs dirname 2>/dev/null || echo "unknown")
            if [ "$pkg_path" != "unknown" ] && [ -d "$pkg_path" ]; then
                size=$(du -sh "$pkg_path" 2>/dev/null | cut -f1 || echo "0")
                echo "  $pkg_name: $size"
            fi
        done | sort -hr | head -15
    fi
    
    echo ""
    echo "=== Node.js 依赖分析 ==="
    if [ -d "sau_frontend/node_modules" ]; then
        echo "node_modules 总大小: $(du -sh sau_frontend/node_modules | cut -f1)"
        echo "最大的 Node.js 包:"
        find sau_frontend/node_modules -maxdepth 1 -type d -exec du -sh {} + 2>/dev/null | sort -hr | head -15
    fi
    
    echo ""
    echo "=== 项目文件分析 ==="
    echo "videoFile 目录: $(du -sh videoFile 2>/dev/null | cut -f1 || echo '0')"
    echo "cookiesFile 目录: $(du -sh cookiesFile 2>/dev/null | cut -f1 || echo '0')"
    echo "logs 目录: $(du -sh logs 2>/dev/null | cut -f1 || echo '0')"
    echo "db 目录: $(du -sh db 2>/dev/null | cut -f1 || echo '0')"
}

# 创建精确的 PyInstaller 配置
create_precise_pyinstaller_spec() {
    echo "📝 创建精确的 PyInstaller 配置..."
    
    cat > sau_backend_precise.spec << 'PYSPEC'
# -*- mode: python ; coding: utf-8 -*-
import sys
import os

# 精确控制导入
hidden_imports = [
    # Flask 核心
    'flask', 'flask_cors', 'werkzeug', 'jinja2', 'markupsafe', 'itsdangerous', 'click',
    
    # 网络请求
    'requests', 'urllib3', 'certifi', 'chardet', 'idna',
    
    # 数据库
    'sqlite3',
    
    # 标准库
    'json', 'threading', 'time', 'datetime', 'uuid', 'hashlib', 'base64',
    'logging', 'traceback', 'functools', 'os', 'sys', 'pathlib',
    
    # Selenium 相关
    'selenium', 'selenium.webdriver', 'selenium.webdriver.chrome', 'selenium.webdriver.common',
    
    # 项目模块
    'conf', 'utils.base_social_media', 'utils.constant', 'utils.files_times',
    'utils.log', 'utils.network', 'myUtils.auth', 'myUtils.login', 'myUtils.postVideo',
    
    # 上传器模块
    'uploader.douyin_uploader.main', 'uploader.tencent_uploader.main',
    'uploader.ks_uploader.main', 'uploader.tk_uploader.main_chrome',
    'uploader.xhs_uploader.main', 'uploader.baijiahao_uploader.main',
    'uploader.bilibili_uploader.main', 'uploader.xiaohongshu_uploader.main',
]

# 严格排除大型不必要的库
excludes = [
    # GUI 库
    'tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'wx',
    
    # 科学计算库
    'numpy', 'pandas', 'scipy', 'matplotlib', 'seaborn', 'plotly',
    'sklearn', 'tensorflow', 'torch', 'cv2', 'PIL.ImageTk',
    
    # 开发工具
    'jupyter', 'ipython', 'notebook', 'pytest', 'setuptools', 'pip',
    'wheel', 'twine', 'sphinx', 'flake8', 'black', 'mypy',
    
    # 测试框架
    'unittest', 'doctest', 'test', 'tests',
    
    # 不需要的标准库模块
    'pdb', 'profile', 'pstats', 'cProfile', 'trace', 'tabnanny',
    'py_compile', 'compileall', 'dis', 'pickletools',
    
    # 网络服务器（我们只需要 Flask 的轻量级服务器）
    'tornado', 'twisted', 'django', 'fastapi', 'uvicorn', 'gunicorn',
    
    # 图像处理（除非真的需要）
    'PIL.ImageQt', 'PIL.ImageTk', 'PIL.ImageWin',
    
    # 加密库（除非必需）
    'cryptography', 'OpenSSL', 'paramiko',
    
    # Windows 特定
    'win32api', 'win32gui', 'win32con', 'pywin32',
]

a = Analysis(
    ['sau_backend.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # 只包含必要的配置和示例文件
        ('conf.py', '.'),
        ('db/createTable.py', 'db'),
        ('utils', 'utils'),
        ('myUtils', 'myUtils'),
        ('uploader', 'uploader'),
        ('examples', 'examples'),
        # 不包含用户数据目录
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

# 过滤二进制文件 - 移除不必要的 DLL/SO 文件
def filter_binaries(binaries):
    excluded_patterns = [
        'tcl', 'tk', '_tkinter', 'numpy', 'scipy', 'matplotlib', 'qt',
        'opencv', 'cv2', 'torch', 'tensorflow', 'sklearn', 'pandas',
        'openblas', 'mkl', 'intel', 'cuda', 'cudnn'
    ]
    
    filtered = []
    for binary in binaries:
        name = binary[0].lower()
        if not any(pattern in name for pattern in excluded_patterns):
            filtered.append(binary)
        else:
            print(f"Excluding binary: {binary[0]}")
    
    return filtered

a.binaries = filter_binaries(a.binaries)

# 过滤数据文件
def filter_datas(datas):
    excluded_patterns = [
        'tcl', 'tk', 'tkinter', 'matplotlib', 'numpy', 'scipy',
        'jupyter', 'ipython', 'test', 'tests', '__pycache__'
    ]
    
    filtered = []
    for data in datas:
        name = data[0].lower()
        if not any(pattern in name for pattern in excluded_patterns):
            filtered.append(data)
        else:
            print(f"Excluding data: {data[0]}")
    
    return filtered

a.datas = filter_datas(a.datas)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='sau_backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # 去除调试信息
    upx=True,    # 启用 UPX 压缩
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
PYSPEC

    echo "✅ 精确 PyInstaller 配置已创建"
}

# 创建严格的 .electronignore
create_strict_electronignore() {
    echo "📝 创建严格的 .electronignore..."
    
    cat > sau_frontend/.electronignore << 'ELECTRONIGNORE'
# === 源代码文件 ===
src/
public/
*.config.js
*.config.ts
*.config.mjs
vite.config.*
vue.config.*
webpack.config.*
rollup.config.*
.env*
README.md
*.md

# === Node.js 相关 ===
node_modules/
package-lock.json
yarn.lock
.npm/
.yarn/
pnpm-lock.yaml

# === 构建和缓存文件 ===
dist-electron/
build/
.next/
.nuxt/
.vite/
.cache/
.temp/
.tmp/

# === 开发工具 ===
.vscode/
.idea/
.vs/
*.log
logs/
.eslintrc*
.prettierrc*
.editorconfig
.gitignore
.gitattributes

# === 版本控制 ===
.git/
.svn/
.hg/

# === 测试文件 ===
test/
tests/
spec/
__tests__/
*.test.*
*.spec.*
coverage/
.nyc_output/

# === 文档 ===
docs/
documentation/

# === 临时文件 ===
*.tmp
*.temp
.DS_Store
Thumbs.db
*.swp
*.swo
*~

# === Python 相关（如果有混合项目）===
*.pyc
__pycache__/
.pytest_cache/
*.py

# === 备份文件 ===
*.backup
*.bak
*.orig

# === 用户数据（重要：不打包用户数据）===
uploads/
downloads/
user-data/
cookies/
sessions/

# === 大文件类型 ===
*.mp4
*.avi
*.mov
*.mkv
*.wmv
*.flv
*.webm
*.m4v
*.iso
*.dmg
*.zip
*.tar.gz
*.7z
*.rar
ELECTRONIGNORE

    echo "✅ 严格的 .electronignore 已创建"
}

# 创建最小化的 Electron main.js
create_minimal_main() {
    echo "⚡ 创建最小化的 main.js..."
    
    mkdir -p sau_frontend/electron
    
    cat > sau_frontend/electron/main.js << 'MAINJS'
const { app, BrowserWindow } = require('electron')
const path = require('path')
const { spawn } = require('child_process')

let mainWindow
let backendProcess

// 简化的端口检查
function isPortInUse(port) {
  return new Promise((resolve) => {
    const net = require('net')
    const server = net.createServer()
    
    server.once('error', () => resolve(true))
    server.once('listening', () => {
      server.close()
      resolve(false)
    })
    
    server.listen(port)
  })
}

// 等待后端启动
async function waitForBackend(maxWait = 30000) {
  const startTime = Date.now()
  
  while (Date.now() - startTime < maxWait) {
    if (await isPortInUse(5409)) {
      return true
    }
    await new Promise(resolve => setTimeout(resolve, 1000))
  }
  
  return false
}

// 创建窗口
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    show: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  })

  // 开发环境
  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.show()
    return
  }

  // 生产环境 - 等待后端启动
  waitForBackend().then(backendReady => {
    if (backendReady) {
      mainWindow.loadURL('http://localhost:5409')
    } else {
      // 后端启动失败，加载静态文件
      mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
    }
    mainWindow.show()
  })
}

// 启动 Python 后端
function startBackend() {
  if (process.env.NODE_ENV === 'development') return

  const backendPath = path.join(process.resourcesPath, 'backend')
  const execPath = path.join(backendPath, 'sau_backend')
  
  try {
    backendProcess = spawn(execPath, [], {
      cwd: backendPath,
      stdio: 'pipe'
    })
    
    backendProcess.on('error', console.error)
  } catch (error) {
    console.error('启动后端失败:', error)
  }
}

// 停止后端
function stopBackend() {
  if (backendProcess) {
    backendProcess.kill()
    backendProcess = null
  }
}

// 应用事件
app.whenReady().then(() => {
  startBackend()
  createWindow()
})

app.on('window-all-closed', () => {
  stopBackend()
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', stopBackend)
MAINJS

    echo "✅ 最小化 main.js 已创建"
}

# 执行优化构建
execute_optimized_build() {
    echo "🔨 执行优化构建..."
    
    # 1. 清理旧的构建文件
    echo "清理旧构建文件..."
    rm -rf build/ dist/ backend-dist/ *.spec
    rm -rf sau_frontend/dist/ sau_frontend/dist-electron/ sau_frontend/resources/
    
    # 2. 构建优化的后端
    echo "构建优化后端..."
    source .env/bin/activate
    pyinstaller --clean sau_backend_precise.spec
    
    # 检查后端大小
    backend_size=$(du -sh dist/sau_backend 2>/dev/null | cut -f1 || echo "Unknown")
    echo "优化后端大小: $backend_size"
    
    # 3. 创建精简的后端分发
    mkdir -p backend-dist
    cp dist/sau_backend backend-dist/
    cp conf.py backend-dist/ 2>/dev/null || true
    
    # 创建空的数据目录（不包含用户数据）
    mkdir -p backend-dist/{db,cookiesFile,videoFile,logs}
    cp db/createTable.py backend-dist/db/ 2>/dev/null || true
    echo "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY);" | sqlite3 backend-dist/db/database.db
    
    backend_dist_size=$(du -sh backend-dist 2>/dev/null | cut -f1 || echo "Unknown")
    echo "后端分发包大小: $backend_dist_size"
    
    # 4. 优化前端构建
    echo "构建优化前端..."
    cd sau_frontend
    
    # 构建前端
    if command -v yarn &> /dev/null; then
        yarn build
    else
        npm run build
    fi
    
    frontend_size=$(du -sh dist 2>/dev/null | cut -f1 || echo "Unknown")
    echo "前端构建大小: $frontend_size"
    
    cd ..
    
    # 5. 准备 Electron 资源
    echo "准备 Electron 资源..."
    mkdir -p sau_frontend/resources/backend
    cp -r backend-dist/* sau_frontend/resources/backend/
    
    resources_size=$(du -sh sau_frontend/resources 2>/dev/null | cut -f1 || echo "Unknown")
    echo "Electron 资源大小: $resources_size"
    
    # 6. 构建 Electron（目录模式）
    echo "构建 Electron 应用..."
    cd sau_frontend
    
    # 更新 package.json 为 Electron 构建
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
        files: ['dist/**/*', 'electron/**/*', 'resources/**/*'],
        extraResources: [{ from: 'resources/backend', to: 'backend' }],
        mac: { target: [{ target: 'dir', arch: ['x64'] }] },
        compression: 'maximum',
        removePackageScripts: true,
        electronVersion: '28.0.0'
    };
    
    fs.writeFileSync('package.json', JSON.stringify(pkg, null, 2));
    "
    
    # 构建 Electron
    export CSC_IDENTITY_AUTO_DISCOVERY=false
    npx electron-builder --mac --x64 --dir --publish=never
    
    cd ..
    
    # 7. 创建最终分发包
    echo "创建最终分发包..."
    mkdir -p final-dist-optimized
    
    if [ -d "sau_frontend/dist-electron/mac" ]; then
        APP_FILE=$(find sau_frontend/dist-electron/mac -name "*.app" -type d | head -1)
        
        if [ -n "$APP_FILE" ]; then
            cp -r "$APP_FILE" final-dist-optimized/
            
            cd final-dist-optimized
            APP_NAME=$(basename "$APP_FILE" .app)
            tar -czf "${APP_NAME}-优化版.tar.gz" "$(basename "$APP_FILE")"
            cd ..
            
            # 显示最终结果
            echo ""
            echo "🎉 优化构建完成！"
            echo "📦 最终应用: final-dist-optimized/"
            echo "📏 应用大小: $(du -sh final-dist-optimized/SAU自媒体自动化运营系统.app 2>/dev/null | cut -f1 || echo 'Unknown')"
            echo "📦 压缩包: final-dist-optimized/${APP_NAME}-优化版.tar.gz"
            echo "📏 压缩包大小: $(du -sh final-dist-optimized/${APP_NAME}-优化版.tar.gz 2>/dev/null | cut -f1 || echo 'Unknown')"
            
            # 分析应用内容
            echo ""
            echo "=== 优化后的应用内容分析 ==="
            echo "后端: $(du -sh final-dist-optimized/SAU自媒体自动化运营系统.app/Contents/Resources/backend 2>/dev/null | cut -f1 || echo 'Unknown')"
            echo "前端: $(du -sh final-dist-optimized/SAU自媒体自动化运营系统.app/Contents/Resources/app.asar 2>/dev/null | cut -f1 || echo 'Unknown')"
            echo "Electron 框架: $(du -sh final-dist-optimized/SAU自媒体自动化运营系统.app/Contents/Frameworks 2>/dev/null | cut -f1 || echo 'Unknown')"
        fi
    fi
}

# 主函数
main() {
    echo "======================================"
    echo "  SAU 优化构建系统"
    echo "  从源头控制打包大小"
    echo "======================================"
    
    if [ ! -f "sau_backend.py" ]; then
        echo "❌ 请在项目根目录运行"
        exit 1
    fi
    
    analyze_dependencies
    echo ""
    read -p "是否继续执行优化构建？(y/N) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        create_precise_pyinstaller_spec
        create_strict_electronignore
        create_minimal_main
        execute_optimized_build
        
        echo ""
        echo "🎉 优化构建系统执行完成！"
        echo "📊 对比原始构建结果，查看优化效果"
    else
        echo "👋 取消执行"
    fi
}

main "$@"

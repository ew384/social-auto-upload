#!/bin/bash

# SAU 自媒体自动化运营系统 - 完整自动化构建脚本
# 适用于代码修改后的重新构建

set -e

# 配置变量
PROJECT_NAME="SAU自媒体自动化运营系统"
BUILD_VERSION=$(date +"%Y%m%d_%H%M%S")
PYTHON_VERSION="3.10"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查环境
check_environment() {
    log_info "检查构建环境..."
    
    # 检查是否在项目根目录
    if [ ! -f "sau_backend.py" ] || [ ! -d "sau_frontend" ]; then
        log_error "请在项目根目录运行此脚本"
        exit 1
    fi
    
    # 检查 Python 虚拟环境
    if [ ! -d ".env" ]; then
        log_error "未找到 Python 虚拟环境 (.env)"
        exit 1
    fi
    
    # 检查配置文件
    if [ ! -f "conf.py" ]; then
        log_warning "未找到 conf.py 配置文件"
        if [ -f "conf.example.py" ]; then
            log_info "复制 conf.example.py 为 conf.py"
            cp conf.example.py conf.py
        else
            log_error "请确保有 conf.py 配置文件"
            exit 1
        fi
    fi
    
    # 检查 Node.js
    if ! command -v node &> /dev/null; then
        log_error "Node.js 未安装"
        exit 1
    fi
    
    log_success "环境检查通过"
}

# 清理旧的构建文件
clean_build_files() {
    log_info "清理旧的构建文件..."
    
    # Python 构建文件
    rm -rf build/ dist/ *.spec
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    # 后端分发目录
    rm -rf backend-dist/
    
    # 前端构建文件
    rm -rf sau_frontend/dist/ sau_frontend/dist-electron/ sau_frontend/resources/
    
    # 最终分发文件
    rm -rf final-dist-optimized/
    
    log_success "构建文件清理完成"
}

# 清理用户数据（可选）
clean_user_data() {
    if [ "$1" = "--clean-data" ]; then
        log_info "清理用户数据..."
        
        # 清理大型视频文件，保留 demo
        find videoFile/ -name "*.mov" -size +10M -not -name "demo.*" -delete 2>/dev/null || true
        find videoFile/ -name "*.mp4" -size +10M -not -name "demo.*" -delete 2>/dev/null || true
        find videoFile/ -name "*output*" -delete 2>/dev/null || true
        
        # 清理日志文件
        find logs/ -name "*.log" -size +1M -delete 2>/dev/null || true
        
        # 清理临时文件
        find . -name "*.tmp" -delete 2>/dev/null || true
        find . -name "*.temp" -delete 2>/dev/null || true
        find . -name ".DS_Store" -delete 2>/dev/null || true
        
        log_success "用户数据清理完成"
    fi
}

# 创建 PyInstaller 配置
create_pyinstaller_spec() {
    log_info "创建 PyInstaller 配置..."
    
    cat > sau_backend_optimized.spec << 'EOF'
# -*- mode: python ; coding: utf-8 -*-

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
    'conf', 
    'utils.base_social_media', 'utils.constant', 'utils.files_times', 'utils.log', 'utils.network',
    'myUtils.auth', 'myUtils.login', 'myUtils.postVideo',
    
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
    
    # 网络服务器
    'tornado', 'twisted', 'django', 'fastapi', 'uvicorn', 'gunicorn',
    
    # 图像处理
    'PIL.ImageQt', 'PIL.ImageTk', 'PIL.ImageWin',
    
    # 加密库
    'cryptography', 'OpenSSL', 'paramiko',
    
    # Windows 特定
    'win32api', 'win32gui', 'win32con', 'pywin32',
]

a = Analysis(
    ['sau_backend.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('conf.py', '.'),
        ('db/createTable.py', 'db'),
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

# 过滤二进制文件
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
    return filtered

a.datas = filter_datas(a.datas)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='sau_backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
)
EOF

    log_success "PyInstaller 配置创建完成"
}

# 构建 Python 后端
build_backend() {
    log_info "构建 Python 后端..."
    
    # 激活虚拟环境
    source .env/bin/activate
    
    # 检查 PyInstaller
    if ! pip show pyinstaller &> /dev/null; then
        log_info "安装 PyInstaller..."
        pip install pyinstaller
    fi
    
    # 构建
    pyinstaller --clean sau_backend_optimized.spec
    
    if [ ! -f "dist/sau_backend" ]; then
        log_error "后端构建失败"
        exit 1
    fi
    
    backend_size=$(du -sh dist/sau_backend | cut -f1)
    log_success "后端构建完成 - 大小: $backend_size"
    
    # 创建后端分发包
    mkdir -p backend-dist
    cp dist/sau_backend backend-dist/
    cp conf.py backend-dist/ 2>/dev/null || true
    
    # 创建数据目录
    mkdir -p backend-dist/{db,cookiesFile,videoFile,logs}
    cp db/createTable.py backend-dist/db/ 2>/dev/null || true
    
    # 创建数据库
    if command -v sqlite3 &> /dev/null; then
        echo "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY);" | sqlite3 backend-dist/db/database.db
    fi
    
    backend_dist_size=$(du -sh backend-dist | cut -f1)
    log_success "后端分发包创建完成 - 大小: $backend_dist_size"
}

# 创建前端优化配置
create_frontend_configs() {
    log_info "创建前端优化配置..."
    
    # 创建 .electronignore
    cat > sau_frontend/.electronignore << 'EOF'
# 源代码文件
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

# Node.js 相关
node_modules/
package-lock.json
yarn.lock
.npm/
.yarn/
pnpm-lock.yaml

# 构建和缓存文件
dist-electron/
build/
.next/
.nuxt/
.vite/
.cache/
.temp/
.tmp/

# 开发工具
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

# 版本控制
.git/
.svn/
.hg/

# 测试文件
test/
tests/
spec/
__tests__/
*.test.*
*.spec.*
coverage/
.nyc_output/

# 文档
docs/
documentation/

# 临时文件
*.tmp
*.temp
.DS_Store
Thumbs.db
*.swp
*.swo
*~

# Python 相关
*.pyc
__pycache__/
.pytest_cache/
*.py

# 备份文件
*.backup
*.bak
*.orig

# 用户数据
uploads/
downloads/
user-data/
cookies/
sessions/

# 大文件类型
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
EOF

    # 创建 Electron main.js
    mkdir -p sau_frontend/electron
    cat > sau_frontend/electron/main.js << 'EOF'
const { app, BrowserWindow } = require('electron')
const path = require('path')
const { spawn } = require('child_process')

let mainWindow
let backendProcess

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

  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.show()
    return
  }

  waitForBackend().then(backendReady => {
    if (backendReady) {
      mainWindow.loadURL('http://localhost:5409')
    } else {
      mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
    }
    mainWindow.show()
  })
}

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

function stopBackend() {
  if (backendProcess) {
    backendProcess.kill()
    backendProcess = null
  }
}

app.whenReady().then(() => {
  startBackend()
  createWindow()
})

app.on('window-all-closed', () => {
  stopBackend()
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', stopBackend)
EOF

    log_success "前端配置文件创建完成"
}

# 构建前端
build_frontend() {
    log_info "构建前端..."
    
    cd sau_frontend
    
    # 构建前端
    if command -v yarn &> /dev/null; then
        yarn build
    else
        npm run build
    fi
    
    if [ ! -d "dist" ]; then
        log_error "前端构建失败"
        exit 1
    fi
    
    frontend_size=$(du -sh dist | cut -f1)
    log_success "前端构建完成 - 大小: $frontend_size"
    
    cd ..
}

# 准备 Electron 资源
prepare_electron_resources() {
    log_info "准备 Electron 资源..."
    
    mkdir -p sau_frontend/resources/backend
    cp -r backend-dist/* sau_frontend/resources/backend/
    
    resources_size=$(du -sh sau_frontend/resources | cut -f1)
    log_success "Electron 资源准备完成 - 大小: $resources_size"
}

# 构建 Electron 应用
build_electron() {
    log_info "构建 Electron 应用..."
    
    cd sau_frontend
    
    # 更新 package.json
    node -e "
    const fs = require('fs');
    const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
    
    pkg.main = 'electron/main.js';
    pkg.homepage = './';
    delete pkg.type;
    
    pkg.build = {
        appId: 'com.sau.media.automation',
        productName: '${PROJECT_NAME}',
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
    
    # 确保依赖已安装
    if ! npm list electron &> /dev/null; then
        log_info "安装 Electron..."
        npm install --save-dev electron@28.0.0
    fi
    
    if ! npm list electron-builder &> /dev/null; then
        log_info "安装 electron-builder..."
        npm install --save-dev electron-builder@24.6.4
    fi
    
    # 设置环境变量
    export CSC_IDENTITY_AUTO_DISCOVERY=false
    export ELECTRON_BUILDER_ALLOW_UNRESOLVED_DEPENDENCIES=true
    
    # 构建
    npx electron-builder --mac --x64 --dir --publish=never
    
    cd ..
    
    # 检查构建结果
    APP_FILE=$(find sau_frontend/dist-electron -name "*.app" -type d | head -1)
    
    if [ -z "$APP_FILE" ]; then
        log_error "Electron 构建失败"
        exit 1
    fi
    
    app_size=$(du -sh "$APP_FILE" | cut -f1)
    log_success "Electron 应用构建完成 - 大小: $app_size"
}

# 创建最终分发包
create_distribution() {
    log_info "创建最终分发包..."
    
    mkdir -p final-dist-optimized
    
    APP_FILE=$(find sau_frontend/dist-electron -name "*.app" -type d | head -1)
    cp -r "$APP_FILE" final-dist-optimized/
    
    cd final-dist-optimized
    APP_NAME=$(basename "$APP_FILE" .app)
    APP_DIR=$(basename "$APP_FILE")
    
    # 创建版本化的压缩包名称
    PACKAGE_NAME="${APP_NAME}-v${BUILD_VERSION}.tar.gz"
    tar -czf "$PACKAGE_NAME" "$APP_DIR"
    
    # 创建最新版本的符号链接
    ln -sf "$PACKAGE_NAME" "${APP_NAME}-latest.tar.gz"
    
    cd ..
    
    # 显示构建结果
    app_size=$(du -sh "final-dist-optimized/$APP_DIR" | cut -f1)
    package_size=$(du -sh "final-dist-optimized/$PACKAGE_NAME" | cut -f1)
    
    log_success "分发包创建完成"
    echo ""
    echo "📊 构建结果:"
    echo "  应用大小: $app_size"
    echo "  压缩包: $package_size"
    echo "  位置: $(pwd)/final-dist-optimized/$PACKAGE_NAME"
}

# 生成构建报告
generate_report() {
    log_info "生成构建报告..."
    
    REPORT_FILE="build-report-${BUILD_VERSION}.txt"
    
    cat > "$REPORT_FILE" << EOF
SAU 自媒体自动化运营系统 - 构建报告
==========================================

构建时间: $(date)
构建版本: $BUILD_VERSION
构建平台: $(uname -s) $(uname -m)

组件大小:
- Python 后端: $(du -sh backend-dist 2>/dev/null | cut -f1 || echo "未知")
- 前端资源: $(du -sh sau_frontend/dist 2>/dev/null | cut -f1 || echo "未知")
- Electron 资源: $(du -sh sau_frontend/resources 2>/dev/null | cut -f1 || echo "未知")
- 最终应用: $(du -sh final-dist-optimized/*.app 2>/dev/null | cut -f1 || echo "未知")
- 压缩包: $(du -sh final-dist-optimized/*-v${BUILD_VERSION}.tar.gz 2>/dev/null | cut -f1 || echo "未知")

安装说明:
1. 将压缩包传输到 macOS 设备
2. 解压: tar -xzf ${PROJECT_NAME}-v${BUILD_VERSION}.tar.gz
3. 将 .app 拖拽到 Applications 文件夹
4. 首次运行前安装依赖: pip3 install playwright && playwright install chromium
5. 右键应用选择"打开"（绕过安全检查）

技术信息:
- Python: $(python3 --version 2>/dev/null || echo "未知")
- Node.js: $(node --version 2>/dev/null || echo "未知")
- Electron: $(cd sau_frontend && npm list electron 2>/dev/null | grep electron || echo "未知")
EOF

    log_success "构建报告已保存: $REPORT_FILE"
}

# 清理构建文件（可选）
cleanup_build_artifacts() {
    if [ "$1" = "--cleanup" ]; then
        log_info "清理构建文件..."
        
        rm -rf build/ dist/ *.spec backend-dist/
        rm -rf sau_frontend/dist/ sau_frontend/dist-electron/ sau_frontend/resources/
        
        log_success "构建文件清理完成"
    fi
}

# 显示使用说明
show_usage() {
    echo "SAU 自动化构建脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --clean-data    清理用户数据（视频文件、日志等）"
    echo "  --cleanup       构建完成后清理中间文件"
    echo "  --help          显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                      # 标准构建"
    echo "  $0 --clean-data         # 清理数据后构建"
    echo "  $0 --cleanup           # 构建后清理中间文件"
    echo "  $0 --clean-data --cleanup  # 完整清理构建"
}

# 主函数
main() {
    echo "======================================"
    echo "  SAU 自媒体自动化运营系统"
    echo "      完整自动化构建脚本"
    echo "======================================"
    echo ""
    
    # 处理参数
    CLEAN_DATA=""
    CLEANUP=""
    
    for arg in "$@"; do
        case $arg in
            --clean-data)
                CLEAN_DATA="--clean-data"
                ;;
            --cleanup)
                CLEANUP="--cleanup"
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                log_error "未知参数: $arg"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # 执行构建流程
    check_environment
    clean_build_files
    clean_user_data "$CLEAN_DATA"
    create_pyinstaller_spec
    build_backend
    create_frontend_configs
    build_frontend
    prepare_electron_resources
    build_electron
    create_distribution
    generate_report
    cleanup_build_artifacts "$CLEANUP"
    
    echo ""
    log_success "🎉 构建完成！"
    echo ""
    echo "📁 构建产物:"
    echo "  应用: final-dist-optimized/${PROJECT_NAME}.app"
    echo "  压缩包: final-dist-optimized/${PROJECT_NAME}-v${BUILD_VERSION}.tar.gz"
    echo "  最新版: final-dist-optimized/${PROJECT_NAME}-latest.tar.gz"
    echo "  报告: build-report-${BUILD_VERSION}.txt"
    echo ""
    echo "🚀 现在可以部署到 macOS 设备了！"
}

# 错误处理
trap 'log_error "构建过程中发生错误，在第 $LINENO 行"; exit 1' ERR

# 运行主函数
main "$@"

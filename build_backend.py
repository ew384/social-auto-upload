#!/usr/bin/env python3
"""
SAU 后端打包脚本 - 支持跨平台构建
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

def ensure_directories():
    """确保必要的目录存在"""
    dirs = ['db', 'cookiesFile', 'videoFile', 'logs']
    for dir_name in dirs:
        os.makedirs(dir_name, exist_ok=True)
        print(f"✅ 确保目录存在: {dir_name}")

def init_database():
    """初始化数据库"""
    db_path = Path('db/database.db')
    if not db_path.exists():
        print("🗄️ 初始化数据库...")
        try:
            subprocess.run([sys.executable, 'db/createTable.py'], check=True)
            print("✅ 数据库初始化成功")
        except subprocess.CalledProcessError as e:
            print(f"❌ 数据库初始化失败: {e}")
            return False
    else:
        print("✅ 数据库已存在")
    return True

def install_pyinstaller():
    """安装 PyInstaller"""
    try:
        import PyInstaller
        print("✅ PyInstaller 已安装")
        return True
    except ImportError:
        print("📦 正在安装 PyInstaller...")
        try:
            # 优先使用 uv pip
            if shutil.which('uv'):
                print("使用 uv pip 安装...")
                subprocess.check_call(['uv', 'pip', 'install', 'pyinstaller'])
            else:
                print("使用 pip 安装...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            return True
        except subprocess.CalledProcessError:
            print("❌ PyInstaller 安装失败")
            return False

def create_spec_file():
    """创建 PyInstaller 规格文件"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-
import sys
import os

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath('sau_backend.py'))
sys.path.insert(0, current_dir)

block_cipher = None

a = Analysis(
    ['sau_backend.py'],
    pathex=[current_dir],
    binaries=[],
    datas=[
        ('db', 'db'),
        ('cookiesFile', 'cookiesFile'),
        ('videoFile', 'videoFile'),
        ('uploader', 'uploader'),
        ('utils', 'utils'),
        ('myUtils', 'myUtils'),
        ('examples', 'examples'),
        ('conf.py', '.'),
    ],
    hiddenimports=[
        'PIL._tkinter_finder',
        'pkg_resources.py2_warn',
        'flask',
        'flask_cors',
        'selenium',
        'undetected_chromedriver',
        'requests',
        'sqlite3',
        'asyncio',
        'pathlib',
        'playwright',
        'playwright.sync_api',
        'playwright.async_api',
        'conf',
        'uploader.douyin_uploader.main',
        'uploader.tencent_uploader.main',
        'uploader.ks_uploader.main',
        'uploader.tk_uploader.main_chrome',
        'uploader.xhs_uploader.main',
        'uploader.baijiahao_uploader.main',
        'uploader.bilibili_uploader.main',
        'uploader.xiaohongshu_uploader.main',
        'utils.base_social_media',
        'utils.constant',
        'utils.files_times',
        'utils.log',
        'utils.network',
        'myUtils.auth',
        'myUtils.login',
        'myUtils.postVideo',
        'werkzeug',
        'werkzeug.security',
        'werkzeug.serving',
        'markupsafe',
        'itsdangerous',
        'click',
        'json',
        'threading',
        'time',
        'datetime',
        'uuid',
        'hashlib',
        'base64',
        'logging',
        'traceback',
        'functools',
        'email.mime.text',
        'email.mime.multipart',
        'smtplib',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'PIL.ImageTk',
        'PIL.ImageWin',
        'PIL._imagingft',
        'setuptools',
        'distutils',
        'test',
        'unittest',
        'pdb',
        'doctest',
        'xmlrpc',
        'bdb',
        'pydoc',
        'email.mime.image',
        'email.mime.audio',
        'email.mime.application',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 过滤不必要的模块
a.binaries = [x for x in a.binaries if not x[0].startswith(('tcl', 'tk', '_tkinter'))]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''
    
    with open('sau_backend.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    print("✅ 创建 PyInstaller 规格文件")

def build_backend():
    """构建后端可执行文件"""
    print("🔨 开始构建 Python 后端...")
    
    # 清理之前的构建
    for path in ['build', 'dist', '__pycache__']:
        if os.path.exists(path):
            shutil.rmtree(path)
    
    cmd = [
        'pyinstaller',
        '--clean',
        '--noconfirm',
        'sau_backend.spec'
    ]
    
    try:
        print("执行构建命令:", ' '.join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ Python 后端构建成功")
        
        # 处理构建结果
        exe_file = Path('dist/sau_backend')
        target_dir = Path('backend-dist')
        
        if target_dir.exists():
            shutil.rmtree(target_dir)
        
        target_dir.mkdir(parents=True, exist_ok=True)
        
        if exe_file.exists():
            # 复制可执行文件
            shutil.copy2(exe_file, target_dir / 'sau_backend')
            os.chmod(target_dir / 'sau_backend', 0o755)  # 确保可执行权限
            
            # 复制必要的数据目录
            data_dirs = ['db', 'cookiesFile', 'videoFile', 'logs']
            for data_dir in data_dirs:
                src_dir = Path(data_dir)
                if src_dir.exists():
                    target_data_dir = target_dir / data_dir
                    if target_data_dir.exists():
                        shutil.rmtree(target_data_dir)
                    shutil.copytree(src_dir, target_data_dir)
            
            # 复制配置文件
            if Path('conf.py').exists():
                shutil.copy2('conf.py', target_dir / 'conf.py')
            
            # 创建启动脚本
            create_startup_script(target_dir)
            
            print(f"✅ 后端文件已复制到 {target_dir}")
            return True
        else:
            print("❌ 构建的可执行文件不存在")
            return False
            
    except subprocess.CalledProcessError as e:
        print("❌ Python 后端构建失败:")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False

def create_startup_script(target_dir):
    """创建启动脚本"""
    startup_script = target_dir / 'start_backend.sh'
    
    script_content = '''#!/bin/bash
# SAU 后端启动脚本

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 切换到脚本目录
cd "$SCRIPT_DIR"

# 设置环境变量
export PYTHONPATH="$SCRIPT_DIR"

# 启动后端服务
echo "🚀 启动 SAU 后端服务..."
./sau_backend

echo "后端服务已停止"
'''
    
    with open(startup_script, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    # 设置执行权限
    os.chmod(startup_script, 0o755)
    print("✅ 创建启动脚本")

def copy_playwright_resources():
    """复制 Playwright 相关资源"""
    try:
        import playwright
        playwright_path = Path(playwright.__file__).parent
        
        # 查找 Playwright 驱动程序
        driver_paths = [
            playwright_path / 'driver',
            Path.home() / '.cache' / 'ms-playwright',
            Path('/usr/lib/playwright'),
        ]
        
        target_dir = Path('backend-dist')
        
        for driver_path in driver_paths:
            if driver_path.exists():
                print(f"🌐 找到 Playwright 驱动: {driver_path}")
                target_playwright_dir = target_dir / 'playwright'
                target_playwright_dir.mkdir(exist_ok=True)
                
                # 创建说明文件而不是复制大量驱动文件
                readme_content = f"""# Playwright 浏览器驱动说明

## 安装说明
在目标机器上需要安装 Playwright 浏览器驱动:

```bash
# 安装 Playwright
pip install playwright

# 安装浏览器驱动
playwright install chromium
```

## 原始驱动路径
{driver_path}

## 注意事项
- 确保目标机器有网络连接用于下载浏览器驱动
- Chromium 驱动大约需要 130MB 空间
- 首次运行可能需要一些时间来初始化浏览器
"""
                
                with open(target_playwright_dir / 'README.md', 'w', encoding='utf-8') as f:
                    f.write(readme_content)
                
                print("✅ 创建 Playwright 说明文件")
                break
        else:
            print("⚠️ 未找到 Playwright 驱动程序")
            
    except ImportError:
        print("⚠️ 未安装 Playwright")

def optimize_build():
    """优化构建结果"""
    target_dir = Path('backend-dist')
    
    if not target_dir.exists():
        return
    
    print("🔧 优化构建结果...")
    
    # 移除不必要的文件
    unnecessary_patterns = [
        '*.pyc',
        '__pycache__',
        '*.pyo',
        '*.pyd',
        'test*',
        '*test*',
        'debug*',
        '*.log',
    ]
    
    import glob
    for pattern in unnecessary_patterns:
        for file_path in glob.glob(str(target_dir / '**' / pattern), recursive=True):
            try:
                path_obj = Path(file_path)
                if path_obj.is_file():
                    path_obj.unlink()
                elif path_obj.is_dir():
                    shutil.rmtree(path_obj)
            except Exception as e:
                print(f"⚠️ 清理文件失败 {file_path}: {e}")
    
    print("✅ 构建优化完成")

def check_conf_file():
    """检查配置文件"""
    if not Path('conf.py').exists():
        if Path('conf.example.py').exists():
            print("⚠️ 未找到 conf.py，请复制 conf.example.py 并重命名为 conf.py")
            return False
        else:
            print("⚠️ 未找到配置文件")
            return False
    return True

def check_dependencies():
    """检查必要的依赖"""
    print("🔍 检查 Python 依赖...")
    
    required_modules = [
        'flask',
        'flask_cors',
        'requests',
        'sqlite3',
        'pathlib',
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print(f"❌ 缺少必要依赖: {', '.join(missing_modules)}")
        print("请使用以下命令安装:")
        print(f"pip install {' '.join(missing_modules)}")
        return False
    
    print("✅ Python 依赖检查通过")
    return True

def create_readme():
    """创建部署说明文件"""
    target_dir = Path('backend-dist')
    readme_content = """# SAU 后端部署说明

## 系统要求
- macOS 10.14 或更高版本
- 至少 2GB 可用磁盘空间
- 网络连接 (用于下载浏览器驱动)

## 部署步骤

### 1. 安装 Playwright 浏览器驱动
```bash
# 如果没有 Python，请先安装 Python 3.8+
# 然后安装 Playwright
pip3 install playwright

# 安装浏览器驱动
playwright install chromium
```

### 2. 运行后端服务
```bash
# 方式1: 使用启动脚本
./start_backend.sh

# 方式2: 直接运行
./sau_backend
```

### 3. 验证服务
打开浏览器访问: http://localhost:5409/api/health

## 配置说明

### conf.py 配置文件
确保 `conf.py` 文件包含正确的配置:
- 数据库路径
- 上传文件路径
- 各平台的认证信息

### 数据库
- 数据库文件: `db/database.db`
- Cookie 文件: `cookiesFile/`
- 视频文件: `videoFile/`
- 日志文件: `logs/`

## 常见问题

### Q: 服务无法启动
A: 检查端口 5409 是否被占用，确保有足够的权限

### Q: 浏览器驱动错误
A: 重新安装 Playwright 驱动: `playwright install chromium`

### Q: 上传失败
A: 检查网络连接和各平台的 Cookie 是否有效

## 日志位置
日志文件保存在 `logs/` 目录下，可以查看详细的错误信息。

## 技术支持
如遇问题，请查看日志文件或联系技术支持。
"""
    
    with open(target_dir / 'README.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print("✅ 创建部署说明文件")

def main():
    """主函数"""
    print("🚀 开始打包 SAU Python 后端...")
    
    # 检查当前目录
    if not os.path.exists('sau_backend.py'):
        print("❌ 找不到 sau_backend.py，请在项目根目录运行此脚本")
        sys.exit(1)
    
    # 检查配置文件
    if not check_conf_file():
        print("❌ 请先配置 conf.py 文件")
        sys.exit(1)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 确保目录存在
    ensure_directories()
    
    # 初始化数据库
    if not init_database():
        sys.exit(1)
    
    # 安装依赖
    if not install_pyinstaller():
        sys.exit(1)
    
    # 创建规格文件
    create_spec_file()
    
    # 构建后端
    if build_backend():
        # 复制 Playwright 资源
        copy_playwright_resources()
        
        # 优化构建结果
        optimize_build()
        
        # 创建说明文件
        create_readme()
        
        print("🎉 Python 后端打包完成！")
        print("📁 可执行文件位置: backend-dist/")
        print("📝 部署说明: backend-dist/README.md")
        print("🚀 使用启动脚本: backend-dist/start_backend.sh")
        print("")
        print("⚠️  重要提示:")
        print("   1. 在目标 macOS 设备上需要安装 Playwright 浏览器驱动")
        print("   2. 运行命令: playwright install chromium")
        print("   3. 确保 conf.py 配置正确")
    else:
        print("💥 打包失败")
        sys.exit(1)

if __name__ == '__main__':
    main()
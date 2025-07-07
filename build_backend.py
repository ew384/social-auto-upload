#!/usr/bin/env python3
"""
SAU 后端打包脚本
"""

import os
import sys
import shutil
import subprocess
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
        ('sau_frontend/dist', 'sau_frontend/dist'),
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
        'utils.base_social_media',
        'utils.constant',
        'utils.files_times',
        'utils.log',
        'utils.network',
        'myUtils.auth',
        'myUtils.login',
        'myUtils.postVideo',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

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
    print("✅ 创建 PyInstaller 规格文件（单文件模式）")

def copy_playwright_browsers():
    """复制 Playwright 浏览器到打包目录"""
    try:
        import playwright
        playwright_path = Path(playwright.__file__).parent
        browsers_path = playwright_path / 'driver'
        
        target_browsers_path = Path('dist/sau_backend/_internal/playwright/driver')
        
        if browsers_path.exists():
            print("🌐 复制 Playwright 浏览器...")
            target_browsers_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(browsers_path, target_browsers_path, dirs_exist_ok=True)
            print("✅ Playwright 浏览器复制完成")
        else:
            print("⚠️ 未找到 Playwright 浏览器，请确保已安装")
            
    except ImportError:
        print("⚠️ 未安装 Playwright")

def build_backend():
    """构建后端可执行文件"""
    print("🔨 开始构建 Python 后端...")
    
    cmd = ['pyinstaller', '--clean', 'sau_backend.spec']
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ Python 后端构建成功")
        
        # 单文件模式，可执行文件直接在 dist 目录
        exe_file = Path('dist/sau_backend')
        target_dir = Path('backend-dist')
        
        if target_dir.exists():
            shutil.rmtree(target_dir)
        
        target_dir.mkdir(parents=True, exist_ok=True)
        
        if exe_file.exists():
            # 复制可执行文件
            shutil.copy2(exe_file, target_dir / 'sau_backend')
            
            # 复制必要的数据目录
            for data_dir in ['db', 'cookiesFile', 'videoFile']:
                src_dir = Path(data_dir)
                if src_dir.exists():
                    target_data_dir = target_dir / data_dir
                    if target_data_dir.exists():
                        shutil.rmtree(target_data_dir)
                    shutil.copytree(src_dir, target_data_dir)
            
            print(f"✅ 后端文件已复制到 {target_dir}")
            return True
        else:
            print("❌ 构建的可执行文件不存在")
            return False
            
    except subprocess.CalledProcessError as e:
        print("❌ Python 后端构建失败:")
        print(e.stderr)
        return False

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
        print("🎉 Python 后端打包完成！")
        print("📁 可执行文件位置: backend-dist/")
        print("📝 注意: 请确保已安装 Playwright 浏览器驱动")
    else:
        print("💥 打包失败")
        sys.exit(1)

if __name__ == '__main__':
    main()

# utils/smart_playwright.py
import subprocess
import time
import requests
from pathlib import Path

DEFAULT_USE_MULTI_BROWSER = True
DEFAULT_API_URL = 'http://localhost:3000'

def start_multi_account_browser():
    """启动 multi-account-browser"""
    try:
        multi_browser_path = Path(__file__).parent.parent.parent / "multi-account-browser"
        print("🚀 启动 multi-account-browser...")
        subprocess.Popen(['npm', 'run', 'start'], cwd=multi_browser_path)
        
        for i in range(30):
            try:
                if requests.get(f'{DEFAULT_API_URL}/api/health', timeout=1).status_code == 200:
                    print("✅ multi-account-browser 启动成功")
                    return True
            except:
                pass
            time.sleep(1)
        return False
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return False

def get_playwright_module():
    """获取 Playwright 模块"""
    if not DEFAULT_USE_MULTI_BROWSER:
        from playwright.async_api import async_playwright, Playwright
        return async_playwright, Playwright
    
    # 检查是否已运行
    try:
        if requests.get(f'{DEFAULT_API_URL}/api/health', timeout=1).status_code == 200:
            print("🌟 使用 multi-account-browser 模式")
        else:
            raise Exception("未运行")
    except:
        if not start_multi_account_browser():
            print("⚠️ 回退到传统模式")
            from playwright.async_api import async_playwright, Playwright
            return async_playwright, Playwright
    
    # 使用混合模式
    from utils.hybrid_playwright import HybridAsyncPlaywright
    from playwright.async_api import Playwright
    return HybridAsyncPlaywright, Playwright

# 🔥 这行必须要！模块导入时执行，决定使用哪个版本
async_playwright, Playwright = get_playwright_module()
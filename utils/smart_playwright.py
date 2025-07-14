"""
智能 Playwright 导入 - 默认使用 multi-account-browser
"""

# 默认配置
DEFAULT_USE_MULTI_BROWSER = True
DEFAULT_API_URL = 'http://localhost:3000'

def get_playwright_module():
    """获取 Playwright 模块 - 默认使用 multi-account-browser"""
    
    use_multi = DEFAULT_USE_MULTI_BROWSER
    
    if use_multi:
        try:
            import requests
            response = requests.get(f'{DEFAULT_API_URL}/api/health', timeout=2)
            
            if response.status_code == 200:
                from utils.playwright_compat import async_playwright_compat, Playwright
                print("🌟 使用 multi-account-browser 模式")
                return async_playwright_compat, Playwright  # 返回函数本身，不是协程
            else:
                print("⚠️ multi-account-browser 服务异常，回退到传统模式")
                
        except Exception as e:
            print(f"⚠️ multi-account-browser 连接失败，回退到传统模式: {e}")
    
    # 回退到传统模式
    print("🔧 使用传统 Playwright 模式")
    from playwright.async_api import async_playwright, Playwright
    return async_playwright, Playwright

# 导出 - 注意这里不要调用函数
async_playwright, Playwright = get_playwright_module()
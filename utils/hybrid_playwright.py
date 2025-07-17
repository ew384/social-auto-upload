# utils/hybrid_playwright.py
from playwright.async_api import async_playwright as native_playwright, Playwright
from utils.playwright_compat import AccountTabManager

def HybridAsyncPlaywright():
    """返回混合异步 Playwright 实例"""
    return _HybridAsyncPlaywrightInstance()

class _HybridAsyncPlaywrightInstance:
    """混合异步 Playwright 实例"""
    
    def __init__(self):
        self.native_pw = native_playwright
        self.pw_context = None  # 保存原始的异步上下文管理器
        
    async def __aenter__(self):
        # 🔥 保存原始的异步上下文管理器
        self.pw_context = self.native_pw()
        self.pw_instance = await self.pw_context.__aenter__()
        # 返回包装对象
        return HybridPlaywright(self.pw_instance)
        
    async def __aexit__(self, *args):
        # 🔥 使用原始的异步上下文管理器来退出
        return await self.pw_context.__aexit__(*args)

class HybridPlaywright:
    """包装 Playwright 对象，拦截 chromium 访问"""
    
    def __init__(self, native_playwright):
        self.native_playwright = native_playwright
        # 🔥 创建混合 chromium
        self.chromium = HybridChromium(native_playwright.chromium)
    
    def __getattr__(self, name):
        """其他属性直接代理到原生对象"""
        return getattr(self.native_playwright, name)

class HybridChromium:
    """混合 Chromium：拦截 launch"""
    
    def __init__(self, native_chromium):
        self.native_chromium = native_chromium
        
    async def launch(self, **kwargs):
        """拦截 launch，连接到 multi-account-browser"""
        print("🔄 使用 multi-account-browser 连接")
        browser = await self.native_chromium.connect_over_cdp('http://localhost:9712')
        return HybridBrowser(browser)
    
    def __getattr__(self, name):
        return getattr(self.native_chromium, name)

class HybridBrowser:
    """混合浏览器：处理账号标签页管理"""
    
    def __init__(self, native_browser):
        self.native_browser = native_browser
        self.account_manager = AccountTabManager.get_instance()
        
    async def new_context(self, storage_state=None, **kwargs):
        """账号标签页管理 + 原生 context"""
        if storage_state:
            # 标签页管理（查找/创建/切换）
            await self.account_manager.get_or_create_account_tab(storage_state=str(storage_state))
        
        # 返回原生 context（操作当前活动标签页）
        return await self.native_browser.new_context(**kwargs)
    
    def __getattr__(self, name):
        return getattr(self.native_browser, name)
# utils/playwright_compat.py - 最小化实现
from utils.browser_adapter import MultiAccountBrowserAdapter
from utils.common import get_account_info_from_db

class PlaywrightCompatPage:
    def __init__(self, tab_id: str, adapter: MultiAccountBrowserAdapter):
        self.tab_id = tab_id
        self.adapter = adapter

    async def goto(self, url: str):
        return await self.adapter.navigate_tab(self.tab_id, url)

    async def set_input_files(self, selector: str, files: list):
        return await self.adapter.upload_file(self.tab_id, selector, files[0])

    async def wait_for_url(self, url_pattern: str, timeout: int = 5000):
        script = f"""
        new Promise((resolve) => {{
            const check = () => {{
                if (window.location.href.includes('{url_pattern}')) {{
                    resolve(true);
                }} else {{
                    setTimeout(check, 500);
                }}
            }};
            check();
            setTimeout(() => resolve(false), {timeout});
        }})
        """
        return await self.adapter.execute_script(self.tab_id, script)

class PlaywrightCompatContext:
    def __init__(self, storage_state: str = None):
        self.storage_state = storage_state
        self.adapter = MultiAccountBrowserAdapter()
        self.current_tab_id = None

    async def new_page(self) -> PlaywrightCompatPage:
        if self.storage_state:
            # 获取账号信息用于显示名称
            account_info = get_account_info_from_db(self.storage_state)
            account_name = account_info.get('username', 'unknown') if account_info else 'unknown'
            
            self.current_tab_id = await self.adapter.create_account_tab(
                account_name=f"视频号_{account_name}",
                platform="weixin",
                initial_url="about:blank"  # 不自动导航
            )
            
            # 加载cookies
            await self.adapter.load_cookies(self.current_tab_id, self.storage_state)
        else:
            self.current_tab_id = await self.adapter.create_account_tab(
                account_name="temp",
                platform="weixin", 
                initial_url="about:blank"
            )

        return PlaywrightCompatPage(self.current_tab_id, self.adapter)

    async def storage_state(self, path: str = None):
        if path and self.current_tab_id:
            await self.adapter.save_cookies(self.current_tab_id, path)

    # 🗑️ 删除所有复杂的初始化脚本、CDP连接等逻辑

class PlaywrightCompatBrowser:
    async def new_context(self, storage_state=None, **kwargs):
        return PlaywrightCompatContext(storage_state)

class PlaywrightCompatChromium:
    async def launch(self, **kwargs):
        return PlaywrightCompatBrowser()

class PlaywrightCompatPlaywright:
    def __init__(self):
        self.chromium = PlaywrightCompatChromium()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

def async_playwright_compat():
    return PlaywrightCompatPlaywright()

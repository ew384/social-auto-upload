# utils/playwright_compat.py - 最小化实现
from utils.browser_adapter import MultiAccountBrowserAdapter
from utils.common import get_account_info_from_db

class PlaywrightCompatPage:
    def __init__(self, tab_id: str, adapter: MultiAccountBrowserAdapter):
        self.tab_id = tab_id
        self.adapter = adapter

    @property
    async def url(self) -> str:
        """获取当前页面URL - 兼容 Playwright API"""
        return await self.adapter.get_page_url(self.tab_id)

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

    def get_by_role(self, role: str, name: str = None):
        """兼容 get_by_role 方法"""
        return PlaywrightCompatLocator(self.tab_id, self.adapter, role, name)

    def get_by_text(self, text: str):
        """兼容 get_by_text 方法"""
        return PlaywrightCompatLocator(self.tab_id, self.adapter, "text", text)

    def frame_locator(self, selector: str):
        """兼容 frame_locator 方法"""
        return PlaywrightCompatFrameLocator(self.tab_id, self.adapter, selector)

    def on(self, event: str, handler):
        """兼容事件监听 - 简化实现"""
        print(f"⚠️ 事件监听 '{event}' 在兼容模式下暂不支持")
        pass

    async def pause(self):
        """兼容 pause 方法 - 用于调试"""
        print("🔧 页面暂停，等待用户操作...")
        # 在兼容模式下，可以用一个长时间等待来模拟 pause
        await asyncio.sleep(300)  # 等待5分钟

class PlaywrightCompatLocator:
    """兼容 Playwright Locator"""
    def __init__(self, tab_id: str, adapter: MultiAccountBrowserAdapter, role: str, name: str):
        self.tab_id = tab_id
        self.adapter = adapter
        self.role = role
        self.name = name

    async def get_attribute(self, attr_name: str):
        """获取元素属性"""
        if self.role == "img":
            script = f'''
            (function() {{
                const imgs = document.querySelectorAll('img');
                for (const img of imgs) {{
                    if (img.alt && img.alt.includes('{self.name}')) {{
                        return img.getAttribute('{attr_name}');
                    }}
                }}
                return null;
            }})()
            '''
        else:
            script = f'document.querySelector("[role=\\"{self.role}\\"]").getAttribute("{attr_name}")'
        
        return await self.adapter.execute_script(self.tab_id, script)

    @property
    def first(self):
        """返回第一个匹配的元素"""
        return self

class PlaywrightCompatFrameLocator:
    """兼容 Playwright FrameLocator"""
    def __init__(self, tab_id: str, adapter: MultiAccountBrowserAdapter, selector: str):
        self.tab_id = tab_id
        self.adapter = adapter
        self.selector = selector

    def get_by_role(self, role: str, name: str = None):
        return PlaywrightCompatFrameElement(self.tab_id, self.adapter, self.selector, role, name)

    @property
    def first(self):
        return self

class PlaywrightCompatFrameElement:
    """兼容 Frame 中的元素"""
    def __init__(self, tab_id: str, adapter: MultiAccountBrowserAdapter, frame_selector: str, role: str, name: str):
        self.tab_id = tab_id
        self.adapter = adapter
        self.frame_selector = frame_selector
        self.role = role
        self.name = name

    async def get_attribute(self, attr_name: str):
        """获取 frame 中元素的属性"""
        script = f'''
        (function() {{
            const iframe = document.querySelector('{self.frame_selector}');
            if (iframe && iframe.contentDocument) {{
                const img = iframe.contentDocument.querySelector('img');
                return img ? img.getAttribute('{attr_name}') : null;
            }}
            return null;
        }})()
        '''
        return await self.adapter.execute_script(self.tab_id, script)

    @property
    def first(self):
        return self

class PlaywrightCompatContext:
    def __init__(self, storage_state=None):  # 参数名保持和原生 Playwright 一致
        # 🔥 内部使用不同的属性名避免冲突
        self.storage_state_file = storage_state  # 存储文件路径
        self.adapter = MultiAccountBrowserAdapter()
        self.current_tab_id = None
        self._init_scripts = []

    async def add_init_script(self, script: str = None, path: str = None, **kwargs):
        """添加初始化脚本 - 兼容 Playwright API"""
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    script_content = f.read()
                print(f"📜 加载初始化脚本: {path}")
            except Exception as e:
                print(f"⚠️ 读取脚本文件失败: {path}, {e}")
                return self
        elif script:
            script_content = script
        else:
            print("⚠️ addInitScript: 未提供脚本内容")
            return self
        
        self._init_scripts.append(script_content)
        print(f"✅ 初始化脚本已注册")
        return self

    async def new_page(self) -> 'PlaywrightCompatPage':
        # 🔥 使用 self.storage_state_file 避免和方法名冲突
        if self.storage_state_file:
            account_info = get_account_info_from_db(self.storage_state_file)
            account_name = account_info.get('username', 'unknown') if account_info else 'unknown'
            
            self.current_tab_id = await self.adapter.create_account_tab(
                account_name=f"视频号_{account_name}",
                platform="weixin",
                initial_url="about:blank"
            )
            
            await self.adapter.load_cookies(self.current_tab_id, self.storage_state_file)
        else:
            self.current_tab_id = await self.adapter.create_account_tab(
                account_name="temp",
                platform="weixin", 
                initial_url="about:blank"
            )

        # 应用初始化脚本
        if self._init_scripts:
            for script in self._init_scripts:
                try:
                    await self.adapter.execute_script(self.current_tab_id, script)
                    print(f"✅ 初始化脚本已应用")
                except Exception as e:
                    print(f"⚠️ 初始化脚本应用失败: {e}")

        return PlaywrightCompatPage(self.current_tab_id, self.adapter)

    async def storage_state(self, path: str = None):  # 方法名
        """保存存储状态 - 和原生 Playwright API 兼容"""
        if path and self.current_tab_id:
            await self.adapter.save_cookies(self.current_tab_id, path)

    async def close(self):
        # 🔥 使用 self.storage_state_file
        if self.storage_state_file and self.current_tab_id:
            await self.adapter.save_cookies(self.current_tab_id, self.storage_state_file)

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

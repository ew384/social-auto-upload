# utils/playwright_compat.py
"""
Multi-Account-Browser Playwright 兼容适配器
核心理念：一个浏览器实例 + 多个账号标签页复用，而不是每次创建新的浏览器实例
"""
import sqlite3
import asyncio
import os
from pathlib import Path
from typing import Optional, Any, Dict, List
from utils.browser_adapter import MultiAccountBrowserAdapter


class AccountTabManager:
    """账号标签页管理器 - 核心类"""
    
    _instance = None
    _adapter = None
    _account_tabs = {}  # account_key -> tab_id
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._adapter = MultiAccountBrowserAdapter()
            # 设置数据库路径
            from conf import BASE_DIR
            cls._adapter.set_database_path(str(BASE_DIR / "db" / "database.db"))
        return cls._instance
    
    @classmethod
    def get_instance(cls):
        return cls()
    @property
    def db_path(self):
        """代理到 adapter 的 db_path"""
        return self._adapter.db_path if self._adapter else None
    def generate_account_key(self, storage_state: str) -> str:
        """根据 storage_state 生成账号唯一标识"""
        if not storage_state:
            return "default_account"
        
        # 使用绝对路径作为唯一标识
        return str(Path(storage_state).absolute())

    async def create_temp_blank_tab(self) -> str:
        """创建临时空白标签页"""
        return await self._adapter.create_account_tab("temp", "temp_login", "about:blank")

    def infer_platform_from_storage(self, storage_state: str) -> str:
        """从数据库获取平台类型"""
        if not storage_state:
            return "weixin"  # 默认值
        
        # 从数据库获取正确的平台类型
        account_info = self.get_account_info_from_db(storage_state)
        if account_info and account_info.get('platform_type'):
            platform_type = account_info['platform_type']
            # 根据数据库的 type 字段映射到正确的平台
            platform_map = {1: 'xiaohongshu', 2: 'weixin', 3: 'douyin', 4: 'kuaishou'}
            return platform_map.get(platform_type, 'weixin')
        
        # 如果数据库没有找到，返回默认值
        print(f"⚠️ 数据库中未找到账号信息: {Path(storage_state).name}")
        return "weixin"
        
    def get_account_info_from_db(self, cookie_file: str) -> Optional[Dict[str, Any]]:
        """从数据库获取账号信息"""
        print(f"🐛 调试: self.db_path = {getattr(self, 'db_path', 'NOT_SET')}")
        if not self.db_path:
            return None
            
        try:
            cookie_filename = Path(cookie_file).name
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT userName, type FROM user_info 
                    WHERE filePath = ?
                ''', (cookie_filename,))
                result = cursor.fetchone()
                
                if result:
                    username, platform_type = result
                    platform_map = {1: 'xiaohongshu', 2: 'weixin', 3: 'douyin', 4: 'kuaishou'}
                    return {
                        'username': username,
                        'platform': platform_map.get(platform_type, 'weixin'),
                        'platform_type': platform_type  # 🔥 添加这个字段
                    }
                return None
        except Exception as e:
            print(f"⚠️ 获取账号信息失败: {e}")
            return None
    def get_platform_initial_url(self, platform: str) -> str:
        """获取平台初始URL"""
        platform_urls = {
            'weixin': 'https://channels.weixin.qq.com',
            'douyin': 'https://creator.douyin.com',
            'xiaohongshu': 'https://creator.xiaohongshu.com',
            'kuaishou': 'https://cp.kuaishou.com'
        }
        return platform_urls.get(platform, 'https://channels.weixin.qq.com')
    
    async def get_or_create_account_tab(self, storage_state: str = None) -> str:
        """
        获取或创建账号标签页
        这是核心方法：替代原来的 browser.new_context() + page.new_page()
        """
        account_key = self.generate_account_key(storage_state)
        platform = self.infer_platform_from_storage(storage_state)
        initial_url = self.get_platform_initial_url(platform)
        
        print(f"\n🎯 获取或创建账号标签页:")
        print(f"   账号标识: {account_key}")
        print(f"   平台: {platform}")
        print(f"   Cookie文件: {Path(storage_state).name if storage_state else 'None'}")
        
        # 检查是否已有该账号的标签页
        if account_key in self._account_tabs:
            tab_id = self._account_tabs[account_key]
            print(f"   发现现有标签页: {tab_id}")
            
            # 验证标签页是否仍然有效
            if await self._adapter.is_tab_valid(tab_id):
                print(f"   ✅ 标签页有效，直接复用")
                
                # 切换到该标签页
                await self._adapter.switch_to_tab(tab_id)
                
                # 检查是否需要重新认证
                current_url = await self._adapter.get_page_url(tab_id)
                print(f"   当前URL: {current_url}")
                
                needs_reauth = await self._check_needs_reauth(platform, current_url)
                if needs_reauth and storage_state:
                    print(f"   ⚠️ 需要重新认证")
                    success = await self._handle_reauth(tab_id, platform, storage_state)
                    if success:
                        print(f"   ✅ 重新认证成功")
                    else:
                        print(f"   ❌ 重新认证失败，将创建新标签页")
                        await self._adapter.close_tab(tab_id)
                        del self._account_tabs[account_key]
                        # 递归调用创建新标签页
                        return await self.get_or_create_account_tab(storage_state)
                
                return tab_id
            else:
                print(f"   ⚠️ 标签页已失效，清理记录")
                del self._account_tabs[account_key]
        
        # 创建新的标签页
        print(f"   🆕 创建新标签页")
        tab_id = await self._adapter.get_or_create_account_tab(
            platform=platform,
            cookie_file=storage_state or "",
            initial_url=initial_url
        )
        
        # 保存账号映射
        self._account_tabs[account_key] = tab_id
        print(f"   ✅ 新标签页创建完成: {tab_id}")
        
        return tab_id
    
    async def _check_needs_reauth(self, platform: str, current_url: str) -> bool:
        """检查是否需要重新认证"""
        login_indicators = ['login', 'signin', 'auth', '登录', '扫码']
        return any(indicator in current_url.lower() for indicator in login_indicators)
    
    async def _handle_reauth(self, tab_id: str, platform: str, storage_state: str) -> bool:
        """处理重新认证"""
        try:
            print(f"   🔄 重新加载cookies: {Path(storage_state).name}")
            
            # 重新加载cookies
            await self._adapter.load_cookies(tab_id, storage_state)
            await asyncio.sleep(3)
            
            # 刷新页面
            await self._adapter.refresh_page(tab_id)
            await asyncio.sleep(5)
            
            # 检查认证结果
            current_url = await self._adapter.get_page_url(tab_id)
            needs_auth = await self._check_needs_reauth(platform, current_url)
            
            return not needs_auth
            
        except Exception as e:
            print(f"   ❌ 重新认证失败: {e}")
            return False
    
    async def save_account_state(self, storage_state: str, tab_id: str = None):
        """保存账号状态"""
        if not storage_state:
            return
        
        if not tab_id:
            account_key = self.generate_account_key(storage_state)
            tab_id = self._account_tabs.get(account_key)
        
        if tab_id:
            await self._adapter.save_cookies(tab_id, storage_state)
            print(f"   💾 账号状态已保存: {Path(storage_state).name}")
    
    def get_adapter(self) -> MultiAccountBrowserAdapter:
        """获取底层适配器"""
        return self._adapter
    
    def debug_print_tabs(self):
        """调试：打印当前所有标签页"""
        print(f"\n📊 当前账号标签页映射 ({len(self._account_tabs)} 个):")
        for account_key, tab_id in self._account_tabs.items():
            print(f"   {Path(account_key).name} -> {tab_id}")


# ========================================
# Playwright 兼容层
# ========================================

class PlaywrightCompatPage:
    """兼容 Playwright Page API"""
    
    def __init__(self, tab_id: str, tab_manager: AccountTabManager, storage_state: str = None):
        self.tab_id = tab_id
        self.tab_manager = tab_manager
        self.adapter = tab_manager.get_adapter()
        self.storage_state = storage_state
        self._url = ""
    
    async def goto(self, url: str, **kwargs) -> None:
        """导航到指定URL"""
        print(f"🔗 [{self.tab_id}] 导航到: {url}")
        await self.adapter.navigate_to_url(self.tab_id, url)
        self._url = url
    
    async def wait_for_selector(self, selector: str, timeout: int = 30000, **kwargs) -> 'PlaywrightCompatElement':
        """等待元素出现"""
        timeout_seconds = timeout / 1000
        
        script = f"""
        new Promise((resolve, reject) => {{
            const timeout = setTimeout(() => {{
                reject(new Error('等待元素超时: {selector}'));
            }}, {timeout});
            
            function checkElement() {{
                const element = document.querySelector('{selector}');
                if (element) {{
                    clearTimeout(timeout);
                    resolve(true);
                }} else {{
                    setTimeout(checkElement, 500);
                }}
            }}
            checkElement();
        }})
        """
        
        try:
            await self.adapter.execute_script(self.tab_id, script)
            return PlaywrightCompatElement(selector, self.tab_id, self.adapter)
        except Exception as e:
            raise TimeoutError(f"等待元素超时: {selector}")
    
    async def wait_for_url(self, url_pattern: str, timeout: int = 30000, **kwargs) -> None:
        """等待URL匹配"""
        timeout_seconds = timeout / 1000
        start_time = asyncio.get_event_loop().time()
        
        while True:
            current_url = await self.adapter.get_page_url(self.tab_id)
            if url_pattern in current_url:
                print(f"✅ [{self.tab_id}] URL匹配成功: {url_pattern}")
                return
            
            if asyncio.get_event_loop().time() - start_time > timeout_seconds:
                raise TimeoutError(f"等待URL超时: {url_pattern}, 当前URL: {current_url}")
            
            await asyncio.sleep(0.5)
    
    def locator(self, selector: str) -> 'PlaywrightCompatElement':
        """创建定位器"""
        return PlaywrightCompatElement(selector, self.tab_id, self.adapter)
    
    def get_by_text(self, text: str, **kwargs) -> 'PlaywrightCompatElement':
        """通过文本查找元素"""
        selector = f'//*[contains(text(), "{text}")]'
        return PlaywrightCompatElement(selector, self.tab_id, self.adapter, is_xpath=True)
    
    def get_by_role(self, role: str, name: str = None, **kwargs) -> 'PlaywrightCompatElement':
        """通过角色查找元素"""
        if name:
            selector = f'[role="{role}"][aria-label*="{name}"], [role="{role}"]:contains("{name}"), {role}:contains("{name}")'
        else:
            selector = f'[role="{role}"], {role}'
        return PlaywrightCompatElement(selector, self.tab_id, self.adapter)
    
    async def screenshot(self, path: str = None, **kwargs) -> bytes:
        """截图"""
        try:
            result = self.adapter._make_request('POST', '/account/screenshot', {
                "tabId": self.tab_id
            })
            
            if result.get("success"):
                screenshot_data = result["data"]["screenshot"]
                import base64
                if screenshot_data.startswith('data:image/png;base64,'):
                    image_data = base64.b64decode(screenshot_data.split(',')[1])
                else:
                    image_data = base64.b64decode(screenshot_data)
                
                if path:
                    with open(path, 'wb') as f:
                        f.write(image_data)
                    print(f"📸 [{self.tab_id}] 截图已保存: {path}")
                
                return image_data
            else:
                raise Exception(f"截图失败: {result.get('error')}")
                
        except Exception as e:
            print(f"⚠️ [{self.tab_id}] 截图失败: {e}")
            return b''
    
    async def evaluate(self, script: str, *args) -> Any:
        """执行JavaScript"""
        if args:
            script = f"({script})({', '.join(repr(arg) for arg in args)})"
        return await self.adapter.execute_script(self.tab_id, script)
    
    async def reload(self, **kwargs) -> None:
        """刷新页面"""
        print(f"🔄 [{self.tab_id}] 刷新页面")
        await self.adapter.refresh_page(self.tab_id)
    
    @property
    def url(self) -> str:
        """获取当前URL"""
        try:
            result = self.adapter._make_request('POST', '/account/execute', {
                "tabId": self.tab_id,
                "script": "window.location.href"
            })
            if result.get("success"):
                return result.get("data", self._url)
        except:
            pass
        return self._url
    
    @property  
    def keyboard(self):
        """键盘对象"""
        return PlaywrightCompatKeyboard(self.tab_id, self.adapter)

    async def query_selector(self, selector: str):
        """查询单个元素 - 修复版本"""
        script = f'''
        (() => {{
            const element = document.querySelector("{selector}");
            return element !== null;
        }})()
        '''
        
        try:
            found = await self.adapter.execute_script(self.tab_id, script)
            if found:
                return PlaywrightCompatElement(selector, self.tab_id, self.adapter)
            else:
                return None
        except Exception as e:
            print(f"⚠️ query_selector 执行失败: {e}")
            return None
    
    async def query_selector_all(self, selector: str):
        """查询所有匹配元素 - 兼容 Playwright page.query_selector_all()"""
        script = f'''
        Array.from(document.querySelectorAll("{selector}")).length
        '''
        
        try:
            count = await self.adapter.execute_script(self.tab_id, script)
            if count > 0:
                return [PlaywrightCompatElement(f'{selector}:nth-child({i+1})', self.tab_id, self.adapter) for i in range(count)]
            else:
                return []
        except:
            return []

class PlaywrightCompatElement:
    """兼容 Playwright Element API"""
    
    def __init__(self, selector: str, tab_id: str, adapter: MultiAccountBrowserAdapter, is_xpath: bool = False):
        self.selector = selector
        self.tab_id = tab_id
        self.adapter = adapter
        self.is_xpath = is_xpath
    
    async def click(self, **kwargs) -> None:
        """点击元素"""
        if self.is_xpath:
            script = f'''
            const xpath = "{self.selector}";
            const element = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            if (element) element.click();
            else throw new Error("元素未找到: " + xpath);
            '''
        else:
            script = f'''
            const element = document.querySelector("{self.selector}");
            if (element) element.click();
            else throw new Error("元素未找到: {self.selector}");
            '''
        
        await self.adapter.execute_script(self.tab_id, script)
    
    async def fill(self, value: str, **kwargs) -> None:
        """填充输入"""
        escaped_value = value.replace('"', '\\"').replace('\n', '\\n')
        
        if self.is_xpath:
            script = f'''
            const xpath = "{self.selector}";
            const element = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            if (element) {{
                element.value = "{escaped_value}";
                element.dispatchEvent(new Event("input", {{ bubbles: true }}));
                element.dispatchEvent(new Event("change", {{ bubbles: true }}));
            }} else throw new Error("元素未找到: " + xpath);
            '''
        else:
            script = f'''
            const element = document.querySelector("{self.selector}");
            if (element) {{
                element.value = "{escaped_value}";
                element.dispatchEvent(new Event("input", {{ bubbles: true }}));
                element.dispatchEvent(new Event("change", {{ bubbles: true }}));
            }} else throw new Error("元素未找到: {self.selector}");
            '''
        
        await self.adapter.execute_script(self.tab_id, script)
    
    async def set_input_files(self, files: str | List[str], **kwargs) -> None:
        """设置文件输入 - 关键方法"""
        if isinstance(files, str):
            files = [files]
        
        file_path = files[0] if files else ""
        
        print(f"📁 [{self.tab_id}] 设置文件输入: {file_path}")
        
        # 使用 multi-account-browser 的文件上传API
        result = self.adapter._make_request('POST', '/account/set-input-files', {
            "tabId": self.tab_id,
            "selector": self.selector,
            "filePath": file_path
        }, timeout=120)  # 文件上传可能需要更长时间
        
        if not result.get("success", False):
            raise Exception(f"文件上传失败: {result.get('error')}")
        
        print(f"✅ [{self.tab_id}] 文件设置成功")
    
    async def inner_text(self) -> str:
        """获取内部文本"""
        if self.is_xpath:
            script = f'''
            const xpath = "{self.selector}";
            const element = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            return element ? element.innerText : "";
            '''
        else:
            script = f'document.querySelector("{self.selector}")?.innerText || ""'
        
        return await self.adapter.execute_script(self.tab_id, script)
    
    async def get_attribute(self, name: str) -> str:
        """获取属性值"""
        if self.is_xpath:
            script = f'''
            const xpath = "{self.selector}";
            const element = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            return element ? element.getAttribute("{name}") : null;
            '''
        else:
            script = f'document.querySelector("{self.selector}")?.getAttribute("{name}")'
        
        return await self.adapter.execute_script(self.tab_id, script)
    
    async def is_visible(self) -> bool:
        """检查元素是否可见"""
        if self.is_xpath:
            script = f'''
            const xpath = "{self.selector}";
            const element = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            return element ? (element.offsetParent !== null) : false;
            '''
        else:
            script = f'''
            const element = document.querySelector("{self.selector}");
            return element ? (element.offsetParent !== null) : false;
            '''
        
        return await self.adapter.execute_script(self.tab_id, script)
    
    async def count(self) -> int:
        """获取匹配元素的数量"""
        if self.is_xpath:
            script = f'''
            const xpath = "{self.selector}";
            const result = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
            return result.snapshotLength;
            '''
        else:
            script = f'document.querySelectorAll("{self.selector}").length'
        
        return await self.adapter.execute_script(self.tab_id, script)
    
    def locator(self, selector: str) -> 'PlaywrightCompatElement':
        """子定位器"""
        if self.is_xpath:
            combined_selector = f'{self.selector}//{selector}'
            return PlaywrightCompatElement(combined_selector, self.tab_id, self.adapter, is_xpath=True)
        else:
            combined_selector = f'{self.selector} {selector}'
            return PlaywrightCompatElement(combined_selector, self.tab_id, self.adapter)
    
    def filter(self, has_text: str = None, **kwargs) -> 'PlaywrightCompatElement':
        """过滤元素"""
        if has_text:
            if self.is_xpath:
                filtered_selector = f'{self.selector}[contains(text(), "{has_text}")]'
            else:
                filtered_selector = f'{self.selector}:contains("{has_text}")'
            return PlaywrightCompatElement(filtered_selector, self.tab_id, self.adapter, self.is_xpath)
        return self
    
    def nth(self, index: int) -> 'PlaywrightCompatElement':
        """获取第n个元素"""
        if self.is_xpath:
            nth_selector = f'({self.selector})[{index + 1}]'
        else:
            nth_selector = f'{self.selector}:nth-child({index + 1})'
        return PlaywrightCompatElement(nth_selector, self.tab_id, self.adapter, self.is_xpath)
    
    @property
    def first(self) -> 'PlaywrightCompatElement':
        """第一个元素"""
        return self.nth(0)


class PlaywrightCompatKeyboard:
    """兼容 Playwright Keyboard API"""
    
    def __init__(self, tab_id: str, adapter: MultiAccountBrowserAdapter):
        self.tab_id = tab_id
        self.adapter = adapter
    
    async def press(self, key: str, **kwargs) -> None:
        """按键"""
        key_map = {
            "Enter": "Enter",
            "Tab": "Tab", 
            "Control+KeyA": "Control+a",
            "Escape": "Escape",
            "Control+a": "Control+a",
            "Space": " "
        }
        
        mapped_key = key_map.get(key, key)
        
        script = f'''
        const event = new KeyboardEvent('keydown', {{
            key: '{mapped_key}',
            code: '{mapped_key}',
            ctrlKey: {str('Control' in key).lower()},
            shiftKey: {str('Shift' in key).lower()}
        }});
        document.activeElement.dispatchEvent(event);
        '''
        
        await self.adapter.execute_script(self.tab_id, script)
    
    async def type(self, text: str, delay: int = 0, **kwargs) -> None:
        """输入文本"""
        escaped_text = text.replace('"', '\\"').replace('\n', '\\n')
        
        script = f'''
        const activeElement = document.activeElement;
        if (activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA')) {{
            activeElement.value += "{escaped_text}";
            activeElement.dispatchEvent(new Event("input", {{ bubbles: true }}));
        }} else {{
            // 尝试在可编辑div中输入
            if (activeElement && activeElement.contentEditable === 'true') {{
                activeElement.textContent += "{escaped_text}";
                activeElement.dispatchEvent(new Event("input", {{ bubbles: true }}));
            }}
        }}
        '''
        
        await self.adapter.execute_script(self.tab_id, script)


class PlaywrightCompatContext:
    """兼容 Playwright Context API - 重新设计为标签页管理"""
    
    def __init__(self, storage_state: str = None):
        self.storage_state = storage_state
        self.tab_manager = AccountTabManager.get_instance()
        self._pages = []
    
    async def new_page(self) -> PlaywrightCompatPage:
        if self.storage_state:
            # 现有账号：使用 storage_state
            tab_id = await self.tab_manager.get_or_create_account_tab(self.storage_state)
        else:
            # 🔥 新账号：创建空白标签页，不指定平台
            tab_id = await self.tab_manager.create_temp_blank_tab()
        
        page = PlaywrightCompatPage(tab_id, self.tab_manager, self.storage_state)
        self._pages.append(page)
        return page
    
    async def storage_state(self, path: str = None) -> Dict:
        """保存存储状态"""
        if path and self._pages:
            # 保存当前页面对应的账号状态
            page = self._pages[0]
            await self.tab_manager.save_account_state(path, page.tab_id)
        return {}
    
    async def close(self) -> None:
        """关闭上下文 - 在标签页复用模式下，这里不关闭标签页"""
        print(f"📝 Context.close() - 保留标签页以供复用")
        
        # 保存当前状态
        if self.storage_state and self._pages:
            await self.tab_manager.save_account_state(self.storage_state, self._pages[0].tab_id)
        
        # 清理页面引用，但不关闭实际的标签页
        self._pages.clear()


class PlaywrightCompatBrowser:
    """兼容 Playwright Browser API - 简化为标签页工厂"""
    
    def __init__(self):
        self.tab_manager = AccountTabManager.get_instance()
        self._contexts = []
        print(f"🚀 浏览器实例创建完成 (multi-account-browser 模式)")
    
    async def new_context(self, storage_state: str = None, **kwargs) -> PlaywrightCompatContext:
        """创建新上下文"""
        print(f"\n🎯 Browser.new_context() - 准备账号上下文")
        print(f"   storage_state: {storage_state}")
        
        # 🔥 修复：只传递 storage_state，忽略其他参数
        context = PlaywrightCompatContext(storage_state)
        self._contexts.append(context)
        return context


class PlaywrightCompatChromium:
    """兼容 Playwright Chromium API"""
    
    async def launch(self, headless: bool = True, executable_path: str = None, **kwargs) -> PlaywrightCompatBrowser:
        """
        启动浏览器 - 核心变化！
        这里不再启动新的Chrome进程，而是使用multi-account-browser的标签页
        """
        print(f"\n🚀 Chromium.launch() - multi-account-browser 模式")
        print(f"   headless: {headless} (忽略，使用 multi-account-browser)")
        print(f"   executable_path: {executable_path} (忽略)")
        
        # 检查 multi-account-browser 是否可用
        tab_manager = AccountTabManager.get_instance()
        adapter = tab_manager.get_adapter()
        
        try:
            # 简单的健康检查
            result = adapter._make_request('GET', '/health')
            if result.get('success'):
                print(f"✅ multi-account-browser 连接成功")
            else:
                print(f"⚠️ multi-account-browser 连接异常")
        except Exception as e:
            print(f"❌ multi-account-browser 连接失败: {e}")
            print(f"   请确保 multi-account-browser 正在运行 (http://localhost:3000)")
            raise Exception("multi-account-browser 不可用")
        
        return PlaywrightCompatBrowser()


class PlaywrightCompatPlaywright:
    """兼容 Playwright 主对象"""
    
    def __init__(self):
        self.chromium = PlaywrightCompatChromium()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


# ========================================
# 替换函数
# ========================================

async def async_playwright_compat() -> PlaywrightCompatPlaywright:
    """
    替换原来的 async_playwright() 函数
    
    迁移步骤：
    1. 将 from playwright.async_api import async_playwright
       改为 from utils.playwright_compat import async_playwright_compat as async_playwright
    
    2. 其他代码完全不变！
    """
    return PlaywrightCompatPlaywright()


# 便捷函数
def get_account_tab_manager() -> AccountTabManager:
    """获取账号标签页管理器 - 用于调试和高级操作"""
    return AccountTabManager.get_instance()


def debug_print_all_tabs():
    """调试函数：打印所有账号标签页"""
    manager = AccountTabManager.get_instance()
    manager.debug_print_tabs()


# 类型注解兼容
Playwright = PlaywrightCompatPlaywright
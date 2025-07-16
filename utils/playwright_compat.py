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
class MainFrame:
    """主框架对象 - 更简单的实现"""
    
    def __init__(self, page):
        self.url = ""
        self.name = "main"
        self._page = page
    
    def __eq__(self, other):
        # 🔥 确保 frame == page.main_frame 返回 True
        return other is self
class PlaywrightCompatPage:
    """兼容 Playwright Page API"""
    
    def __init__(self, tab_id: str, tab_manager: AccountTabManager, storage_state: str = None, init_scripts: str = None):
        self.tab_id = tab_id
        self.tab_manager = tab_manager
        self.adapter = tab_manager.get_adapter()
        self.storage_state = storage_state
        self._url = ""
        self._event_listeners = {}  # 🔥 新增：事件监听器存储
        self.main_frame = MainFrame(self)
        self._monitoring_task = None

    def on(self, event: str, handler) -> None:
        if event not in self._event_listeners:
            self._event_listeners[event] = []
        self._event_listeners[event].append(handler)
        
        # 🔥 如果是 framenavigated 事件且还没有监控任务，就启动监控
        if event == 'framenavigated' and not self._monitoring_task:
            self._monitoring_task = asyncio.create_task(self._start_url_monitoring())

    async def _start_url_monitoring(self) -> None:
        """URL 变化监控 - 简化版本"""
        print(f"🔍 [{self.tab_id}] 启动 URL 变化监控")
        
        current_url = self._url
        
        while True:  # 🔥 简化：不需要额外的停止条件
            try:
                new_url = await self.adapter.execute_script(self.tab_id, 'window.location.href')
                
                if new_url and new_url != current_url:
                    print(f"🔄 [{self.tab_id}] URL 变化: {current_url} -> {new_url}")
                    
                    current_url = new_url
                    self._url = new_url
                    self.main_frame.url = new_url
                    
                    # 触发事件
                    if 'framenavigated' in self._event_listeners:
                        for handler in self._event_listeners['framenavigated']:
                            try:
                                result = handler(self.main_frame)
                                if hasattr(result, '__await__'):
                                    await result
                            except Exception as e:
                                print(f"⚠️ [{self.tab_id}] 事件处理器执行失败: {e}")
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"⚠️ [{self.tab_id}] URL 监控异常: {e}")
                await asyncio.sleep(0.5)

    async def goto(self, url: str, **kwargs) -> None:
        """导航到指定URL - 简化版本，初始化脚本由 multi-account-browser 自动处理"""
        
        print(f"🔗 [{self.tab_id}] 导航到: {url}")
        
        # 🔥 直接导航，初始化脚本会由 TabManager 在 did-finish-load 时自动注入
        await self.adapter.navigate_to_url(self.tab_id, url)
        self._url = url
        
        # 简单等待页面加载完成
        await asyncio.sleep(3)  # 或者你可以保留一个简单的等待逻辑
        
        print(f"✅ [{self.tab_id}] 导航完成")

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
            selector = f'[role="{role}"][aria-label*="{name}"], [role="{role}"]'
        else:
            if role.lower() == 'img':
                selector = 'img'  # 🔥 简化：直接使用 img 标签
            else:
                selector = f'[role="{role}"], {role}'
        
        print(f"🎯 [{self.tab_id}] get_by_role 生成选择器: {selector}")
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
        # 转义选择器中的特殊字符
        escaped_selector = selector.replace('"', '\\"')
        
        script = f'''
        (() => {{
            try {{
                const element = document.querySelector("{escaped_selector}");
                return element !== null;
            }} catch (e) {{
                console.error("选择器错误:", e);
                return false;
            }}
        }})()
        '''
        
        try:
            found = await self.adapter.execute_script(self.tab_id, script)
            if found:
                return PlaywrightCompatElement(selector, self.tab_id, self.adapter)
            else:
                return None
        except Exception as e:
            print(f"⚠️ query_selector 执行失败 - selector: {selector}, error: {e}")
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
    def frame_locator(self, selector: str) -> 'PlaywrightCompatFrameLocator':
        """创建框架定位器"""
        return PlaywrightCompatFrameLocator(selector, self.tab_id, self.adapter)

class PlaywrightCompatFrameLocator:
    """兼容 Playwright FrameLocator API - 完整版"""
    
    def __init__(self, selector: str, tab_id: str, adapter):
        self.selector = selector
        self.tab_id = tab_id
        self.adapter = adapter
    
    @property
    def first(self) -> 'PlaywrightCompatElement':
        """获取第一个匹配的框架"""
        # 对于iframe，我们需要特殊处理
        if self.selector.lower() == 'iframe':
            # 返回一个特殊的元素，用于后续在iframe内查找
            return PlaywrightCompatElement('iframe:first-of-type', self.tab_id, self.adapter, is_iframe=True)
        else:
            return PlaywrightCompatElement(f'{self.selector}:first-of-type', self.tab_id, self.adapter)
    
    def get_by_role(self, role: str, name: str = None, **kwargs) -> 'PlaywrightCompatElement':
        """在框架内通过角色查找元素"""
        if role.lower() == 'img':
            # 针对你的具体需求：在iframe内查找img
            iframe_img_selector = f'iframe img'
        else:
            iframe_img_selector = f'iframe [role="{role}"]'
        
        return PlaywrightCompatElement(iframe_img_selector, self.tab_id, self.adapter, is_iframe_content=True)


class PlaywrightCompatElement:
    """兼容 Playwright Element API - 支持iframe"""
    
    def __init__(self, selector: str, tab_id: str, adapter, is_xpath: bool = False, is_iframe: bool = False, is_iframe_content: bool = False):
        self.selector = selector
        self.tab_id = tab_id
        self.adapter = adapter
        self.is_xpath = is_xpath
        self.is_iframe = is_iframe
        self.is_iframe_content = is_iframe_content

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
        await asyncio.sleep(1)

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
    
    def nth(self, index: int) -> 'PlaywrightCompatElement':
        """获取第n个元素 - 修复索引计算"""
        if self.is_xpath:
            # XPath 是 1-based，但 Playwright nth() 是 0-based
            # 所以要 +1 转换
            nth_selector = f'({self.selector})[{index + 1}]'
        else:
            # JavaScript 数组是 0-based，与 Playwright 一致
            nth_selector = f'__INDEX_SELECTOR__{self.selector}__INDEX__{index}'
        
        print(f"🎯 [{self.tab_id}] nth({index}) 生成选择器: {nth_selector}")
        return PlaywrightCompatElement(nth_selector, self.tab_id, self.adapter, self.is_xpath)

    async def get_attribute(self, name: str) -> str:
        """获取属性值 - 支持索引选择器"""
        # 🔥 检查是否是iframe内容查询
        if 'iframe' in self.selector and 'img' in self.selector:
            # 特殊处理：访问iframe内部的元素
            script = f'''
            (() => {{
                try {{
                    console.log("开始查找iframe内的img元素");
                    
                    // 查找页面中的第一个iframe
                    const iframe = document.querySelector('iframe');
                    if (!iframe) {{
                        console.log("页面中没有找到iframe");
                        return null;
                    }}
                    
                    console.log("找到iframe，尝试访问其内容");
                    
                    // 等待iframe加载完成
                    if (!iframe.contentDocument && !iframe.contentWindow) {{
                        console.log("iframe还未加载完成");
                        return null;
                    }}
                    
                    // 获取iframe的文档
                    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                    if (!iframeDoc) {{
                        console.log("无法访问iframe文档");
                        return null;
                    }}
                    
                    // 在iframe内查找img元素
                    const imgElements = iframeDoc.querySelectorAll('img');
                    console.log("iframe内找到", imgElements.length, "个img元素");
                    
                    if (imgElements.length > 0) {{
                        const firstImg = imgElements[0];
                        const srcValue = firstImg.getAttribute("{name}");
                        console.log("第一个img的{name}属性:", srcValue);
                        return srcValue;
                    }} else {{
                        console.log("iframe内没有找到img元素");
                        return null;
                    }}
                    
                }} catch (e) {{
                    console.error("访问iframe内容时出错:", e);
                    return null;
                }}
            }})()
            '''
            
            try:
                result = await self.adapter.execute_script(self.tab_id, script)
                if result and result.strip():
                    print(f"✅ [{self.tab_id}] 成功获取iframe内img的{name}: {result[:50]}...")
                    return result
                else:
                    print(f"⚠️ [{self.tab_id}] iframe内img的{name}属性为空")
                    return ""
            except Exception as e:
                print(f"❌ [{self.tab_id}] 获取iframe内容失败: {e}")
                return ""
        
        # 🔥 检查是否是索引选择器
        elif '__INDEX_SELECTOR__' in self.selector:
            # 你现有的索引选择器处理逻辑保持不变
            parts = self.selector.split('__INDEX_SELECTOR__')[1].split('__INDEX__')
            base_selector = parts[0]
            index = int(parts[1])
            
            script = f'''
            (() => {{
                try {{
                    const elements = document.querySelectorAll("{base_selector}");
                    if (elements.length > {index}) {{
                        const element = elements[{index}];
                        const value = element.getAttribute("{name}");
                        return value;
                    }} else {{
                        return null;
                    }}
                }} catch (e) {{
                    return null;
                }}
            }})()
            '''
            
            try:
                result = await self.adapter.execute_script(self.tab_id, script)
                return result or ""
            except Exception as e:
                print(f"❌ [{self.tab_id}] 获取属性失败: {e}")
                return ""
        
        else:
                # 原有的选择器逻辑
                script = f'''
                (() => {{
                    try {{
                        const element = document.querySelector("{self.selector}");
                        return element ? element.getAttribute("{name}") : null;
                    }} catch (e) {{
                        return null;
                    }}
                }})()
                '''
        
        try:
            result = await self.adapter.execute_script(self.tab_id, script)
            if result and result.strip():
                return result
            else:
                print(f"⚠️ [{self.tab_id}] 属性 '{name}' 为空或null")
                return ""
        except Exception as e:
            print(f"❌ [{self.tab_id}] 获取属性失败: {e}")
            return ""
            
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

    def get_by_role(self, role: str, name: str = None, **kwargs) -> 'PlaywrightCompatElement':
        """通过角色查找子元素"""
        if name:
            sub_selector = f'[role="{role}"][aria-label*="{name}"], [role="{role}"]'
        else:
            if role.lower() == 'img':
                sub_selector = 'img'
            else:
                sub_selector = f'[role="{role}"], {role}'
        
        # 组合选择器：在当前元素内查找
        if self.is_xpath:
            combined_selector = f'{self.selector}//{sub_selector}'
            return PlaywrightCompatElement(combined_selector, self.tab_id, self.adapter, is_xpath=True)
        else:
            combined_selector = f'{self.selector} {sub_selector}'
            return PlaywrightCompatElement(combined_selector, self.tab_id, self.adapter)

    def get_by_text(self, text: str, **kwargs) -> 'PlaywrightCompatElement':
        """通过文本查找子元素"""
        if self.is_xpath:
            xpath_selector = f'{self.selector}//*[contains(text(), "{text}")]'
            return PlaywrightCompatElement(xpath_selector, self.tab_id, self.adapter, is_xpath=True)
        else:
            # CSS选择器不能直接按文本查找，需要用JavaScript
            combined_selector = f'{self.selector}__TEXT_SEARCH__{text}'
            return PlaywrightCompatElement(combined_selector, self.tab_id, self.adapter)

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
        self._init_scripts = []  # 存储初始化脚本

    async def add_init_script(self, script: str = None, path: str = None, **kwargs) -> 'PlaywrightCompatContext':
        """添加初始化脚本 - 极简版本"""
        
        # 处理参数
        if isinstance(script, dict):
            if 'path' in script:
                path = script['path']
                script = None
            elif 'content' in script:
                script = script['content']
        
        # 获取脚本内容
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    script_content = f.read()
                print(f"📜 从文件加载初始化脚本: {path}")
            except Exception as e:
                print(f"⚠️ 读取脚本文件失败: {path}, {e}")
                return self
        elif script:
            script_content = script
            print(f"📜 注册内联初始化脚本")
        else:
            print("⚠️ addInitScript: 未提供脚本内容")
            return self
        
        # 🔥 关键简化：直接存储脚本，在 newPage 时应用
        self._init_scripts.append(script_content)
        print(f"✅ 初始化脚本已注册 (总计: {len(self._init_scripts)} 个)")
        
        return self

    async def new_page(self) -> 'PlaywrightCompatPage':
        """创建新页面 - 🔥 极简化，使用 multi-account-browser 原生能力"""
        
        print(f"\n🎯 Context.newPage() - 创建页面")
        
        # 1. 获取或创建标签页
        if self.storage_state:
            tab_id = await self.tab_manager.get_or_create_account_tab(self.storage_state)
        else:
            tab_id = await self.tab_manager.create_temp_blank_tab()
        
        # 2. 🔥 核心简化：直接调用 multi-account-browser 的 addInitScript API
        if self._init_scripts:
            await self._apply_init_scripts_to_tab(tab_id)
        
        # 3. 创建页面对象
        page = PlaywrightCompatPage(
            tab_id=tab_id, 
            tab_manager=self.tab_manager, 
            storage_state=self.storage_state
        )
        self._pages.append(page)
        
        print(f"✅ [{tab_id}] 页面创建完成")
        return page

    async def _apply_init_scripts_to_tab(self, tab_id: str) -> None:
        """应用初始化脚本到标签页 - 🔥 直接使用 multi-account-browser API"""
        
        print(f"📜 [{tab_id}] 应用 {len(self._init_scripts)} 个初始化脚本")
        
        for i, script_content in enumerate(self._init_scripts):
            try:
                # 🔥 关键：直接调用 multi-account-browser 的原生 API
                result = self.tab_manager.get_adapter()._make_request('POST', '/account/add-init-script', {
                    "tabId": tab_id,
                    "script": script_content
                })
                
                if result.get("success"):
                    print(f"✅ [{tab_id}] 脚本 {i+1} 应用成功")
                else:
                    print(f"❌ [{tab_id}] 脚本 {i+1} 应用失败: {result.get('error')}")
                    
            except Exception as e:
                print(f"❌ [{tab_id}] 脚本 {i+1} 应用异常: {e}")

    async def storage_state(self, path: str = None) -> Dict:
        """保存存储状态"""
        if path and self._pages:
            # 保存当前页面对应的账号状态
            page = self._pages[0]
            await self.tab_manager.save_account_state(path, page.tab_id)
        #return {}

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
        from utils.playwright_compat import get_account_tab_manager
        self.tab_manager = get_account_tab_manager()
        self._contexts = []
        print(f"🚀 浏览器实例创建完成 (multi-account-browser 模式)")
    
    async def new_context(self, storage_state: str = None, **kwargs) -> 'PlaywrightCompatContext':
        """创建新上下文"""
        print(f"\n🎯 Browser.new_context() - 准备账号上下文")
        print(f"   storage_state: {storage_state}")
        
        context = PlaywrightCompatContext(storage_state)
        self._contexts.append(context)
        return context


class PlaywrightCompatChromium:
    """兼容 Playwright Chromium API"""
    
    async def launch(self, headless: bool = True, executable_path: str = None, **kwargs) -> PlaywrightCompatBrowser:
        """启动浏览器"""
        print(f"\n🚀 Chromium.launch() - multi-account-browser 模式")
        print(f"   headless: {headless} (忽略，使用 multi-account-browser)")
        
        # 检查 multi-account-browser 是否可用
        from utils.playwright_compat import get_account_tab_manager
        tab_manager = get_account_tab_manager()
        adapter = tab_manager.get_adapter()
        
        try:
            result = adapter._make_request('GET', '/health')
            if result.get('success'):
                print(f"✅ multi-account-browser 连接成功")
            else:
                print(f"⚠️ multi-account-browser 连接异常")
        except Exception as e:
            print(f"❌ multi-account-browser 连接失败: {e}")
            raise Exception("multi-account-browser 不可用")
        
        return PlaywrightCompatBrowser()


class PlaywrightCompatPlaywright:
    """兼容 Playwright 主对象"""
    
    def __init__(self):
        self.chromium = PlaywrightCompatChromium()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        print("🛑 PlaywrightCompat 上下文管理器关闭")   
        if exc_type:
            print(f"⚠️ PlaywrightCompat 上下文中发生异常: {exc_type.__name__}: {exc_val}")
        return False

# ========================================
# 替换函数
# ========================================

def async_playwright_compat() -> PlaywrightCompatPlaywright:
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
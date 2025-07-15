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
    
    def __init__(self, tab_id: str, tab_manager: AccountTabManager, storage_state: str = None, init_scripts: str = None):
        self.tab_id = tab_id
        self.tab_manager = tab_manager
        self.adapter = tab_manager.get_adapter()
        self.storage_state = storage_state
        self.init_scripts = init_scripts
        self._url = ""
        self.init_scripts = init_scripts or []  # 从 Context 继承的脚本
        self._navigation_count = 0  # 🔥 导航计数器
        self._scripts_injected = False  # 🔥 脚本注入状态标记
        self._event_listeners = {}  # 🔥 新增：事件监听器存储
        self.main_frame = self

    def on(self, event: str, handler) -> None:
        """添加事件监听器 - 兼容 Playwright API"""
        if event not in self._event_listeners:
            self._event_listeners[event] = []
        self._event_listeners[event].append(handler)
        print(f"📡 [{self.tab_id}] 添加事件监听器: {event}")
        
        # 🔥 对于 framenavigated 事件，我们需要启动 URL 监控
        if event == 'framenavigated':
            asyncio.create_task(self._start_url_monitoring())
    
    async def _start_url_monitoring(self) -> None:
        """启动 URL 变化监控"""
        print(f"🔍 [{self.tab_id}] 启动 URL 变化监控")
        
        current_url = self._url
        check_interval = 1  # 每秒检查一次
        
        while True:
            try:
                # 获取当前页面 URL
                new_url = await self.adapter.execute_script(self.tab_id, 'window.location.href')
                
                if new_url and new_url != current_url:
                    print(f"🔄 [{self.tab_id}] URL 变化: {current_url} -> {new_url}")
                    
                    # 触发 framenavigated 事件
                    if 'framenavigated' in self._event_listeners:
                        for handler in self._event_listeners['framenavigated']:
                            try:
                                # 创建模拟的 frame 对象
                                mock_frame = type('MockFrame', (), {
                                    'url': new_url,
                                    'name': 'main'
                                })()
                                
                                # 调用处理器
                                if asyncio.iscoroutinefunction(handler):
                                    await handler(mock_frame)
                                else:
                                    handler(mock_frame)
                            except Exception as e:
                                print(f"⚠️ [{self.tab_id}] 事件处理器执行失败: {e}")
                    
                    current_url = new_url
                    self._url = new_url
                
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                print(f"⚠️ [{self.tab_id}] URL 监控异常: {e}")
                await asyncio.sleep(check_interval)
    async def goto(self, url: str, **kwargs) -> None:
        """导航到指定URL - 简化版本"""
        print(f"🔗 [{self.tab_id}] 导航到: {url} (第 {self._navigation_count + 1} 次导航)")
        
        self._navigation_count += 1
        
        # 在首次导航前处理初始化脚本
        if self.init_scripts and self._navigation_count == 1 and not self._scripts_injected:
            await self._register_init_scripts_before_first_navigation()
        
        # 执行导航
        await self.adapter.navigate_to_url(self.tab_id, url)
        self._url = url
        
        # 等待页面加载完成
        await self._wait_for_page_ready()
        
        # 确保脚本在页面加载后执行（备用保障）
        if hasattr(self, '_fallback_scripts_needed') and self._fallback_scripts_needed:
            await self._inject_fallback_scripts()
            self._fallback_scripts_needed = False  # 执行后清除标记
    

    async def _register_init_scripts_before_first_navigation(self) -> None:
        """在首次导航前注册初始化脚本"""
        print(f"📜 [{self.tab_id}] 首次导航前准备 {len(self.init_scripts)} 个初始化脚本")
        
        self._scripts_injected = True
        
        # 🔥 关键修改：由于 multi-account-browser 不支持 add-init-script API
        # 直接标记使用备用方案
        print(f"📋 [{self.tab_id}] multi-account-browser 不支持 add-init-script API，使用备用方案")
        self._fallback_scripts_needed = True
        
        # 🔥 或者，我们可以尝试其他方式，比如在导航前立即执行脚本
        # 这样可以在页面内容加载前执行，接近原始的 init-script 效果
        if True:  # 尝试预执行方案
            await self._pre_execute_init_scripts()

    async def _pre_execute_init_scripts(self) -> None:
        """预执行初始化脚本 - 在导航前执行"""
        print(f"🚀 [{self.tab_id}] 在导航前预执行 {len(self.init_scripts)} 个初始化脚本")
        
        for i, script_content in enumerate(self.init_scripts):
            try:
                # 🔥 关键：包装脚本，使其能在任何环境下安全执行
                pre_execute_script = f'''
                (function() {{
                    try {{
                        console.log("预执行初始化脚本 {i+1}...");
                        
                        // 如果当前页面是 about:blank，设置一些基本的全局变量
                        if (window.location.href === 'about:blank') {{
                            console.log("在空白页面设置初始化脚本...");
                            // 将脚本保存到全局变量，等页面加载时执行
                            window.__initScripts = window.__initScripts || [];
                            window.__initScripts.push(function() {{
                                {script_content}
                            }});
                            return "queued";
                        }} else {{
                            // 如果已经有页面内容，直接执行
                            console.log("直接执行初始化脚本...");
                            {script_content}
                            return "executed";
                        }}
                    }} catch (e) {{
                        console.error("预执行脚本失败:", e.message);
                        return "failed";
                    }}
                }})();
                '''
                
                result = await self.adapter.execute_script(self.tab_id, pre_execute_script)
                print(f"✅ [{self.tab_id}] 预执行脚本 {i+1} 结果: {result}")
                
            except Exception as e:
                print(f"⚠️ [{self.tab_id}] 预执行脚本 {i+1} 失败: {e}")
    
        # 设置页面加载监听器，确保脚本在新页面加载时也能执行
        await self._setup_script_execution_listener()

    async def _setup_script_execution_listener(self) -> None:
        """设置脚本执行监听器"""
        try:
            listener_script = '''
            (function() {
                console.log("设置初始化脚本监听器...");
                
                // 监听页面加载事件
                function executeQueuedScripts() {
                    if (window.__initScripts && window.__initScripts.length > 0) {
                        console.log("执行队列中的初始化脚本:", window.__initScripts.length);
                        window.__initScripts.forEach(function(scriptFunc, index) {
                            try {
                                scriptFunc();
                                console.log("队列脚本", index + 1, "执行成功");
                            } catch (e) {
                                console.error("队列脚本", index + 1, "执行失败:", e);
                            }
                        });
                        // 清空队列
                        window.__initScripts = [];
                    }
                }
                
                // 如果 DOM 已经加载，立即执行
                if (document.readyState !== 'loading') {
                    executeQueuedScripts();
                }
                
                // 监听 DOM 加载完成
                document.addEventListener('DOMContentLoaded', executeQueuedScripts);
                
                // 监听页面完全加载
                window.addEventListener('load', executeQueuedScripts);
                
                return "listener_set";
            })();
            '''
            
            result = await self.adapter.execute_script(self.tab_id, listener_script)
            print(f"✅ [{self.tab_id}] 脚本监听器设置结果: {result}")
            
        except Exception as e:
            print(f"⚠️ [{self.tab_id}] 设置脚本监听器失败: {e}")

    async def _inject_fallback_scripts(self) -> None:
        """备用方案：导航后立即注入脚本"""
        print(f"🔧 [{self.tab_id}] 使用备用方案注入 {len(self.init_scripts)} 个脚本")
        
        for i, script_content in enumerate(self.init_scripts):
            try:
                # 包装脚本以提高成功率
                safe_script = f'''
                (function() {{
                    try {{
                        console.log("执行备用初始化脚本 {i+1}...");
                        
                        // 等待 DOM 基本就绪
                        if (document.readyState === 'loading') {{
                            console.log("DOM 仍在加载，延迟执行脚本...");
                            setTimeout(function() {{
                                try {{
                                    {script_content}
                                    console.log("延迟执行的初始化脚本完成");
                                }} catch (e) {{
                                    console.error("延迟执行脚本失败:", e);
                                }}
                            }}, 1000);
                        }} else {{
                            console.log("立即执行初始化脚本...");
                            {script_content}
                            console.log("立即执行的初始化脚本完成");
                        }}
                        return true;
                    }} catch (e) {{
                        console.error("备用脚本执行失败:", e.message);
                        console.error("错误堆栈:", e.stack);
                        return false;
                    }}
                }})();
                '''
                
                result = await self.adapter.execute_script(self.tab_id, safe_script)
                print(f"✅ [{self.tab_id}] 备用脚本 {i+1} 执行结果: {result}")
                
            except Exception as e:
                print(f"❌ [{self.tab_id}] 备用脚本 {i+1} 执行失败: {e}")
        
        # 清除标记
        self._fallback_scripts_needed = False
    
    async def _wait_for_page_ready(self) -> None:
        """等待页面就绪 - 保持原有逻辑"""
        print(f"⏳ [{self.tab_id}] 等待页面加载完成...")
        
        max_wait_time = 10  # 减少等待时间
        check_interval = 0.5
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < max_wait_time:
            try:
                page_status = await self.adapter.execute_script(self.tab_id, '''
                (function() {
                    try {
                        return {
                            readyState: document.readyState,
                            hasBody: !!document.body,
                            url: window.location.href,
                            bodyChildren: document.body ? document.body.children.length : 0
                        };
                    } catch (e) {
                        return { error: e.message, readyState: 'loading' };
                    }
                })()
                ''')
                
                if page_status:
                    ready_state = page_status.get('readyState')
                    has_body = page_status.get('hasBody', False)
                    body_children = page_status.get('bodyChildren', 0)
                    
                    if (ready_state in ['interactive', 'complete'] and 
                        has_body and body_children > 0):
                        print(f"✅ [{self.tab_id}] 页面加载完成")
                        return
                
            except Exception as e:
                print(f"⚠️ [{self.tab_id}] 页面状态检查失败: {e}")
            
            await asyncio.sleep(check_interval)
        
        print(f"⚠️ [{self.tab_id}] 页面加载等待超时，继续执行")
    
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
        await asyncio.sleep(3)

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
        """获取第n个元素 - 修复版本，使用索引而不是 nth-of-type"""
        if self.is_xpath:
            nth_selector = f'({self.selector})[{index + 1}]'
        else:
            # 🔥 关键修复：不使用 nth-of-type，直接用 JavaScript 索引
            nth_selector = f'__INDEX_SELECTOR__{self.selector}__INDEX__{index}'
        
        print(f"🎯 [{self.tab_id}] nth({index}) 生成选择器: {nth_selector}")
        return PlaywrightCompatElement(nth_selector, self.tab_id, self.adapter, self.is_xpath)

    async def get_attribute(self, name: str) -> str:
        """获取属性值 - 支持索引选择器"""
        
        # 🔥 检查是否是索引选择器
        if '__INDEX_SELECTOR__' in self.selector:
            parts = self.selector.split('__INDEX_SELECTOR__')[1].split('__INDEX__')
            base_selector = parts[0]
            index = int(parts[1])
            
            script = f'''
            (() => {{
                try {{
                    const elements = document.querySelectorAll("{base_selector}");
                    console.log("找到元素数量:", elements.length);
                    
                    if (elements.length > {index}) {{
                        const element = elements[{index}];
                        const value = element.getAttribute("{name}");
                        console.log("索引", {index}, "元素的", "{name}", "属性:", value);
                        return value;
                    }} else {{
                        console.log("索引", {index}, "超出范围，总数:", elements.length);
                        return null;
                    }}
                }} catch (e) {{
                    console.error("索引选择器错误:", e);
                    return null;
                }}
            }})()
            '''
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
                print(f"✅ [{self.tab_id}] 成功获取属性 '{name}': {result[:50]}...")
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

    async def add_init_script(self, script: str = None, path: str = None) -> 'PlaywrightCompatContext':
        """
        添加初始化脚本 - 模拟 Playwright 的 Context 级别脚本注册
        注意：这里只是注册脚本，不执行！
        """
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    script_content = f.read()
            except Exception as e:
                print(f"⚠️ 读取脚本文件失败: {path}, {e}")
                return self
        elif script:
            script_content = script
        else:
            print("⚠️ add_init_script: 未提供脚本内容或路径")
            return self
        
        # 🔥 关键：只注册脚本，不立即执行
        self._init_scripts.append(script_content)
        print(f"📜 初始化脚本已注册到 Context: {len(script_content)} 字符")
        
        return self  # 返回 self 保持链式调用
    
    async def new_page(self) -> PlaywrightCompatPage:
        """创建新页面 - 传递初始化脚本给页面"""
        if self.storage_state:
            tab_id = await self.tab_manager.get_or_create_account_tab(self.storage_state)
        else:
            tab_id = await self.tab_manager.create_temp_blank_tab()
        
        # 🔥 关键：将 Context 级别的脚本传递给页面
        page = PlaywrightCompatPage(
            tab_id=tab_id, 
            tab_manager=self.tab_manager, 
            storage_state=self.storage_state,
            init_scripts=self._init_scripts.copy()  # 传递脚本副本
        )
        self._pages.append(page)
        
        print(f"📄 [{tab_id}] 页面创建完成，已继承 {len(self._init_scripts)} 个初始化脚本")
        
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
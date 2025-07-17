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
            try:
                from conf import BASE_DIR
                db_path = str(BASE_DIR / "db" / "database.db")
                cls._adapter.set_database_path(db_path)
                print(f"🐛 AccountTabManager 数据库路径设置: {db_path}")
            except Exception as e:
                print(f"⚠️ 设置数据库路径失败: {e}")
        return cls._instance
    
    @classmethod
    def get_instance(cls):
        return cls()
    @property
    def db_path(self):
        """代理到 adapter 的 db_path"""
        return self._adapter.db_path if self._adapter else None

    def generate_account_key(self, storage_state: str) -> str:
        """根据 storage_state 生成账号唯一标识 - 🔥 统一参数名"""
        if not storage_state:
            return "default_account"
        
        return str(Path(storage_state).absolute())

    async def create_temp_blank_tab(self) -> str:
        """创建临时空白标签页"""
        return await self._adapter.create_account_tab("temp", "temp_login", "about:blank")

    def infer_platform_from_storage(self, storage_state: str) -> str:
        """从数据库获取平台类型 - 🔥 统一参数名"""
        if not storage_state:
            return "weixin"
        
        account_info = self.get_account_info_from_db(storage_state)
        if account_info and account_info.get('platform_type'):
            platform_type = account_info['platform_type']
            platform_map = {1: 'xiaohongshu', 2: 'weixin', 3: 'douyin', 4: 'kuaishou'}
            return platform_map.get(platform_type, 'weixin')
        
        print(f"⚠️ 数据库中未找到账号信息: {Path(storage_state).name}")
        return "weixin"
        
    def get_account_info_from_db(self, cookie_file: str) -> Optional[Dict[str, Any]]:
        """从数据库获取账号信息"""
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
                        'platform_type': platform_type
                    }
                else:
                    print(f"⚠️ 数据库中未找到账号信息: {cookie_filename}")
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
    
    async def get_or_create_account_tab(self, storage_state: str = None, auto_navigate: bool = True) -> str:
        """获取或创建账号标签页 - 修复版本"""
        account_key = self.generate_account_key(storage_state)
        platform = self.infer_platform_from_storage(storage_state)
        
        print(f"\n🎯 获取或创建账号标签页:")
        print(f"   账号标识: {account_key}")
        print(f"   平台: {platform}")
        print(f"   自动导航: {auto_navigate}")
        
        # 🔥 步骤1：首先检查内存缓存中的标签页
        if account_key in self._account_tabs:
            tab_id = self._account_tabs[account_key]
            print(f"   💾 内存缓存中找到标签页: {tab_id}")
            
            if await self._adapter.is_tab_valid(tab_id):
                await self._adapter.switch_to_tab(tab_id)
                print(f"   ✅ 内存缓存标签页有效，直接复用")
                return tab_id
            else:
                print(f"   ⚠️ 内存缓存标签页失效，清理缓存")
                del self._account_tabs[account_key]
        
        # 🔥 步骤2：检查浏览器中是否已有该账号的标签页
        if storage_state:
            existing_tab_id = await self._find_existing_tab_in_browser(storage_state)
            if existing_tab_id:
                print(f"   🔍 浏览器中找到现有标签页: {existing_tab_id}")
                
                # 验证标签页是否仍然有效
                if await self._adapter.is_tab_valid(existing_tab_id):
                    await self._adapter.switch_to_tab(existing_tab_id)
                    
                    # 更新内存缓存
                    self._account_tabs[account_key] = existing_tab_id
                    print(f"   ✅ 复用浏览器现有标签页并更新缓存")
                    
                    # 只在auto_navigate=True时检查登录状态
                    if auto_navigate:
                        current_url = await self._adapter.get_page_url(existing_tab_id)
                        login_indicators = ['login', 'signin', 'auth', '登录', '扫码']
                        needs_auth = any(indicator in current_url.lower() for indicator in login_indicators)
                        
                        if needs_auth:
                            print(f"   ⚠️ 现有标签页需要重新认证")
                            success = await self._handle_reauth_with_navigation(existing_tab_id, platform, storage_state)
                            if not success:
                                print(f"   ❌ 重新认证失败，关闭现有标签页创建新的")
                                await self._adapter.close_tab(existing_tab_id)
                                del self._account_tabs[account_key]
                                # 继续执行创建新标签页的逻辑
                            else:
                                return existing_tab_id
                        else:
                            return existing_tab_id
                    else:
                        # auto_navigate=False时，直接返回现有标签页
                        return existing_tab_id
                else:
                    print(f"   ⚠️ 浏览器现有标签页失效，将创建新的")
        
        # 🔥 步骤3：创建新标签页
        print(f"   🆕 创建新标签页（auto_navigate: {auto_navigate}）")
        
        if auto_navigate:
            initial_url = self.get_platform_initial_url(platform)
            tab_id = await self._adapter.get_or_create_account_tab(
                platform=platform,
                cookie_file=storage_state or "",
                initial_url=initial_url
            )
        else:
            tab_id = await self._create_blank_tab_with_cookies(platform, storage_state)
        
        # 更新内存缓存
        self._account_tabs[account_key] = tab_id
        print(f"   ✅ 新标签页创建完成: {tab_id}")
        
        return tab_id

    async def _find_existing_tab_in_browser(self, storage_state: str) -> str:
        """在浏览器中查找现有的账号标签页 - 使用适配器方法"""
        try:
            cookie_filename = Path(storage_state).name
            print(f"   🔍 在浏览器中查找 Cookie 文件: {cookie_filename}")
            
            # 🔥 使用 _adapter 的方法，不需要直接构造URL
            try:
                # 先获取所有标签页
                result = self._adapter._make_request('GET', '/accounts')
                
                if not result.get('success'):
                    print(f"   ❌ 无法获取标签页列表: {result.get('error')}")
                    return None
                
                tabs = result.get('data', [])
                print(f"   📋 浏览器中共有 {len(tabs)} 个标签页")
                
                # 查找匹配的标签页
                for tab in tabs:
                    if tab.get('cookieFile'):
                        tab_cookie_filename = Path(tab['cookieFile']).name
                        if tab_cookie_filename == cookie_filename:
                            tab_id = tab['id']
                            account_name = tab.get('accountName', 'unknown')
                            login_status = tab.get('loginStatus', 'unknown')
                            url = tab.get('url', 'unknown')
                            
                            print(f"   ✅ 找到现有标签页: {account_name} (ID: {tab_id}, 状态: {login_status})")
                            print(f"   📍 当前URL: {url}")
                            return tab_id
                
                print(f"   ❌ 浏览器中未找到对应的标签页")
                return None
                
            except Exception as api_error:
                print(f"   ❌ API 请求失败: {api_error}")
                return None
                
        except Exception as e:
            print(f"   ⚠️ 查找现有标签页时出错: {e}")
            return None

    async def _create_blank_tab_with_cookies(self, platform: str, storage_state: str) -> str:
        """创建空白标签页并加载cookies，但不导航"""
        
        # 生成临时标签页标识
        tab_identifier = f"temp_{platform}_{int(asyncio.get_event_loop().time() * 1000)}"
        
        # 创建空白标签页
        tab_id = await self._adapter.create_account_tab(
            platform=platform,
            account_name=tab_identifier,
            initial_url="about:blank"  # 空白页面
        )
        
        # 加载cookies（如果存在）
        if storage_state and Path(storage_state).exists():
            print(f"🍪 为空白标签页加载cookies: {Path(storage_state).name}")
            success = await self._adapter.load_cookies_only(tab_id, platform, storage_state)
            if success:
                print(f"✅ 空白标签页cookies加载成功")
            else:
                print(f"⚠️ 空白标签页cookies加载失败")
        
        return tab_id

    async def _handle_reauth_with_navigation(self, tab_id: str, platform: str, storage_state: str) -> bool:
        """处理重新认证 - 简化版本"""
        try:
            print(f"   🔄 重新加载cookies: {Path(storage_state).name}")
            
            # 直接使用load_cookies_only
            success = await self.load_cookies_only(tab_id, platform, storage_state)
            if not success:
                return False
            
            await asyncio.sleep(3)
            await self._adapter.refresh_page(tab_id)
            await asyncio.sleep(5)
            
            # 🔥 简化验证：只检查URL中是否还有登录标识
            current_url = await self._adapter.get_page_url(tab_id)
            login_indicators = ['login', 'signin', 'auth', '登录', '扫码']
            still_needs_auth = any(indicator in current_url.lower() for indicator in login_indicators)
            
            return not still_needs_auth
            
        except Exception as e:
            print(f"   ❌ 重新认证失败: {e}")
            return False
    
    async def save_account_state(self, storage_state: str, tab_id: str = None):
        """保存账号状态 - 🔥 统一参数名"""
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

class PlaywrightCompatContext:
    """兼容 Playwright Context API - 重新设计为标签页管理"""
    
    def __init__(self, storage_state: str = None):  # 🔥 修改：使用原生参数名
        # 🔥 统一类型处理：支持 str | Path | Dict，与原生 Playwright 一致
        if storage_state:
            if isinstance(storage_state, (str, Path)):
                self.storage_state_file = str(storage_state)  # 🔥 改名
            elif isinstance(storage_state, dict):
                self.storage_state_file = None
                print("⚠️ 兼容层暂不支持 dict 类型的 storage_state")
            else:
                self.storage_state_file = str(storage_state)
        else:
            self.storage_state_file = None  # 🔥 改名
        self.tab_manager = AccountTabManager.get_instance()
        self.current_tab_id = None
        self._init_scripts = []  # 存储初始化脚本
        self._cdp_browser = None  # 保存连接
        self._playwright_instance = None
        self._tab_page_map: Dict[str, any] = {}  # 🔥 tab_id -> Page 映射
        self._tracking_setup = False

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
        """创建新页面 - 修复版本，避免自动导航冲突"""
        
        print(f"\n🎯 Context.newPage() - 创建页面")
        
        # 🔥 关键修改：无论是否有 storage_state_file auto_navigate=False
        # 让应用层（如 tencent_uploader）完全控制导航时机
        if self.storage_state_file:
            print(f"📋 检测到 storage_state，创建空白页面让应用控制导航")
            print(f"   Cookie文件: {Path(self.storage_state_file).name}")
            
            # 使用 auto_navigate=False，只创建空白页面并加载cookies
            self.current_tab_id = await self.tab_manager.get_or_create_account_tab(
                storage_state=self.storage_state_file, 
                auto_navigate=False  # 🔥 关键：不自动导航
            )
        else:
            print(f"📋 无 storage_state，创建临时空白页面")
            self.current_tab_id = await self.tab_manager.create_temp_blank_tab()
        
        # 应用初始化脚本
        if self._init_scripts:
            print(f"📜 应用 {len(self._init_scripts)} 个初始化脚本")
            await self._apply_init_scripts_to_tab(self.current_tab_id)
        
        # 设置页面跟踪
        await self._setup_page_tracking()
        
        # 获取原生页面
        return await self._get_native_page_for_tab(self.current_tab_id)

    async def _setup_page_tracking(self):
        """设置页面跟踪"""
        if self._tracking_setup:
            return
            
        try:
            # 初始化 CDP 连接
            if self._cdp_browser is None:
                from playwright.async_api import async_playwright
                self._playwright_instance = async_playwright()
                pw = await self._playwright_instance.__aenter__()
                self._cdp_browser = await pw.chromium.connect_over_cdp('http://localhost:9712')
            
            # 🔥 监听页面创建事件
            contexts = self._cdp_browser.contexts
            if contexts and len(contexts) > 0:
                context = contexts[0]
                
                # 监听新页面创建
                context.on("page", lambda page: asyncio.create_task(self._register_page_with_tab_id(page)))
                
                # 🔥 处理现有页面
                for page in context.pages:
                    await self._register_page_with_tab_id(page)
            
            self._tracking_setup = True
            print("✅ 页面跟踪设置完成")
            
        except Exception as e:
            print(f"❌ 设置页面跟踪失败: {e}")
    
    async def _register_page_with_tab_id(self, page):
        """注册页面与 tab_id 的映射"""
        try:
            # 等待页面加载完成
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
            
            # 跳过系统页面
            if page.url.endswith('index.html'):
                return
            
            # 🔥 从页面中提取 tab_id
            tab_id = await page.evaluate("window.__TAB_ID__")
            
            if tab_id:
                self._tab_page_map[str(tab_id)] = page
                print(f"✅ 映射建立: {tab_id} -> {page.url}")
                
                # 🔥 监听页面关闭，清理映射
                page.on("close", lambda: self._cleanup_page_mapping(str(tab_id)))
            else:
                print(f"⚠️ 页面无 tab_id: {page.url}")
                
        except Exception as e:
            print(f"⚠️ 注册页面失败: {page.url}, {e}")
    
    def _cleanup_page_mapping(self, tab_id: str):
        """清理页面映射"""
        if tab_id in self._tab_page_map:
            del self._tab_page_map[tab_id]
            print(f"🗑️ 清理映射: {tab_id}")
    
    async def _get_native_page_for_tab(self, tab_id: str):
        """通过映射获取页面"""
        try:
            # 🔥 方法1：从映射中直接获取
            if tab_id in self._tab_page_map:
                page = self._tab_page_map[tab_id]
                print(f"✅ 从映射中找到页面: {tab_id} -> {page.url}")
                return page
            
            # 🔥 方法2：等待映射建立
            for i in range(10):  # 最多等待5秒
                await asyncio.sleep(0.5)
                if tab_id in self._tab_page_map:
                    page = self._tab_page_map[tab_id]
                    print(f"✅ 等待后找到页面: {tab_id} -> {page.url}")
                    return page
            
            # 🔥 方法3：主动查找并建立映射
            await self._force_rebuild_mapping()
            
            if tab_id in self._tab_page_map:
                page = self._tab_page_map[tab_id]
                print(f"✅ 重建映射后找到页面: {tab_id} -> {page.url}")
                return page
            
            raise Exception(f"无法找到 tab_id 对应的页面: {tab_id}")
            
        except Exception as e:
            print(f"❌ 获取页面失败: {e}")
            raise
    
    async def _force_rebuild_mapping(self):
        """强制重建映射"""
        try:
            contexts = self._cdp_browser.contexts
            if contexts and len(contexts) > 0:
                pages = contexts[0].pages
                
                print(f"🔄 重建映射，检查 {len(pages)} 个页面")
                
                for page in pages:
                    if not page.url.endswith('index.html'):
                        try:
                            tab_id = await page.evaluate("window.__TAB_ID__")
                            if tab_id:
                                self._tab_page_map[str(tab_id)] = page
                                print(f"🔄 重建映射: {tab_id} -> {page.url}")
                        except:
                            continue
                            
        except Exception as e:
            print(f"❌ 重建映射失败: {e}")

    async def _get_native_page_for_tab(self, tab_id):
        """获取指定标签页的原生页面"""
        try:
            # 🔥 如果没有连接，创建连接
            if self._cdp_browser is None:
                from playwright.async_api import async_playwright
                self._playwright_instance = async_playwright()
                pw = await self._playwright_instance.__aenter__()
                self._cdp_browser = await pw.chromium.connect_over_cdp('http://localhost:9712')
                print("✅ CDP 连接已建立")
            
            # 🔥 通过 API 获取指定 tab 的 URL，然后匹配页面
            import requests
            response = requests.get(f'http://localhost:3000/api/account/{tab_id}')
            if response.status_code == 200:
                tab_info = response.json()['data']
                tab_url = tab_info.get('url', 'about:blank')
                
                # 在所有页面中查找匹配的页面
                contexts = self._cdp_browser.contexts
                if contexts and len(contexts) > 0:
                    pages = contexts[0].pages
                    
                    print(f"🔍 查找标签页 {tab_id} 对应的页面:")
                    print(f"   目标 URL: {tab_url}")
                    
                    for i, page in enumerate(pages):
                        page_url = page.url
                        print(f"   页面 {i}: {page_url}")
                        
                        # 🔥 匹配逻辑：about:blank 或 URL 包含关键部分
                        if (tab_url == 'about:blank' and page_url == 'about:blank') or \
                           (tab_url != 'about:blank' and tab_url in page_url):
                            print(f"✅ 找到匹配页面: {page_url}")
                            return page
                    
                    # 如果没找到精确匹配，返回最后创建的页面（通常是我们想要的）
                    if pages:
                        page = pages[-1]
                        print(f"⚠️ 使用最新页面: {page.url}")
                        return page
            
            raise Exception(f"无法找到标签页 {tab_id} 对应的页面")
            
        except Exception as e:
            print(f"❌ 获取原生页面失败: {e}")
            raise
    
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
        if path and self.current_tab_id:
            await self.tab_manager.save_account_state(path, self.current_tab_id)
        return {}

    async def close(self):
        """关闭 CDP 连接"""
        if self._playwright_instance:
            try:
                await self._playwright_instance.__aexit__(None, None, None)
                print("✅ CDP 连接已关闭")
            except:
                pass
            self._cdp_browser = None
            self._playwright_instance = None
        if self.storage_state_file and self.current_tab_id:
            await self.tab_manager.save_account_state(self.storage_state_file, self.current_tab_id)
        

class PlaywrightCompatBrowser:
    """兼容 Playwright Browser API - 简化为标签页工厂"""
    
    def __init__(self):
        from utils.playwright_compat import get_account_tab_manager
        self.tab_manager = get_account_tab_manager()
        self._contexts = []
        print(f"🚀 浏览器实例创建完成 (multi-account-browser 模式)")
    
    async def new_context(self, storage_state=None, **kwargs) -> 'PlaywrightCompatContext':
        """
        创建新上下文 - 🔥 与原生 Playwright 完全兼容
        
        Args:
            storage_state: str | Path | Dict | None - 与原生 Playwright 一致
                - str/Path: cookie 文件路径
                - Dict: storage state 对象（暂不支持）
                - None: 无状态
        """
        print(f"\n🎯 Browser.new_context() - 准备账号上下文")
        print(f"   storage_state: {storage_state}")
        print(f"   storage_state 类型: {type(storage_state)}")
        
        context = PlaywrightCompatContext(storage_state)
        self._contexts.append(context)
        return context
    
    async def close(self) -> None:
        """浏览器关闭 - 空操作，浏览器由外部管理"""
        print(f"📝 Browser.close() - 浏览器实例保留")


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

import sqlite3
import time
from pathlib import Path
from typing import Optional, Dict, Any
import asyncio
import requests

class MultiAccountBrowserAdapter:
    """multi-account-browser API 适配层 - 通用UUID标识"""
    
    def __init__(self, api_base_url: str = "http://localhost:3000/api"):
        self.api_base_url = api_base_url
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.account_tabs: Dict[str, str] = {}  # account_file_path -> tab_id
        self.db_path = None
        print(f"🐛 MultiAccountBrowserAdapter.__init__: db_path = {self.db_path}")
    def set_database_path(self, db_path: str):
        """设置数据库路径"""
        self.db_path = db_path

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
                        'platform': platform_map.get(platform_type, 'unknown'),
                        'platform_type': platform_type
                    }
                return None
        except Exception as e:
            print(f"⚠️ 获取账号信息失败: {e}")
            return None

    def generate_tab_identifier(self, platform: str, cookie_file: str) -> str:
        """生成内部标签页标识符（包含UUID） - 后端使用"""
        cookie_stem = Path(cookie_file).stem  # UUID部分
        platform_prefix_map = {
            'weixin': 'wx', 
            'douyin': 'dy', 
            'xiaohongshu': 'xhs', 
            'kuaishou': 'ks'
        }
        platform_prefix = platform_prefix_map.get(platform, platform[:3])
        
        # 内部标识符格式：wx_a7342fe8-5ff6-11f0-b1ab-a45e60e0141b
        return f"{platform_prefix}_{cookie_stem}"

    def generate_display_name(self, platform: str, cookie_file: str) -> str:
        """生成用户友好的显示名称（不包含UUID） - 前端显示"""
        account_info = self.get_account_info_from_db(cookie_file)
        
        if account_info and account_info.get('username'):
            username = account_info['username']
            platform_name_map = {
                'weixin': '视频号', 
                'douyin': '抖音', 
                'xiaohongshu': '小红书', 
                'kuaishou': '快手'
            }
            platform_name = platform_name_map.get(platform, platform)
            # 用户友好格式：视频号_endian
            return f"{platform_name}_{username}"
        
        # 备选：使用UUID的前8位
        uuid_short = Path(cookie_file).stem.split('-')[0] if '-' in Path(cookie_file).stem else Path(cookie_file).stem[:8]
        platform_name_map = {
            'weixin': '视频号', 
            'douyin': '抖音', 
            'xiaohongshu': '小红书', 
            'kuaishou': '快手'
        }
        platform_name = platform_name_map.get(platform, platform)
        return f"{platform_name}_{uuid_short}"

    async def get_or_create_account_tab(self, platform: str, cookie_file: str, initial_url: str) -> str:
        """获取或创建账号标签页 - 增强版本"""
        
        # 生成标识符和显示名
        tab_identifier = self.generate_tab_identifier(platform, cookie_file)
        display_name = self.generate_display_name(platform, cookie_file)
        
        # 使用cookie文件绝对路径作为映射键
        account_key = str(Path(cookie_file).absolute())
        
        print(f"🔍 查找账号标签页:")
        print(f"    平台: {platform}")
        print(f"    显示名: {display_name}")
        print(f"    内部标识: {tab_identifier}")
        print(f"    Cookie文件: {Path(cookie_file).name}")
        
        # 🔥 步骤1：检查 multi-account-browser 中的现有标签页
        try:
            result = self._make_request('GET', '/accounts')
            if result.get('success'):
                existing_tabs = result.get('data', [])
                
                # 🔥 改进：支持多种匹配方式
                cookie_filename = Path(cookie_file).name
                for tab in existing_tabs:
                    is_match = False
                    
                    # 方式1: 通过 cookieFile 精确匹配
                    if tab.get('cookieFile') and Path(tab['cookieFile']).name == cookie_filename:
                        is_match = True
                        print(f"🎯 通过 cookieFile 匹配到标签页: {tab['accountName']}")
                    
                    # 方式2: 通过账号名称匹配（备用）
                    elif tab.get('accountName') == tab_identifier:
                        is_match = True
                        print(f"🎯 通过 accountName 匹配到标签页: {tab['accountName']}")
                    
                    # 方式3: 通过平台和部分UUID匹配（容错）
                    elif platform in tab.get('accountName', '') and cookie_filename.split('.')[0] in tab.get('accountName', ''):
                        is_match = True
                        print(f"🎯 通过平台+UUID匹配到标签页: {tab['accountName']}")
                    
                    if is_match:
                        tab_id = tab['id']
                        print(f"🔄 发现现有标签页: {tab['accountName']} (ID: {tab_id})")
                        
                        # 验证标签页是否仍然有效
                        if await self.is_tab_valid(tab_id):
                            print(f"✅ 现有标签页有效，开始验证登录状态...")
                            
                            # 🔥 验证 cookies 状态
                            login_valid = await self.verify_login_status(tab_id, platform)
                            
                            if login_valid:
                                print(f"✅ 账号登录状态有效，直接复用标签页")
                                await self.switch_to_tab(tab_id)
                                self.account_tabs[account_key] = tab_id
                                return tab_id
                            else:
                                print(f"⚠️ 账号登录状态失效，重新加载cookies...")
                                # 重新加载cookies
                                success = await self.load_cookies_with_verification(tab_id, platform, cookie_file)
                                if success:
                                    print(f"✅ Cookies重新加载成功，复用标签页")
                                    await self.switch_to_tab(tab_id)
                                    self.account_tabs[account_key] = tab_id
                                    return tab_id
                                else:
                                    print(f"❌ Cookies重新加载失败，关闭旧标签页")
                                    await self.close_tab(tab_id)
                        else:
                            print(f"⚠️ 现有标签页无效，关闭并重新创建")
                            await self.close_tab(tab_id)
                        
                        break  # 找到匹配项就跳出循环
                        
        except Exception as e:
            print(f"⚠️ 检查现有标签页失败: {e}")
        
        # 🔥 步骤2：创建新的标签页
        print(f"🆕 为账号创建新的标签页: {display_name}")
        tab_id = await self.create_account_tab(platform, tab_identifier, initial_url)
        # 🔥 步骤3：加载cookies（如果存在）
        if cookie_file and Path(cookie_file).exists():
            print(f"🍪 为新标签页加载cookies: {Path(cookie_file).name}")
            print(f"🔍 Cookie文件大小: {Path(cookie_file).stat().st_size} 字节")
            
            success = await self.load_cookies_with_verification(tab_id, platform, cookie_file)
            if success:
                print(f"✅ 新标签页cookies加载并验证成功")
            else:
                print(f"⚠️ 新标签页cookies加载失败，但继续使用标签页")
                # 🔥 增加：获取当前页面状态用于调试
                try:
                    current_url = await self.get_page_url(tab_id)
                    page_title = await self.execute_script(tab_id, "document.title")
                    print(f"🔍 当前页面状态: {current_url}")
                    print(f"🔍 页面标题: {page_title}")
                except Exception as e:
                    print(f"🔍 无法获取页面状态: {e}")
        
        # 🔥 步骤4：保存账号映射
        self.account_tabs[account_key] = tab_id
        print(f"📋 账号标签页映射已保存: {display_name} -> {tab_id}")
        
        return tab_id


    async def check_if_needs_reauth(self, platform: str, current_url: str) -> bool:
        """检查是否需要重新认证 - 支持多平台"""
        # 通用的登录页面检测逻辑
        login_indicators = ['login', 'signin', 'auth', '登录', '扫码']
        
        # 检查URL是否包含登录相关关键词
        url_needs_auth = any(indicator in current_url.lower() for indicator in login_indicators)
        
        if url_needs_auth:
            return True
        
        # 平台特定的检测逻辑
        platform_specific_checks = {
            'weixin': lambda url: 'login.html' in url or 'channels.weixin.qq.com/login' in url,
            'douyin': lambda url: 'login' in url or 'sso.douyin.com' in url,
            'xiaohongshu': lambda url: 'login' in url or 'xiaohongshu.com/login' in url,
            'kuaishou': lambda url: 'login' in url or 'kuaishou.com/login' in url
        }
        
        platform_check = platform_specific_checks.get(platform)
        if platform_check and platform_check(current_url):
            return True
        
        return False

    async def handle_reauth(self, tab_id: str, platform: str, cookie_file: str, initial_url: str) -> bool:
        """通用的重新认证处理"""
        try:
            print(f"🔄 开始重新认证: {tab_id}")
            
            # 方案1: 重新加载cookies
            print("    尝试重新加载cookies...")
            success = await self.load_cookies_with_verification(tab_id, platform, cookie_file)
            if success:
                print("    ✅ cookies重新加载成功")
                return True
            
            # 方案2: 导航到首页再重新加载
            print("    尝试导航到首页重新加载...")
            
            # 根据平台选择合适的首页
            platform_home_urls = {
                'weixin': 'https://channels.weixin.qq.com',
                'douyin': 'https://creator.douyin.com',
                'xiaohongshu': 'https://creator.xiaohongshu.com',
                'kuaishou': 'https://cp.kuaishou.com'
            }
            
            home_url = platform_home_urls.get(platform, initial_url)
            await self.navigate_to_url(tab_id, home_url)
            await asyncio.sleep(3)
            
            # 重新加载cookies
            await self.load_cookies(tab_id, cookie_file)
            await asyncio.sleep(3)
            
            # 刷新页面
            await self.refresh_page(tab_id)
            await asyncio.sleep(5)
            
            # 检查结果
            current_url = await self.get_page_url(tab_id)
            needs_auth = await self.check_if_needs_reauth(platform, current_url)
            
            if not needs_auth:
                print("    ✅ 第二次尝试成功")
                return True
            else:
                print("    ❌ 重新认证仍然失败")
                return False
                
        except Exception as e:
            print(f"    ❌ 重新认证过程出错: {e}")
            return False

    async def load_cookies_with_verification(self, tab_id: str, platform: str, cookie_file: str) -> bool:
        cookie_file_str = str(cookie_file) if cookie_file else ""
        
        if not Path(cookie_file_str).exists():
            print(f"⚠️ Cookie文件不存在: {cookie_file_str}")
            return False
        
        print(f"🍪 开始加载并验证cookies: {Path(cookie_file_str).name}")
        
        # 1. 加载cookies
        result = self._make_request('POST', '/account/load-cookies', {
            "tabId": tab_id,
            "cookieFile": cookie_file_str
        })
        
        if not result.get("success", False):
            print(f"❌ Cookies加载失败: {result.get('error')}")
            return False
        
        print(f"🍪 Cookies文件加载成功，开始导航到主页...")
        
        # 🔥 关键修改：不要刷新当前页面，而是导航到平台主页
        platform_home_urls = {
            'weixin': 'https://channels.weixin.qq.com/platform',  # 使用平台主页而不是根目录
            'douyin': 'https://creator.douyin.com/creator-micro/content/upload',
            'xiaohongshu': 'https://creator.xiaohongshu.com/creator-micro/content/upload',
            'kuaishou': 'https://cp.kuaishou.com/article/publish/video'
        }
        
        target_url = platform_home_urls.get(platform, 'https://channels.weixin.qq.com/platform')
        
        # 2. 导航到目标页面
        await self.navigate_to_url(tab_id, target_url)
        await asyncio.sleep(5)  # 给页面足够时间加载
        
        # 3. 验证cookies是否生效
        max_retries = 2  # 减少重试次数
        for i in range(max_retries):
            try:
                current_url = await self.get_page_url(tab_id)
                print(f"验证第{i+1}次，当前URL: {current_url}")
                
                # 🔥 优化：检查URL是否不再包含登录标识
                needs_auth = self._is_login_url(current_url)
                
                if not needs_auth:
                    print(f"✅ Cookies验证成功: {Path(cookie_file).name}")
                    return True
                    
                # 如果仍需要认证，等待一下再检查
                if i < max_retries - 1:
                    print(f"第{i+1}次验证失败，等待页面完全加载...")
                    await asyncio.sleep(3)
                        
            except Exception as e:
                print(f"验证过程出错: {e}")
        
        print(f"❌ Cookies验证失败: {Path(cookie_file).name}")
        return False

    def _is_login_url(self, url: str) -> bool:
        """检查URL是否是登录页面"""
        login_indicators = [
            'login.html', 'login', 'signin', 'auth', 
            '登录', '扫码', 'qrcode', 'scan'
        ]
        return any(indicator in url.lower() for indicator in login_indicators)

    def debug_print_account_mapping(self):
        """调试：打印当前的账号映射"""
        print("\n" + "="*60)
        print("📊 当前账号标签页映射:")
        print("="*60)
        
        for account_file, tab_id in self.account_tabs.items():
            cookie_name = Path(account_file).name
            display_name = self.generate_display_name("unknown", account_file)
            print(f"显示名: {display_name}")
            print(f"Cookie文件: {cookie_name}")
            print(f"标签页ID: {tab_id}")
            print("-" * 40)
        
        print(f"总计: {len(self.account_tabs)} 个账号映射")
        print("="*60 + "\n")

    # ========================================
    # 基础API方法（保持不变）
    # ========================================
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """统一的API请求方法"""
        url = f"{self.api_base_url}{endpoint}"
        
        try:
            timeout = 120 if '/set-file' in endpoint else 60
            
            if method.upper() == 'GET':
                response = self.session.get(url, timeout=timeout)
            else:
                response = self.session.post(url, json=data, timeout=timeout)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.ConnectionError as e:
            raise Exception(f"连接失败: 请确保 multi-account-browser 正在运行")
        except requests.exceptions.Timeout as e:
            raise Exception(f"请求超时: {e}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"API请求失败: {e}")
    
    async def create_account_tab(self, platform: str, account_name: str, initial_url: str) -> str:
        """创建账号标签页"""
        print(f"🚀 创建标签页: {account_name} ({platform}) -> {initial_url}")
        
        result = self._make_request('POST', '/account/create', {
            "accountName": account_name,
            "platform": platform,
            "initialUrl": initial_url
        })
        
        if result.get("success"):
            tab_id = result["data"]["tabId"]
            print(f"✅ 标签页创建成功: {tab_id}")
            await asyncio.sleep(3)
            return tab_id
        else:
            raise Exception(f"创建标签页失败: {result.get('error')}")
    
    async def switch_to_tab(self, tab_id: str) -> bool:
        """切换到指定标签页"""
        result = self._make_request('POST', '/account/switch', {"tabId": tab_id})
        success = result.get("success", False)
        if success:
            print(f"🔄 切换到标签页: {tab_id}")
        return success
    
    async def is_tab_valid(self, tab_id: str) -> bool:
        """检查标签页是否仍然有效"""
        try:
            result = await self.execute_script(tab_id, "window.location.href")
            return bool(result)
        except:
            return False
    
    async def execute_script(self, tab_id: str, script: str) -> Any:
        """在指定标签页执行脚本"""
        result = self._make_request('POST', '/account/execute', {
            "tabId": tab_id, 
            "script": script
        })
        
        if result.get("success"):
            return result.get("data")
        else:
            raise Exception(f"脚本执行失败: {result.get('error')}")
    
    async def navigate_to_url(self, tab_id: str, url: str) -> bool:
        """导航到指定URL"""
        result = self._make_request('POST', '/account/navigate', {
            "tabId": tab_id,
            "url": url
        })
        
        if result.get("success"):
            await asyncio.sleep(5)
            return True
        else:
            raise Exception(f"导航失败: {result.get('error')}")
    
    async def load_cookies(self, tab_id: str, cookie_file: str) -> bool:
        """加载 cookies"""
        cookie_file_str = str(cookie_file) if cookie_file else ""
        
        if not Path(cookie_file_str).exists():
            print(f"⚠️ Cookie文件不存在: {cookie_file_str}")
            return False
        
        result = self._make_request('POST', '/account/load-cookies', {
            "tabId": tab_id,
            "cookieFile": cookie_file_str  # 使用字符串而不是 Path 对象
        })
        
        success = result.get("success", False)
        if success:
            print(f"💾 Cookies加载成功: {cookie_file_str}")
            await asyncio.sleep(1)
        return success
    
    async def save_cookies(self, tab_id: str, cookie_file: str) -> bool:
        """保存 cookies"""
        # 确保 cookie_file 是字符串
        cookie_file_str = str(cookie_file) if cookie_file else ""
        
        if not Path(cookie_file_str).parent.exists():
            Path(cookie_file_str).parent.mkdir(parents=True, exist_ok=True)
        
        result = self._make_request('POST', '/account/save-cookies', {
            "tabId": tab_id,
            "cookieFile": cookie_file_str  # 使用字符串而不是 Path 对象
        })
        
        success = result.get("success", False)
        if success:
            print(f"💾 Cookies保存成功: {cookie_file_str}")
        return success
    
    async def close_tab(self, tab_id: str) -> bool:
        """关闭标签页"""
        result = self._make_request('POST', '/account/close', {"tabId": tab_id})
        success = result.get("success", False)
        if success:
            print(f"🗑️ 标签页已关闭: {tab_id}")
        return success
    
    async def refresh_page(self, tab_id: str) -> bool:
        """刷新页面"""
        result = self._make_request('POST', '/account/refresh', {"tabId": tab_id})
        return result.get("success", False)
    
    async def get_page_url(self, tab_id: str) -> str:
        """获取当前页面URL"""
        url_script = "window.location.href"
        try:
            url = await self.execute_script(tab_id, url_script)
            return str(url) if url else ""
        except:
            return ""
    
    async def wait_for_login_completion(self, tab_id: str, account_name: str, timeout: int = 300) -> bool:
        """等待用户登录完成"""
        print(f"⏳ 等待用户登录 {account_name}，最多等待 {timeout} 秒...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                current_url = await self.get_page_url(tab_id)
                
                # 简单检查：如果不在登录页面，认为已登录
                if 'login' not in current_url.lower():
                    print(f"✅ 检测到 {account_name} 已登录!")
                    return True
                
                await asyncio.sleep(5)  # 每5秒检查一次
                
                # 每30秒提示一次
                elapsed = int(time.time() - start_time)
                if elapsed % 30 == 0 and elapsed > 0:
                    print(f"⏳ 仍在等待 {account_name} 登录... ({elapsed}/{timeout}秒)")
                    
            except Exception as e:
                print(f"⚠️ 检查登录状态时出错: {e}")
                await asyncio.sleep(5)
        
        print(f"⏱️ 等待 {account_name} 登录超时")
        return False
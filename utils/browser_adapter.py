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

    async def load_cookies_only(self, tab_id: str, platform: str, cookie_file: str) -> bool:
        """仅加载cookies，不进行导航验证"""
        cookie_file_str = str(cookie_file) if cookie_file else ""
        
        if not Path(cookie_file_str).exists():
            print(f"⚠️ Cookie文件不存在: {cookie_file_str}")
            return False
        
        print(f"🍪 仅加载cookies（不导航验证）: {Path(cookie_file_str).name}")
        
        # 加载cookies
        result = self._make_request('POST', '/account/load-cookies', {
            "tabId": tab_id,
            "cookieFile": cookie_file_str
        })
        
        if not result.get("success", False):
            print(f"❌ Cookies加载失败: {result.get('error')}")
            return False
        
        print(f"✅ Cookies已加载，等待应用自行导航")
        return True
    
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

    async def get_or_create_account_tab(self, storage_state: str = None, auto_navigate: bool = True) -> str:
        """获取或创建账号标签页"""
        account_key = self.generate_account_key(storage_state)
        platform = self.infer_platform_from_storage(storage_state)
        
        print(f"\n🎯 获取或创建账号标签页:")
        print(f"   账号标识: {account_key}")
        print(f"   平台: {platform}")
        print(f"   自动导航: {auto_navigate}")
        
        # 检查现有标签页
        if account_key in self._account_tabs:
            tab_id = self._account_tabs[account_key]
            print(f"   发现现有标签页: {tab_id}")
            
            if await self._adapter.is_tab_valid(tab_id):
                await self._adapter.switch_to_tab(tab_id)
                
                # 🔥 只在auto_navigate=True时才检查和处理登录状态
                if auto_navigate and storage_state:
                    current_url = await self._adapter.get_page_url(tab_id)
                    login_indicators = ['login', 'signin', 'auth', '登录', '扫码']
                    needs_auth = any(indicator in current_url.lower() for indicator in login_indicators)
                    
                    if needs_auth:
                        print(f"   ⚠️ 需要重新认证")
                        success = await self._handle_reauth_with_navigation(tab_id, platform, storage_state)
                        if not success:
                            print(f"   ❌ 重新认证失败，创建新标签页")
                            await self._adapter.close_tab(tab_id)
                            del self._account_tabs[account_key]
                            return await self.get_or_create_account_tab(storage_state, auto_navigate)
                
                return tab_id
            else:
                del self._account_tabs[account_key]
        
        # 创建新标签页
        if auto_navigate:
            # 完整的导航验证模式
            initial_url = self.get_platform_initial_url(platform)
            tab_id = await self._adapter.get_or_create_account_tab(
                platform=platform,
                cookie_file=storage_state or "",
                initial_url=initial_url
            )
        else:
            # 🔥 新的空白模式
            tab_id = await self._create_blank_tab_with_cookies(platform, storage_state)
        
        self._account_tabs[account_key] = tab_id
        return tab_id


    async def create_temp_blank_tab(self) -> str:
        """创建临时空白标签页（用于无storage_state的情况）"""
        return await self._adapter.create_account_tab("temp", "temp_blank", "about:blank")

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
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, timeout: int = 60) -> Dict[str, Any]:
        """统一的API请求方法"""
        url = f"{self.api_base_url}{endpoint}"
        
        try:
            # 使用传入的 timeout 参数
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
        """在指定标签页执行脚本 - 添加健壮的错误处理"""
        max_retries = 3
        base_wait = 1
        
        for attempt in range(max_retries):
            try:
                # 🔥 在每次执行前稍微等待，避免过于频繁的请求
                if attempt > 0:
                    wait_time = base_wait * (2 ** (attempt - 1))
                    print(f"⏳ [{tab_id}] 等待 {wait_time}s 后重试脚本执行...")
                    import asyncio
                    await asyncio.sleep(wait_time)
                
                result = self._make_request('POST', '/account/execute', {
                    "tabId": tab_id, 
                    "script": script
                })
                
                if result.get("success"):
                    return result.get("data")
                else:
                    error_msg = result.get("error", "Unknown error")
                    print(f"❌ [{tab_id}] 脚本执行失败: {error_msg}")
                    
                    # 🔥 检查是否是严重错误（渲染器崩溃）
                    if "renderer console" in error_msg.lower() or "script failed to execute" in error_msg.lower():
                        print(f"🚨 [{tab_id}] 检测到渲染器错误，尝试恢复...")
                        
                        # 尝试恢复：刷新页面
                        try:
                            await self._try_recovery(tab_id)
                        except Exception as recovery_error:
                            print(f"⚠️ [{tab_id}] 恢复失败: {recovery_error}")
                    
                    if attempt < max_retries - 1:
                        continue
                    else:
                        raise Exception(f"脚本执行失败 (重试{max_retries}次): {error_msg}")
                        
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ [{tab_id}] 执行异常 (第{attempt+1}次): {e}")
                    continue
                else:
                    raise Exception(f"脚本执行失败 (重试{max_retries}次): {e}")

    async def _try_recovery(self, tab_id: str) -> None:
        """尝试恢复标签页"""
        try:
            import asyncio
            
            print(f"🔄 [{tab_id}] 尝试恢复标签页...")
            
            # 方法1: 简单等待，让页面稳定
            await asyncio.sleep(3)
            
            # 方法2: 尝试执行一个简单的脚本测试页面是否响应
            test_result = self._make_request('POST', '/account/execute', {
                "tabId": tab_id,
                "script": "document.readyState"
            })
            
            if test_result.get("success"):
                print(f"✅ [{tab_id}] 页面恢复正常")
            else:
                print(f"⚠️ [{tab_id}] 页面仍然异常，可能需要重新加载")
                
        except Exception as e:
            print(f"❌ [{tab_id}] 恢复过程出错: {e}")
            raise
    
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
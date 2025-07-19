# utils/browser_adapter.py
import requests
from typing import Optional, Dict, Any
import os
from pathlib import Path
from urllib.parse import urlparse
#import hashlib


class MultiAccountBrowserAdapter:
    
    def __init__(self, api_base_url: str = "http://localhost:3000/api"):
        self.api_base_url = api_base_url
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, timeout: int = 60) -> Dict[str, Any]:
        """统一的API请求方法"""
        url = f"{self.api_base_url}{endpoint}"
        
        try:
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
    
    async def get_qr_code(self, tab_id: str, selector: str) -> Optional[str]:
        """获取页面中的二维码图片URL"""
        result = self._make_request('POST', '/account/get-qrcode', {
            "tabId": tab_id, "selector": selector
        })
        return result["data"]["qrUrl"] if result.get("success") else None

    async def wait_for_url_change(self, tab_id: str, timeout: int = 200000) -> bool:
        """等待页面URL变化"""
        result = self._make_request('POST', '/account/wait-url-change', {
            "tabId": tab_id, "timeout": timeout
        }, timeout=timeout//1000 + 10)
        return result.get("data", {}).get("urlChanged", False)
    
    def extract_page_elements(self, tab_id: str, selectors: dict) -> dict:
        """通用页面元素提取"""
        result = self._make_request('POST', '/account/extract-elements', {
            "tabId": tab_id,
            "selectors": selectors
        })
        return result.get("data", {}) if result.get("success") else {}

    def get_account_info(self, tab_id: str, platform: str) -> dict:
        """获取账号信息"""
        result = self._make_request('POST', '/account/get-info', {
            "tabId": tab_id,
            "platform": platform
        })
        return result.get("data", {}) if result.get("success") else {}

    def get_platform_selectors(self, platform: str) -> dict:
        """获取平台选择器配置（调试用）"""
        result = self._make_request('GET', f'/account/platform-selectors/{platform}')
        return result.get("data", {}) if result.get("success") else {}

    def download_avatar(self, avatar_url: str, platform: str, account_name: str, account_id: str = None) -> str:
        """下载用户头像到本地"""
        if not avatar_url or not avatar_url.startswith('http'):
            return None
        
        try:
            # 创建头像存储目录结构：platform/accountName_accountId/
            safe_account_name = "".join(c for c in account_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_account_id = "".join(c for c in (account_id or '')) if account_id else ''
            
            if safe_account_id:
                folder_name = f"{safe_account_name}_{safe_account_id}"
            else:
                folder_name = safe_account_name
                
            avatar_dir = Path("sau_frontend/src/assets/avatar") / platform / folder_name
            avatar_dir.mkdir(parents=True, exist_ok=True)
            
            # 获取文件扩展名
            parsed_url = urlparse(avatar_url)
            file_ext = os.path.splitext(parsed_url.path)[1] or '.jpg'
            
            # 生成文件名：avatar + 扩展名
            avatar_filename = f"avatar{file_ext}"
            avatar_path = avatar_dir / avatar_filename
            
            # 下载头像
            response = requests.get(avatar_url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            # 保存文件
            with open(avatar_path, 'wb') as f:
                f.write(response.content)
            
            # 返回相对路径（前端可用）
            relative_path = f"assets/avatar/{platform}/{folder_name}/{avatar_filename}"
            print(f"✅ 头像已保存: {relative_path}")
            return relative_path
            
        except Exception as e:
            print(f"❌ 头像下载失败: {e}")
            return None
    
    def get_account_info_with_avatar(self, tab_id: str, platform: str, base_dir: str) -> dict:
        """🔥 获取账号信息并下载头像（仅数据获取，不保存数据库）"""
        try:
            # 获取账号信息
            account_info = self.get_account_info(tab_id, platform)
            
            if not account_info or not account_info.get('accountName'):
                print("⚠️ 未获取到账号信息")
                return None
            
            # 下载头像
            avatar_url = account_info.get('avatar')
            if avatar_url:
                original_cwd = os.getcwd()
                try:
                    os.chdir(base_dir)
                    local_avatar_path = self.download_avatar(
                        avatar_url, 
                        platform, 
                        account_info.get('accountName'),
                        account_info.get('accountId')
                    )
                    account_info['localAvatar'] = local_avatar_path
                except Exception as e:
                    print(f"❌ 头像下载失败: {e}")
                    account_info['localAvatar'] = None
                finally:
                    os.chdir(original_cwd)
            else:
                account_info['localAvatar'] = None
            
            print(f"✅ 账号信息获取成功: {account_info.get('accountName')} (粉丝: {account_info.get('followersCount')})")
            return account_info
            
        except Exception as e:
            print(f"❌ 获取账号信息异常: {e}")
            return None
    # 标签页基础操作
    async def create_account_tab(self, account_name: str, platform: str, initial_url: str) -> str:
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

    async def close_tab(self, tab_id: str) -> bool:
        """关闭标签页"""
        result = self._make_request('POST', '/account/close', {"tabId": tab_id})
        success = result.get("success", False)
        if success:
            print(f"🗑️ 标签页已关闭: {tab_id}")
        return success

    async def navigate_tab(self, tab_id: str, url: str) -> bool:
        """导航到指定URL"""
        result = self._make_request('POST', '/account/navigate', {
            "tabId": tab_id,
            "url": url
        })
        
        if result.get("success"):
            return True
        else:
            raise Exception(f"导航失败: {result.get('error')}")

    async def refresh_tab(self, tab_id: str) -> bool:
        """刷新页面"""
        result = self._make_request('POST', '/account/refresh', {"tabId": tab_id})
        return result.get("success", False)

    # 脚本执行
    async def execute_script(self, tab_id: str, script: str) -> Any:
        """在指定标签页执行脚本"""
        result = self._make_request('POST', '/account/execute', {
            "tabId": tab_id, 
            "script": script
        })
        
        if result.get("success"):
            return result.get("data")
        else:
            error_msg = result.get("error", "Unknown error")
            raise Exception(f"脚本执行失败: {error_msg}")

    # Cookie 管理
    async def load_cookies(self, tab_id: str, cookie_file: str) -> bool:
        """加载 cookies"""
        result = self._make_request('POST', '/account/load-cookies', {
            "tabId": tab_id,
            "cookieFile": str(cookie_file)
        })
        
        success = result.get("success", False)
        if success:
            print(f"💾 Cookies加载成功: {cookie_file}")
        return success

    async def save_cookies(self, tab_id: str, cookie_file: str) -> bool:
        """保存 cookies"""
        result = self._make_request('POST', '/account/save-cookies', {
            "tabId": tab_id,
            "cookieFile": str(cookie_file)
        })
        
        success = result.get("success", False)
        if success:
            print(f"💾 Cookies保存成功: {cookie_file}")
        return success

    # 文件上传
    async def upload_file(self, tab_id: str, selector: str, file_path: str, options: Optional[Dict] = None) -> bool:
        """统一文件上传入口 - 使用流式上传"""
        result = self._make_request('POST', '/account/set-files-streaming-v2', {
            "tabId": tab_id,
            "selector": selector,
            "filePath": str(file_path),
            "options": options or {}
        })
        return result.get("success", False)

    # 状态查询
    async def get_all_tabs(self) -> Dict:
        """获取所有标签页"""
        return self._make_request('GET', '/accounts')

    async def get_tab_status(self, tab_id: str) -> Dict:
        """获取标签页状态"""
        return self._make_request('GET', f'/account/{tab_id}/status')

    async def get_page_url(self, tab_id: str) -> str:
        """获取当前页面URL"""
        try:
            url = await self.execute_script(tab_id, "window.location.href")
            return str(url) if url else ""
        except:
            return ""

    async def is_tab_valid(self, tab_id: str) -> bool:
        """检查标签页是否仍然有效"""
        try:
            result = await self.execute_script(tab_id, "window.location.href")
            return bool(result)
        except:
            return False
# utils/browser_adapter.py
import requests
from typing import Optional, Dict, Any

class MultiAccountBrowserAdapter:
    """Multi-Account-Browser API 适配层 - 精简版"""
    
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
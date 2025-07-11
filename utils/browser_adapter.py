import requests
import asyncio
import time
import json
from typing import Optional, Dict, Any, List
from pathlib import Path

class MultiAccountBrowserAdapter:
    """multi-account-browser API 适配层"""
    
    def __init__(self, api_base_url: str = "http://localhost:3000/api"):
        self.api_base_url = api_base_url
        self.created_tabs: Dict[str, str] = {}  # account_name -> tab_id
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """统一的API请求方法"""
        url = f"{self.api_base_url}{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, timeout=30)
            else:
                response = self.session.post(url, json=data, timeout=30)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"API请求失败 {method} {endpoint}: {e}")
    
    async def create_account_tab(self, platform: str, account_name: str, initial_url: str) -> str:
        """创建账号标签页，替代 playwright browser.new_context()"""
        print(f"🚀 创建标签页: {account_name} ({platform}) -> {initial_url}")
        
        result = self._make_request('POST', '/account/create', {
            "accountName": account_name,
            "platform": platform,
            "initialUrl": initial_url
        })
        
        if result.get("success"):
            tab_id = result["data"]["tabId"]
            self.created_tabs[account_name] = tab_id
            print(f"✅ 标签页创建成功: {tab_id}")
            
            # 等待页面初始化
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
    
    async def execute_script(self, tab_id: str, script: str, timeout: int = 30) -> Any:
        """在指定标签页执行脚本，替代 page.evaluate()"""
        print(f"📜 执行脚本在标签页 {tab_id}")
        
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
        print(f"🔗 导航到: {url}")
        
        result = self._make_request('POST', '/account/navigate', {
            "tabId": tab_id,
            "url": url
        })
        
        if result.get("success"):
            # 等待页面加载
            await asyncio.sleep(5)
            return True
        else:
            raise Exception(f"导航失败: {result.get('error')}")
    
    async def wait_for_selector(self, tab_id: str, selector: str, timeout: int = 30) -> bool:
        """等待元素出现（通过脚本实现）"""
        wait_script = f"""
        (function() {{
            return new Promise((resolve) => {{
                const startTime = Date.now();
                const checkElement = () => {{
                    const element = document.querySelector('{selector}');
                    if (element) {{
                        resolve(true);
                    }} else if (Date.now() - startTime > {timeout * 1000}) {{
                        resolve(false);
                    }} else {{
                        setTimeout(checkElement, 500);
                    }}
                }};
                checkElement();
            }});
        }})()
        """
        
        try:
            result = await self.execute_script(tab_id, wait_script)
            return bool(result)
        except:
            return False
    
    async def click_element(self, tab_id: str, selector: str) -> bool:
        """点击元素"""
        click_script = f"""
        (function() {{
            const element = document.querySelector('{selector}');
            if (element) {{
                element.click();
                return true;
            }}
            return false;
        }})()
        """
        
        try:
            result = await self.execute_script(tab_id, click_script)
            return bool(result)
        except:
            return False
    
    async def type_text(self, tab_id: str, selector: str, text: str) -> bool:
        """在输入框中输入文本"""
        type_script = f"""
        (function() {{
            const element = document.querySelector('{selector}');
            if (element) {{
                element.focus();
                element.value = '{text}';
                element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return true;
            }}
            return false;
        }})()
        """
        
        try:
            result = await self.execute_script(tab_id, type_script)
            return bool(result)
        except:
            return False
    
    async def upload_file(self, tab_id: str, file_selector: str, file_path: str) -> bool:
        """文件上传处理 - 特殊实现"""
        print(f"📁 准备上传文件: {file_path}")
        
        # 方法1: 直接触发文件选择器，然后手动提示用户选择文件
        trigger_script = f"""
        (function() {{
            const fileInput = document.querySelector('{file_selector}');
            if (fileInput) {{
                fileInput.click();
                return true;
            }}
            return false;
        }})()
        """
        
        try:
            result = await self.execute_script(tab_id, trigger_script)
            if result:
                print(f"🔔 已触发文件选择器，请手动选择文件: {file_path}")
                # 这里可能需要等待用户手动操作，或者通过其他方式处理
                return True
        except Exception as e:
            print(f"❌ 文件上传失败: {e}")
        
        return False
    
    async def save_cookies(self, tab_id: str, cookie_file: str) -> bool:
        """保存 cookies，替代 context.storage_state()"""
        result = self._make_request('POST', '/account/save-cookies', {
            "tabId": tab_id,
            "cookieFile": cookie_file
        })
        
        success = result.get("success", False)
        if success:
            print(f"💾 Cookies保存成功: {cookie_file}")
        return success
    
    async def load_cookies(self, tab_id: str, cookie_file: str) -> bool:
        """加载 cookies"""
        if not Path(cookie_file).exists():
            print(f"⚠️ Cookie文件不存在: {cookie_file}")
            return False
        
        result = self._make_request('POST', '/account/load-cookies', {
            "tabId": tab_id,
            "cookieFile": cookie_file
        })
        
        success = result.get("success", False)
        if success:
            print(f"🍪 Cookies加载成功: {cookie_file}")
            # 等待cookies生效
            await asyncio.sleep(2)
        return success
    
    async def close_tab(self, tab_id: str) -> bool:
        """关闭标签页"""
        result = self._make_request('POST', '/account/close', {"tabId": tab_id})
        success = result.get("success", False)
        if success:
            print(f"🗑️ 标签页已关闭: {tab_id}")
        return success
    
    async def take_screenshot(self, tab_id: str) -> Optional[str]:
        """截图"""
        result = self._make_request('POST', '/account/screenshot', {"tabId": tab_id})
        
        if result.get("success"):
            return result["data"]["screenshot"]
        return None
    
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
    
    async def check_login_status(self, tab_id: str, platform: str = "") -> Dict[str, Any]:
        """检查登录状态 - 通用版本"""
        check_script = """
        (function() {
            try {
                const indicators = {
                    hasUserAvatar: !!document.querySelector('.avatar, .user-avatar, [class*="avatar"]'),
                    hasUserName: !!document.querySelector('.username, .user-name, [class*="username"]'),
                    hasLoginButton: !!document.querySelector('[text*="登录"], .login, .sign-in'),
                    hasLogoutButton: !!document.querySelector('[text*="退出"], .logout, .sign-out'),
                    currentUrl: window.location.href,
                    title: document.title,
                    timestamp: new Date().toISOString()
                };
                
                // 简单判断登录状态
                const isLoggedIn = (indicators.hasUserAvatar || indicators.hasUserName || indicators.hasLogoutButton) 
                                 && !indicators.hasLoginButton;
                
                return {
                    ...indicators,
                    isLoggedIn: isLoggedIn,
                    loginStatus: isLoggedIn ? 'logged_in' : 'logged_out'
                };
            } catch(e) {
                return {
                    isLoggedIn: false,
                    loginStatus: 'unknown',
                    error: e.message,
                    currentUrl: window.location.href
                };
            }
        })()
        """
        
        try:
            result = await self.execute_script(tab_id, check_script)
            return result if isinstance(result, dict) else {"isLoggedIn": False, "error": "Invalid response"}
        except Exception as e:
            return {"isLoggedIn": False, "error": str(e)}
    
    def get_tab_id(self, account_name: str) -> Optional[str]:
        """根据账号名获取标签页ID"""
        return self.created_tabs.get(account_name)
    
    async def wait_for_login_completion(self, tab_id: str, account_name: str, timeout: int = 300) -> bool:
        """等待用户登录完成"""
        print(f"⏳ 等待用户登录 {account_name}，最多等待 {timeout} 秒...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                status = await self.check_login_status(tab_id)
                
                if status.get("isLoggedIn"):
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
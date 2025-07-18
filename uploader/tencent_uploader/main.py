# uploader/tencent_uploader/main.py
import os
import asyncio
from datetime import datetime
from pathlib import Path

from utils.browser_adapter import MultiAccountBrowserAdapter
from utils.common import get_account_info_from_db
from conf import BASE_DIR


class TencentVideo:
    def __init__(self, title, file_path, tags, publish_date, account_file, category=None):
        self.title = title
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.category = category

    async def main(self):
        """简化的主流程 - 大部分逻辑代理给浏览器"""
        # 🔥 检查 cookie 有效性，如果失效则提示用户重新登录
        if not await self._check_cookie_validity():
            raise Exception("Cookie 失效，请重新添加账号")
        
        adapter = MultiAccountBrowserAdapter()
        tab_id = None
        
        try:
            print(f'[+] 正在上传-------{self.title}')
            
            # 1. 获取或创建标签页
            tab_id = await self._get_or_create_tab(adapter)
            
            # 2. 加载cookies
            if Path(self.account_file).exists():
                await adapter.load_cookies(tab_id, str(self.account_file))
            
            # 3. 导航到上传页面
            await adapter.navigate_tab(tab_id, "https://channels.weixin.qq.com/platform/post/create")
            
            # 4. 🔥 核心：调用浏览器端完整自动化
            success = await self._upload_via_automation_engine(adapter, tab_id)
            
            if not success:
                raise Exception("视频上传失败")
                
            print("✅ 上传完成!")
            
        except Exception as e:
            print(f"❌ 上传过程中出现错误: {e}")
            raise
        finally:
            # 保存cookies
            if tab_id:
                try:
                    await adapter.save_cookies(tab_id, str(self.account_file))
                except Exception as e:
                    print(f"⚠️ 保存cookies失败: {e}")

    async def _check_cookie_validity(self) -> bool:
        """检查 cookie 有效性 - 使用原有的验证方法"""
        if not Path(self.account_file).exists():
            print(f"❌ Cookie 文件不存在: {self.account_file}")
            return False
        
        try:
            from myUtils.auth import cookie_auth_tencent
            is_valid = await cookie_auth_tencent(self.account_file)
            if not is_valid:
                print(f"❌ Cookie 已失效: {self.account_file}")
            return is_valid
        except Exception as e:
            print(f"❌ Cookie 验证失败: {e}")
            return False

    async def _get_or_create_tab(self, adapter) -> str:
        """获取或创建标签页"""
        # 检查现有标签页
        try:
            tabs = await adapter.get_all_tabs()
            for tab in tabs.get('data', []):
                if tab.get('cookieFile') == str(self.account_file):
                    print(f"🔄 复用现有标签页: {tab['id']}")
                    return tab['id']
        except:
            pass
        
        # 创建新标签页
        account_info = get_account_info_from_db(self.account_file)
        account_name = account_info.get('username', 'unknown') if account_info else 'unknown'
        
        tab_id = await adapter.create_account_tab(
            account_name=f"视频号_{account_name}",
            platform="weixin",
            initial_url="https://channels.weixin.qq.com"
        )
        
        return tab_id

    async def _upload_via_automation_engine(self, adapter, tab_id: str) -> bool:
        """调用浏览器端自动化引擎"""
        try:
            result = await adapter._make_request('POST', '/automation/upload-video-complete', {
                "tabId": tab_id,
                "platform": "wechat",
                "filePath": str(self.file_path),
                "title": self.title,
                "tags": self.tags,
                "publishDate": self.publish_date.isoformat() if self.publish_date else None,
                "enableOriginal": True,
                "addToCollection": True,
                "category": self.category
            })
            return result.get("success", False)
        except Exception as e:
            print(f"❌ 自动化引擎调用失败: {e}")
            return False
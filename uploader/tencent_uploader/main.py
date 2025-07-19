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

    async def _get_or_create_tab(self, adapter) -> str:
        """获取或创建标签页 - 使用通用方法"""
        return await adapter.get_or_create_tab(
            cookie_file=self.account_file,
            platform="wechat", 
            initial_url="https://channels.weixin.qq.com",
            tab_name_prefix="视频号_"  # 可选，会自动推断
        )

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
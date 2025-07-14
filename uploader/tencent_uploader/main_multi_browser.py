# -*- coding: utf-8 -*-
import asyncio
from datetime import datetime
from pathlib import Path

from utils.log import tencent_logger
from utils.browser_adapter import MultiAccountBrowserAdapter
from conf import BASE_DIR

class TencentVideoMultiBrowser:
    def __init__(self, title, file_path, tags, publish_date, account_file, category=None):
        self.title = title
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.category = category
        self.adapter = MultiAccountBrowserAdapter()
        self.tab_id = None
        self.adapter.set_database_path(str(BASE_DIR / "db" / "database.db"))
        self.tab_id = None

    async def main(self):
        """主流程：multi-account-browser 管理账号 + 原来的 main.py 上传"""
        try:
            from utils.log import tencent_logger
            tencent_logger.info(f'[+] 开始上传视频: {self.title}')
            
            # 步骤1: 使用通用方法确保账号登录状态
            await self.ensure_account_ready()
            
            # 步骤2: 直接调用原来成功的 main.py 方法
            await self.use_original_uploader()
            
            tencent_logger.success('[+] 视频上传成功!')
            
        except Exception as e:
            from utils.log import tencent_logger
            tencent_logger.error(f'[-] 视频上传失败: {e}')
            raise

    async def ensure_account_ready(self):
        """使用通用方法确保账号准备就绪"""
        from utils.log import tencent_logger
        tencent_logger.info("🔄 检查视频号账号登录状态...")
        
        # 调试：显示当前映射状态
        self.adapter.debug_print_account_mapping()
        
        # 使用通用方法获取或创建标签页
        self.tab_id = await self.adapter.get_or_create_account_tab(
            platform="weixin",
            cookie_file=self.account_file,
            initial_url="https://channels.weixin.qq.com/platform/post/create
        )
        
        tencent_logger.success(f"✅ 视频号账号状态检查完成，标签页ID: {self.tab_id}")


    async def check_login_status_accurately(self):
        """更准确的登录状态检查"""
        try:
            # 使用更精确的视频号登录状态检查
            login_check_script = """
            (function() {
                try {
                    // 检查视频号特有的登录标识
                    const userInfo = document.querySelector('.user-info, .profile, .avatar, [class*="user"], [class*="profile"]');
                    const loginBtn = document.querySelector('.login, .sign-in, [class*="login"], button:contains("登录")');
                    const logoutBtn = document.querySelector('.logout, .sign-out, [class*="logout"]');
                    
                    // 检查是否在登录页面
                    const isLoginPage = window.location.href.includes('login') || 
                                       document.title.includes('登录') ||
                                       document.querySelector('.login-container, .login-form');
                    
                    // 检查是否有用户头像或用户名
                    const hasUserElement = !!userInfo;
                    const hasLoginButton = !!loginBtn;
                    const hasLogoutButton = !!logoutBtn;
                    
                    // 更准确的判断逻辑
                    const isLoggedIn = hasUserElement || 
                                      (hasLogoutButton && !hasLoginButton) ||
                                      (!isLoginPage && !hasLoginButton);
                    
                    return {
                        isLoggedIn: isLoggedIn,
                        loginStatus: isLoggedIn ? 'logged_in' : 'logged_out',
                        currentUrl: window.location.href,
                        title: document.title,
                        hasUserElement: hasUserElement,
                        hasLoginButton: hasLoginButton,
                        hasLogoutButton: hasLogoutButton,
                        isLoginPage: isLoginPage,
                        timestamp: new Date().toISOString()
                    };
                } catch(e) {
                    return {
                        isLoggedIn: false,
                        loginStatus: 'unknown',
                        error: e.message,
                        currentUrl: window.location.href,
                        title: document.title
                    };
                }
            })()
            """
            
            result = await self.adapter.execute_script(self.tab_id, login_check_script)
            
            if result:
                tencent_logger.info(f"登录状态检查: {result.get('loginStatus')}")
                tencent_logger.info(f"当前页面: {result.get('currentUrl')}")
                return result
            else:
                return {"isLoggedIn": False, "loginStatus": "unknown"}
                
        except Exception as e:
            tencent_logger.warning(f"登录状态检查失败: {e}")
            return {"isLoggedIn": False, "loginStatus": "unknown", "error": str(e)}

    async def use_original_uploader(self):
        """直接使用原来成功的 main.py 上传器"""
        from utils.log import tencent_logger
        tencent_logger.info("🚀 使用原来的成功方案上传...")
        
        # 直接导入并使用原来的 TencentVideo 类
        from uploader.tencent_uploader.main import TencentVideo
        
        # 创建原来的上传器实例
        original_uploader = TencentVideo(
            title=self.title,
            file_path=self.file_path,
            tags=self.tags,
            publish_date=self.publish_date,
            account_file=self.account_file,
            category=self.category
        )
        
        # 直接调用原来的 main 方法
        await original_uploader.main()
        
        tencent_logger.success("✅ 原来的方案上传完成")
        """直接使用原来成功的 main.py 上传器"""
        tencent_logger.info("🚀 使用原来的成功方案上传...")
        
        # 直接导入并使用原来的 TencentVideo 类
        from uploader.tencent_uploader.main import TencentVideo
        
        # 创建原来的上传器实例
        original_uploader = TencentVideo(
            title=self.title,
            file_path=self.file_path,
            tags=self.tags,
            publish_date=self.publish_date,
            account_file=self.account_file,
            category=self.category
        )
        
        # 直接调用原来的 main 方法
        await original_uploader.main()
        
        tencent_logger.success("✅ 原来的方案上传完成")
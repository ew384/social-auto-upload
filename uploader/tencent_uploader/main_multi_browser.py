# -*- coding: utf-8 -*-
import asyncio
from datetime import datetime
from pathlib import Path

from utils.log import tencent_logger
from utils.browser_adapter import MultiAccountBrowserAdapter

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

    async def main(self):
        """主流程：multi-account-browser 管理账号 + 原来的 main.py 上传"""
        try:
            tencent_logger.info(f'[+] 开始上传视频: {self.title}')
            
            # 步骤1: 使用 multi-account-browser 确保账号登录状态
            await self.ensure_account_ready()
            
            # 步骤2: 直接调用原来成功的 main.py 方法
            await self.use_original_uploader()
            
            tencent_logger.success('[+] 视频上传成功!')
            
        except Exception as e:
            tencent_logger.error(f'[-] 视频上传失败: {e}')
            raise

    async def ensure_account_ready(self):
        """使用 multi-account-browser 确保账号准备就绪"""
        tencent_logger.info("🔄 检查账号登录状态...")
        
        # 1. 获取账号专属标签页（检查是否已存在）
        account_name = f"视频号_{Path(self.account_file).stem}"
        
        # 先检查是否已有该账号的标签页
        existing_tabs = self.adapter.get_all_account_tabs()
        account_key = str(Path(self.account_file).absolute())
        
        if account_key in existing_tabs:
            self.tab_id = existing_tabs[account_key]
            tencent_logger.info(f"🔄 复用现有标签页: {self.tab_id}")
            
            # 验证标签页是否仍然有效
            if not await self.adapter.is_tab_valid(self.tab_id):
                tencent_logger.warning("现有标签页已失效，创建新的")
                del self.adapter.account_tabs[account_key]
                self.tab_id = None
        
        # 如果没有有效的标签页，创建新的
        if not self.tab_id:
            self.tab_id = await self.adapter.get_or_create_account_tab(
                platform="weixin",
                account_name=account_name,
                account_file=self.account_file,
                initial_url="https://channels.weixin.qq.com/platform"
            )
        
        # 2. 等待页面加载
        await asyncio.sleep(3)
        
        # 3. 确保导航到正确页面
        current_url = await self.adapter.get_page_url(self.tab_id)
        if 'channels.weixin.qq.com' not in current_url:
            tencent_logger.info("导航到视频号平台...")
            await self.adapter.navigate_to_url(self.tab_id, "https://channels.weixin.qq.com/platform")
            await asyncio.sleep(3)
        
        # 4. 检查登录状态
        login_status = await self.check_login_status_accurately()
        
        if not login_status.get('isLoggedIn'):
            tencent_logger.warning("⚠️ 检测到未登录，尝试刷新页面让 cookies 生效...")
            
            # 刷新页面让 cookies 生效
            await self.adapter.refresh_page(self.tab_id)
            await asyncio.sleep(5)
            
            # 再次检查登录状态
            login_status = await self.check_login_status_accurately()
            
            if not login_status.get('isLoggedIn'):
                tencent_logger.warning("⚠️ 刷新后仍未登录，等待手动登录...")
                success = await self.adapter.wait_for_login_completion(
                    self.tab_id, account_name, timeout=300
                )
                if not success:
                    tencent_logger.warning("登录超时，尝试继续执行")
        
        # 5. 保存最新的登录状态
        try:
            await self.adapter.save_cookies(self.tab_id, self.account_file)
            tencent_logger.info("💾 最新登录状态已保存")
        except Exception as e:
            tencent_logger.warning(f"保存登录状态失败: {e}")
        
        tencent_logger.success("✅ 账号状态检查完成")

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
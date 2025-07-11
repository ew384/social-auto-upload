import asyncio
import configparser
import os

from playwright.async_api import async_playwright
from xhs import XhsClient

from conf import BASE_DIR
from utils.base_social_media import set_init_script
from utils.log import tencent_logger, kuaishou_logger
from pathlib import Path
from uploader.xhs_uploader.main import sign_local
from utils.browser_adapter import MultiAccountBrowserAdapter

async def cookie_auth_douyin_multi_browser(account_file):
    """使用 multi-account-browser 验证抖音 cookies"""
    adapter = MultiAccountBrowserAdapter()
    
    try:
        # 创建临时验证标签页
        tab_id = await adapter.create_account_tab(
            platform="douyin", 
            account_name="temp_verify_douyin",
            initial_url="https://creator.douyin.com/creator-micro/content/upload"
        )
        
        # 加载 cookies
        if not await adapter.load_cookies(tab_id, account_file):
            await adapter.close_tab(tab_id)
            return False
        
        # 等待页面加载
        await asyncio.sleep(3)
        
        # 验证登录状态
        verify_script = """
        (function() {
            const hasLoginForm = document.querySelector('[text*="手机号登录"], [text*="扫码登录"]');
            const hasUserInfo = document.querySelector('.avatar, [class*="user"], [class*="profile"]');
            const isUploadPage = window.location.href.includes('upload');
            
            return {
                isValid: !hasLoginForm && (hasUserInfo || isUploadPage),
                currentUrl: window.location.href,
                hasLoginForm: !!hasLoginForm,
                hasUserInfo: !!hasUserInfo
            };
        })()
        """
        
        result = await adapter.execute_script(tab_id, verify_script)
        is_valid = result.get("isValid", False) if isinstance(result, dict) else False
        
        # 关闭临时标签页
        await adapter.close_tab(tab_id)
        
        print(f"🔍 抖音Cookie验证结果: {'有效' if is_valid else '无效'}")
        return is_valid
        
    except Exception as e:
        print(f"❌ 抖音Cookie验证异常: {e}")
        return False

async def cookie_auth_xiaohongshu_multi_browser(account_file):
    """使用 multi-account-browser 验证小红书 cookies"""
    adapter = MultiAccountBrowserAdapter()
    
    try:
        # 创建临时验证标签页
        tab_id = await adapter.create_account_tab(
            platform="xiaohongshu", 
            account_name="temp_verify_xhs",
            initial_url="https://creator.xiaohongshu.com/creator-micro/content/upload"
        )
        
        # 加载 cookies
        if not await adapter.load_cookies(tab_id, account_file):
            await adapter.close_tab(tab_id)
            return False
        
        # 等待页面加载
        await asyncio.sleep(3)
        
        # 验证登录状态
        verify_script = """
        (function() {
            const hasLoginForm = document.querySelector('[text*="手机号登录"], [text*="扫码登录"]');
            const hasUserInfo = document.querySelector('.avatar, [class*="user"], [class*="profile"]');
            const isCreatorPage = window.location.href.includes('creator');
            
            return {
                isValid: !hasLoginForm && (hasUserInfo || isCreatorPage),
                currentUrl: window.location.href,
                hasLoginForm: !!hasLoginForm,
                hasUserInfo: !!hasUserInfo
            };
        })()
        """
        
        result = await adapter.execute_script(tab_id, verify_script)
        is_valid = result.get("isValid", False) if isinstance(result, dict) else False
        
        # 关闭临时标签页
        await adapter.close_tab(tab_id)
        
        print(f"🔍 小红书Cookie验证结果: {'有效' if is_valid else '无效'}")
        return is_valid
        
    except Exception as e:
        print(f"❌ 小红书Cookie验证异常: {e}")
        return False

async def cookie_auth_tencent_multi_browser(account_file):
    """使用 multi-account-browser 验证视频号 cookies"""
    adapter = MultiAccountBrowserAdapter()
    
    try:
        # 创建临时验证标签页
        tab_id = await adapter.create_account_tab(
            platform="weixin", 
            account_name="temp_verify_weixin",
            initial_url="https://channels.weixin.qq.com/platform/post/create"
        )
        
        # 加载 cookies
        if not await adapter.load_cookies(tab_id, account_file):
            await adapter.close_tab(tab_id)
            return False
        
        # 等待页面加载
        await asyncio.sleep(5)
        
        # 验证登录状态
        verify_script = """
        (function() {
            const hasWeixinStore = document.querySelector('div.title-name:has-text("微信小店")');
            const hasLoginPage = window.location.href.includes('login');
            const hasCreatorPage = window.location.href.includes('platform');
            
            return {
                isValid: !hasWeixinStore && !hasLoginPage && hasCreatorPage,
                currentUrl: window.location.href,
                hasWeixinStore: !!hasWeixinStore,
                hasLoginPage: hasLoginPage
            };
        })()
        """
        
        result = await adapter.execute_script(tab_id, verify_script)
        is_valid = result.get("isValid", False) if isinstance(result, dict) else False
        
        # 关闭临时标签页
        await adapter.close_tab(tab_id)
        
        print(f"🔍 视频号Cookie验证结果: {'有效' if is_valid else '无效'}")
        return is_valid
        
    except Exception as e:
        print(f"❌ 视频号Cookie验证异常: {e}")
        return False

async def cookie_auth_ks_multi_browser(account_file):
    """使用 multi-account-browser 验证快手 cookies"""
    adapter = MultiAccountBrowserAdapter()
    
    try:
        # 创建临时验证标签页
        tab_id = await adapter.create_account_tab(
            platform="kuaishou", 
            account_name="temp_verify_ks",
            initial_url="https://cp.kuaishou.com/article/publish/video"
        )
        
        # 加载 cookies
        if not await adapter.load_cookies(tab_id, account_file):
            await adapter.close_tab(tab_id)
            return False
        
        # 等待页面加载
        await asyncio.sleep(3)
        
        # 验证登录状态
        verify_script = """
        (function() {
            const hasInstitutionService = document.querySelector("div.names div.container div.name:text('机构服务')");
            const hasLoginButton = document.querySelector('[text*="登录"]');
            const isCreatorPage = window.location.href.includes('cp.kuaishou.com');
            
            return {
                isValid: !hasInstitutionService && !hasLoginButton && isCreatorPage,
                currentUrl: window.location.href,
                hasInstitutionService: !!hasInstitutionService,
                hasLoginButton: !!hasLoginButton
            };
        })()
        """
        
        result = await adapter.execute_script(tab_id, verify_script)
        is_valid = result.get("isValid", False) if isinstance(result, dict) else False
        
        # 关闭临时标签页
        await adapter.close_tab(tab_id)
        
        print(f"🔍 快手Cookie验证结果: {'有效' if is_valid else '无效'}")
        return is_valid
        
    except Exception as e:
        print(f"❌ 快手Cookie验证异常: {e}")
        return False

async def check_cookie_multi_browser(type, file_path):
    """使用 multi-account-browser 检查cookie"""
    match type:
        # 小红书
        case 1:
            return await cookie_auth_xiaohongshu_multi_browser(Path(BASE_DIR / "cookiesFile" / file_path))
        # 视频号
        case 2:
            return await cookie_auth_tencent_multi_browser(Path(BASE_DIR / "cookiesFile" / file_path))
        # 抖音
        case 3:
            return await cookie_auth_douyin_multi_browser(Path(BASE_DIR / "cookiesFile" / file_path))
        # 快手
        case 4:
            return await cookie_auth_ks_multi_browser(Path(BASE_DIR / "cookiesFile" / file_path))
        case _:
            return False
            
async def cookie_auth_douyin(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://creator.douyin.com/creator-micro/content/upload")
        try:
            await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload", timeout=5000)
        except:
            print("[+] 等待5秒 cookie 失效")
            await context.close()
            await browser.close()
            return False
        # 2024.06.17 抖音创作者中心改版
        if await page.get_by_text('手机号登录').count() or await page.get_by_text('扫码登录').count():
            print("[+] 等待5秒 cookie 失效")
            return False
        else:
            print("[+] cookie 有效")
            return True

async def cookie_auth_tencent(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://channels.weixin.qq.com/platform/post/create")
        try:
            await page.wait_for_selector('div.title-name:has-text("微信小店")', timeout=5000)  # 等待5秒
            tencent_logger.error("[+] 等待5秒 cookie 失效")
            return False
        except:
            tencent_logger.success("[+] cookie 有效")
            return True

async def cookie_auth_ks(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://cp.kuaishou.com/article/publish/video")
        try:
            await page.wait_for_selector("div.names div.container div.name:text('机构服务')", timeout=5000)  # 等待5秒

            kuaishou_logger.info("[+] 等待5秒 cookie 失效")
            return False
        except:
            kuaishou_logger.success("[+] cookie 有效")
            return True


async def cookie_auth_xhs(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://creator.xiaohongshu.com/creator-micro/content/upload")
        try:
            await page.wait_for_url("https://creator.xiaohongshu.com/creator-micro/content/upload", timeout=5000)
        except:
            print("[+] 等待5秒 cookie 失效")
            await context.close()
            await browser.close()
            return False
        # 2024.06.17 抖音创作者中心改版
        if await page.get_by_text('手机号登录').count() or await page.get_by_text('扫码登录').count():
            print("[+] 等待5秒 cookie 失效")
            return False
        else:
            print("[+] cookie 有效")
            return True


async def check_cookie(type,file_path):
    match type:
        # 小红书
        case 1:
            return await cookie_auth_xhs(Path(BASE_DIR / "cookiesFile" / file_path))
        # 视频号
        case 2:
            return await cookie_auth_tencent(Path(BASE_DIR / "cookiesFile" / file_path))
        # 抖音
        case 3:
            return await cookie_auth_douyin(Path(BASE_DIR / "cookiesFile" / file_path))
        # 快手
        case 4:
            return await cookie_auth_ks(Path(BASE_DIR / "cookiesFile" / file_path))
        case _:
            return False

# a = asyncio.run(check_cookie(1,"3a6cfdc0-3d51-11f0-8507-44e51723d63c.json"))
# print(a)
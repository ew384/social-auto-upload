import asyncio
import sqlite3
import time
from utils.smart_playwright import async_playwright, Playwright
from queue import Queue
from myUtils.auth import check_cookie
from utils.base_social_media import set_init_script
import uuid
from pathlib import Path
from conf import BASE_DIR


async def get_tencent_cookie(account_name: str, status_queue: Queue = None):
    """
    视频号登录 - 自动选择浏览器模式
    """
    cookie_file = Path(BASE_DIR / "cookiesFile" / f"{account_name}_tencent.json")
    
    if status_queue:
        status_queue.put("开始视频号登录...")
    
    print(f"🎯 视频号登录开始: {account_name}")
    print(f"   Cookie文件: {cookie_file}")
    
    try:
        # 🔥 关键：这里会自动选择最优的浏览器实现
        # 如果有 multi-account-browser，会复用标签页
        # 如果没有，会使用传统的 Chrome 启动
        async with (await async_playwright()) as playwright:
            browser = await playwright.chromium.launch(
                headless=False,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            # 创建上下文 - 会自动映射到对应的账号标签页
            context = await browser.new_context()
            page = await context.new_page()
            
            if status_queue:
                status_queue.put("正在打开登录页面...")
            
            # 导航到登录页
            await page.goto("https://channels.weixin.qq.com")
            
            if status_queue:
                status_queue.put("请扫码登录，登录完成后会自动保存Cookie...")
            
            print("📱 请在浏览器中完成登录...")
            
            # 等待用户登录完成的检测
            login_success = False
            max_wait_time = 300  # 5分钟超时
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                try:
                    current_url = page.url
                    
                    # 检测是否已登录（不在登录页面）
                    if "login" not in current_url.lower():
                        # 进一步检测登录状态
                        try:
                            # 检查是否有用户相关元素
                            user_element = await page.query_selector('.user-avatar, .avatar, .nickname, .username')
                            if user_element:
                                login_success = True
                                break
                        except:
                            pass
                    
                    await asyncio.sleep(2)
                    
                    # 每30秒提示一次
                    elapsed = int(time.time() - start_time)
                    if elapsed % 30 == 0 and elapsed > 0:
                        if status_queue:
                            status_queue.put(f"等待登录中... ({elapsed}/{max_wait_time}秒)")
                        print(f"⏳ 等待登录中... ({elapsed}/{max_wait_time}秒)")
                
                except Exception as e:
                    print(f"⚠️ 登录检测异常: {e}")
                    await asyncio.sleep(5)
            
            if login_success:
                if status_queue:
                    status_queue.put("登录成功，正在保存Cookie...")
                
                print("✅ 检测到登录成功，保存Cookie...")
                
                # 保存 Cookie - 会自动保存到指定文件
                await context.storage_state(path=str(cookie_file))
                
                if status_queue:
                    status_queue.put("200")  # 成功状态码
                
                print(f"✅ 视频号登录完成: {account_name}")
                print(f"   Cookie已保存: {cookie_file}")
                
            else:
                if status_queue:
                    status_queue.put("500")  # 失败状态码
                
                print(f"⏱️ 视频号登录超时: {account_name}")
            
            await context.close()
            await browser.close()
            
    except Exception as e:
        if status_queue:
            status_queue.put("500")
        
        print(f"❌ 视频号登录失败: {account_name}, 错误: {e}")
        raise

async def douyin_cookie_gen(account_name: str, status_queue: Queue = None):
    """
    抖音登录 - 自动选择浏览器模式
    """
    cookie_file = Path(BASE_DIR / "cookiesFile" / f"{account_name}_douyin.json")
    
    if status_queue:
        status_queue.put("开始抖音登录...")
    
    print(f"🎯 抖音登录开始: {account_name}")
    
    try:
        async with (await async_playwright()) as playwright:
            browser = await playwright.chromium.launch(
                headless=False,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            context = await browser.new_context()
            page = await context.new_page()
            
            if status_queue:
                status_queue.put("正在打开登录页面...")
            
            await page.goto("https://creator.douyin.com")
            
            if status_queue:
                status_queue.put("请完成登录，登录完成后会自动保存Cookie...")
            
            print("📱 请在浏览器中完成抖音登录...")
            
            # 等待登录完成
            login_success = False
            max_wait_time = 300
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                try:
                    current_url = page.url
                    
                    # 检测抖音登录状态
                    if "creator.douyin.com" in current_url and "login" not in current_url.lower():
                        try:
                            # 检查是否有创作者相关元素
                            creator_element = await page.query_selector('.semi-avatar, .creator-header, .user-info')
                            if creator_element:
                                login_success = True
                                break
                        except:
                            pass
                    
                    await asyncio.sleep(2)
                    
                    elapsed = int(time.time() - start_time)
                    if elapsed % 30 == 0 and elapsed > 0:
                        if status_queue:
                            status_queue.put(f"等待抖音登录中... ({elapsed}/{max_wait_time}秒)")
                
                except Exception as e:
                    print(f"⚠️ 抖音登录检测异常: {e}")
                    await asyncio.sleep(5)
            
            if login_success:
                if status_queue:
                    status_queue.put("抖音登录成功，正在保存Cookie...")
                
                print("✅ 抖音登录成功，保存Cookie...")
                await context.storage_state(path=str(cookie_file))
                
                if status_queue:
                    status_queue.put("200")
                
                print(f"✅ 抖音登录完成: {account_name}")
                
            else:
                if status_queue:
                    status_queue.put("500")
                
                print(f"⏱️ 抖音登录超时: {account_name}")
            
            await context.close()
            await browser.close()
            
    except Exception as e:
        if status_queue:
            status_queue.put("500")
        
        print(f"❌ 抖音登录失败: {account_name}, 错误: {e}")
        raise

async def xiaohongshu_cookie_gen(account_name: str, status_queue: Queue = None):
    """
    小红书登录 - 自动选择浏览器模式
    """
    cookie_file = Path(BASE_DIR / "cookiesFile" / f"{account_name}_xiaohongshu.json")
    
    if status_queue:
        status_queue.put("开始小红书登录...")
    
    print(f"🎯 小红书登录开始: {account_name}")
    
    try:
        async with (await async_playwright()) as playwright:
            browser = await playwright.chromium.launch(
                headless=False,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            context = await browser.new_context()
            page = await context.new_page()
            
            if status_queue:
                status_queue.put("正在打开小红书创作者平台...")
            
            await page.goto("https://creator.xiaohongshu.com")
            
            if status_queue:
                status_queue.put("请完成登录，登录完成后会自动保存Cookie...")
            
            print("📱 请在浏览器中完成小红书登录...")
            
            # 等待登录完成
            login_success = False
            max_wait_time = 300
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                try:
                    current_url = page.url
                    
                    # 检测小红书登录状态
                    if "creator.xiaohongshu.com" in current_url and "login" not in current_url.lower():
                        try:
                            # 检查是否有创作者相关元素
                            creator_element = await page.query_selector('.header-avatar, .user-avatar, .creator-info')
                            if creator_element:
                                login_success = True
                                break
                        except:
                            pass
                    
                    await asyncio.sleep(2)
                    
                    elapsed = int(time.time() - start_time)
                    if elapsed % 30 == 0 and elapsed > 0:
                        if status_queue:
                            status_queue.put(f"等待小红书登录中... ({elapsed}/{max_wait_time}秒)")
                
                except Exception as e:
                    print(f"⚠️ 小红书登录检测异常: {e}")
                    await asyncio.sleep(5)
            
            if login_success:
                if status_queue:
                    status_queue.put("小红书登录成功，正在保存Cookie...")
                
                print("✅ 小红书登录成功，保存Cookie...")
                await context.storage_state(path=str(cookie_file))
                
                if status_queue:
                    status_queue.put("200")
                
                print(f"✅ 小红书登录完成: {account_name}")
                
            else:
                if status_queue:
                    status_queue.put("500")
                
                print(f"⏱️ 小红书登录超时: {account_name}")
            
            await context.close()
            await browser.close()
            
    except Exception as e:
        if status_queue:
            status_queue.put("500")
        
        print(f"❌ 小红书登录失败: {account_name}, 错误: {e}")
        raise

async def get_ks_cookie(account_name: str, status_queue: Queue = None):
    """
    快手登录 - 自动选择浏览器模式
    """
    cookie_file = Path(BASE_DIR / "cookiesFile" / f"{account_name}_kuaishou.json")
    
    if status_queue:
        status_queue.put("开始快手登录...")
    
    print(f"🎯 快手登录开始: {account_name}")
    
    try:
        async with (await async_playwright()) as playwright:
            browser = await playwright.chromium.launch(
                headless=False,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            context = await browser.new_context()
            page = await context.new_page()
            
            if status_queue:
                status_queue.put("正在打开快手创作者平台...")
            
            await page.goto("https://cp.kuaishou.com")
            
            if status_queue:
                status_queue.put("请完成登录，登录完成后会自动保存Cookie...")
            
            print("📱 请在浏览器中完成快手登录...")
            
            # 等待登录完成
            login_success = False
            max_wait_time = 300
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                try:
                    current_url = page.url
                    
                    # 检测快手登录状态
                    if "cp.kuaishou.com" in current_url and "login" not in current_url.lower():
                        try:
                            # 检查是否有创作者相关元素
                            creator_element = await page.query_selector('.header-userinfo, .user-avatar, .creator-header')
                            if creator_element:
                                login_success = True
                                break
                        except:
                            pass
                    
                    await asyncio.sleep(2)
                    
                    elapsed = int(time.time() - start_time)
                    if elapsed % 30 == 0 and elapsed > 0:
                        if status_queue:
                            status_queue.put(f"等待快手登录中... ({elapsed}/{max_wait_time}秒)")
                
                except Exception as e:
                    print(f"⚠️ 快手登录检测异常: {e}")
                    await asyncio.sleep(5)
            
            if login_success:
                if status_queue:
                    status_queue.put("快手登录成功，正在保存Cookie...")
                
                print("✅ 快手登录成功，保存Cookie...")
                await context.storage_state(path=str(cookie_file))
                
                if status_queue:
                    status_queue.put("200")
                
                print(f"✅ 快手登录完成: {account_name}")
                
            else:
                if status_queue:
                    status_queue.put("500")
                
                print(f"⏱️ 快手登录超时: {account_name}")
            
            await context.close()
            await browser.close()
            
    except Exception as e:
        if status_queue:
            status_queue.put("500")
        
        print(f"❌ 快手登录失败: {account_name}, 错误: {e}")
        raise
# a = asyncio.run(xiaohongshu_cookie_gen(4,None))
# print(a)

import asyncio
import sqlite3

from playwright.async_api import async_playwright

from myUtils.auth import check_cookie
from utils.base_social_media import set_init_script
import uuid
from pathlib import Path
from conf import BASE_DIR
from utils.browser_adapter import MultiAccountBrowserAdapter

async def douyin_cookie_gen_multi_browser(id, status_queue):
    """使用 multi-account-browser 的抖音登录函数"""
    adapter = MultiAccountBrowserAdapter()
    
    try:
        status_queue.put(f"data:开始创建抖音登录标签页...")
        
        # 1. 创建抖音登录标签页
        tab_id = await adapter.create_account_tab(
            platform="douyin",
            account_name=id,
            initial_url="https://creator.douyin.com/"
        )
        
        status_queue.put(f"data:标签页创建成功，等待用户登录...")
        
        # 2. 等待用户手动登录
        login_success = await adapter.wait_for_login_completion(tab_id, id, timeout=200)
        
        if not login_success:
            status_queue.put("500")
            return
        
        # 3. 保存 cookies
        uuid_v1 = uuid.uuid1()
        cookie_file = Path(BASE_DIR / "cookiesFile" / f"{uuid_v1}.json")
        
        if await adapter.save_cookies(tab_id, str(cookie_file)):
            # 4. 保存到数据库
            with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO user_info (type, filePath, userName, status)
                    VALUES (?, ?, ?, ?)
                ''', (3, f"{uuid_v1}.json", id, 1))
                conn.commit()
                print("✅ 用户信息已保存到数据库")
            
            status_queue.put("200")
            print(f"✅ 抖音账号 {id} 登录成功，cookies已保存")
        else:
            status_queue.put("500")
            print(f"❌ 保存cookies失败")
            
    except Exception as e:
        print(f"❌ 抖音登录失败: {e}")
        status_queue.put("500")

async def xiaohongshu_cookie_gen_multi_browser(id, status_queue):
    """使用 multi-account-browser 的小红书登录函数"""
    adapter = MultiAccountBrowserAdapter()
    
    try:
        status_queue.put(f"data:开始创建小红书登录标签页...")
        
        # 1. 创建小红书登录标签页
        tab_id = await adapter.create_account_tab(
            platform="xiaohongshu",
            account_name=id,
            initial_url="https://creator.xiaohongshu.com/"
        )
        
        status_queue.put(f"data:标签页创建成功，等待用户登录...")
        
        # 2. 等待用户手动登录
        login_success = await adapter.wait_for_login_completion(tab_id, id, timeout=200)
        
        if not login_success:
            status_queue.put("500")
            return
        
        # 3. 保存 cookies
        uuid_v1 = uuid.uuid1()
        cookie_file = Path(BASE_DIR / "cookiesFile" / f"{uuid_v1}.json")
        
        if await adapter.save_cookies(tab_id, str(cookie_file)):
            # 4. 保存到数据库
            with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO user_info (type, filePath, userName, status)
                    VALUES (?, ?, ?, ?)
                ''', (1, f"{uuid_v1}.json", id, 1))
                conn.commit()
                print("✅ 用户信息已保存到数据库")
            
            status_queue.put("200")
            print(f"✅ 小红书账号 {id} 登录成功，cookies已保存")
        else:
            status_queue.put("500")
            print(f"❌ 保存cookies失败")
            
    except Exception as e:
        print(f"❌ 小红书登录失败: {e}")
        status_queue.put("500")

async def get_tencent_cookie_multi_browser(id, status_queue):
    """使用 multi-account-browser 的视频号登录函数 - 使用通用方法"""
    adapter = MultiAccountBrowserAdapter()
    
    # 设置数据库路径
    from conf import BASE_DIR
    adapter.set_database_path(str(BASE_DIR / "db" / "database.db"))
    
    try:
        status_queue.put(f"data:开始创建视频号登录标签页...")
        
        # 生成临时的cookie文件名（用于预先生成账号标识符）
        uuid_v1 = uuid.uuid1()
        temp_cookie_file = str(BASE_DIR / "cookiesFile" / f"{uuid_v1}.json")
        
        # 生成账号标识符和显示名
        tab_identifier = adapter.generate_tab_identifier("weixin", temp_cookie_file)
        display_name = adapter.generate_display_name("weixin", temp_cookie_file)
        
        status_queue.put(f"data:标签页标识符: {tab_identifier}")
        status_queue.put(f"data:显示名称: {display_name}")
        
        # 1. 创建视频号登录标签页（使用UUID标识符）
        tab_id = await adapter.create_account_tab(
            platform="weixin",
            account_name=tab_identifier,  # 后端使用UUID标识符
            initial_url="https://channels.weixin.qq.com/"
        )
        
        status_queue.put(f"data:标签页创建成功（ID: {tab_id}），等待用户登录...")
        
        # 2. 等待用户手动登录
        login_success = await adapter.wait_for_login_completion(tab_id, id, timeout=200)
        
        if not login_success:
            status_queue.put("500")
            return
        
        # 3. 保存 cookies（使用实际的文件路径）
        cookie_file = Path(BASE_DIR / "cookiesFile" / f"{uuid_v1}.json")
        
        if await adapter.save_cookies(tab_id, str(cookie_file)):
            # 4. 保存到数据库
            with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO user_info (type, filePath, userName, status)
                    VALUES (?, ?, ?, ?)
                ''', (2, f"{uuid_v1}.json", id, 1))
                conn.commit()
                print("✅ 用户信息已保存到数据库")
            
            # 5. 更新适配器的账号映射（重要！）
            account_key = str(cookie_file.absolute())
            adapter.account_tabs[account_key] = tab_id
            print(f"📋 登录完成后更新账号映射: {display_name} -> {tab_id}")
            
            status_queue.put("200")
            print(f"✅ 视频号账号 {id} 登录成功，cookies已保存")
        else:
            status_queue.put("500")
            print(f"❌ 保存cookies失败")
            
    except Exception as e:
        print(f"❌ 视频号登录失败: {e}")
        status_queue.put("500")


async def get_ks_cookie_multi_browser(id, status_queue):
    """使用 multi-account-browser 的快手登录函数"""
    adapter = MultiAccountBrowserAdapter()
    
    try:
        status_queue.put(f"data:开始创建快手登录标签页...")
        
        # 1. 创建快手登录标签页
        tab_id = await adapter.create_account_tab(
            platform="kuaishou",
            account_name=id,
            initial_url="https://cp.kuaishou.com"
        )
        
        status_queue.put(f"data:标签页创建成功，等待用户登录...")
        
        # 2. 等待用户手动登录
        login_success = await adapter.wait_for_login_completion(tab_id, id, timeout=200)
        
        if not login_success:
            status_queue.put("500")
            return
        
        # 3. 保存 cookies
        uuid_v1 = uuid.uuid1()
        cookie_file = Path(BASE_DIR / "cookiesFile" / f"{uuid_v1}.json")
        
        if await adapter.save_cookies(tab_id, str(cookie_file)):
            # 4. 保存到数据库
            with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO user_info (type, filePath, userName, status)
                    VALUES (?, ?, ?, ?)
                ''', (4, f"{uuid_v1}.json", id, 1))
                conn.commit()
                print("✅ 用户信息已保存到数据库")
            
            status_queue.put("200")
            print(f"✅ 快手账号 {id} 登录成功，cookies已保存")
        else:
            status_queue.put("500")
            print(f"❌ 保存cookies失败")
            
    except Exception as e:
        print(f"❌ 快手登录失败: {e}")
        status_queue.put("500")
        
async def douyin_cookie_gen(id,status_queue):
    url_changed_event = asyncio.Event()
    async def on_url_change():
        # 检查是否是主框架的变化
        if page.url != original_url:
            url_changed_event.set()
    async with async_playwright() as playwright:
        options = {
            'headless': False
        }
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://creator.douyin.com/")
        original_url = page.url
        img_locator = page.get_by_role("img", name="二维码")
        # 获取 src 属性值
        try:
            # 首先等待元素出现
            await img_locator.wait_for(state="visible", timeout=60000)
            # 然后获取属性
            src = await img_locator.get_attribute("src", timeout=10000)
        except TimeoutError:
            # 如果仍然超时，可以尝试刷新页面或重试
            await page.reload()
            await img_locator.wait_for(state="visible", timeout=60000)
            src = await img_locator.get_attribute("src", timeout=10000)
        print("✅ 图片地址:", src)
        status_queue.put(src)
        # 监听页面的 'framenavigated' 事件，只关注主框架的变化
        page.on('framenavigated',
                lambda frame: asyncio.create_task(on_url_change()) if frame == page.main_frame else None)
        try:
            # 等待 URL 变化或超时
            await asyncio.wait_for(url_changed_event.wait(), timeout=200)  # 最多等待 200 秒
            print("监听页面跳转成功")
        except asyncio.TimeoutError:
            print("监听页面跳转超时")
            await page.close()
            await context.close()
            await browser.close()
            status_queue.put("500")
            return None
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        await context.storage_state(path=Path(BASE_DIR / "cookiesFile" / f"{uuid_v1}.json"))
        result = await check_cookie(3, f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                                INSERT INTO user_info (type, filePath, userName, status)
                                VALUES (?, ?, ?, ?)
                                ''', (3, f"{uuid_v1}.json", id, 1))
            conn.commit()
            print("✅ 用户状态已记录")
        status_queue.put("200")


# 视频号登录
async def get_tencent_cookie(id,status_queue):
    url_changed_event = asyncio.Event()
    async def on_url_change():
        # 检查是否是主框架的变化
        if page.url != original_url:
            url_changed_event.set()

    async with async_playwright() as playwright:
        options = {
            'args': [
                '--lang en-GB'
            ],
            'headless': False,  # Set headless option here
        }
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        # Pause the page, and start recording manually.
        context = await set_init_script(context)
        page = await context.new_page()
        await page.goto("https://channels.weixin.qq.com")
        original_url = page.url

        # 监听页面的 'framenavigated' 事件，只关注主框架的变化
        page.on('framenavigated',
                lambda frame: asyncio.create_task(on_url_change()) if frame == page.main_frame else None)

        # 等待 iframe 出现（最多等 60 秒）
        iframe_locator = page.frame_locator("iframe").first

        # 获取 iframe 中的第一个 img 元素
        img_locator = iframe_locator.get_by_role("img").first

        # 获取 src 属性值
        src = await img_locator.get_attribute("src")
        print("✅ 图片地址:", src)
        status_queue.put(src)

        try:
            # 等待 URL 变化或超时
            await asyncio.wait_for(url_changed_event.wait(), timeout=200)  # 最多等待 200 秒
            print("监听页面跳转成功")
        except asyncio.TimeoutError:
            status_queue.put("500")
            print("监听页面跳转超时")
            await page.close()
            await context.close()
            await browser.close()
            return None
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        await context.storage_state(path=Path(BASE_DIR / "cookiesFile" / f"{uuid_v1}.json"))
        result = await check_cookie(2,f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()

        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                                INSERT INTO user_info (type, filePath, userName, status)
                                VALUES (?, ?, ?, ?)
                                ''', (2, f"{uuid_v1}.json", id, 1))
            conn.commit()
            print("✅ 用户状态已记录")
        status_queue.put("200")

# 快手登录
async def get_ks_cookie(id,status_queue):
    url_changed_event = asyncio.Event()
    async def on_url_change():
        # 检查是否是主框架的变化
        if page.url != original_url:
            url_changed_event.set()
    async with async_playwright() as playwright:
        options = {
            'args': [
                '--lang en-GB'
            ],
            'headless': False,  # Set headless option here
        }
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://cp.kuaishou.com")

        # 定位并点击“立即登录”按钮（类型为 link）
        await page.get_by_role("link", name="立即登录").click()
        await page.get_by_text("扫码登录").click()
        img_locator = page.get_by_role("img", name="qrcode")
        # 获取 src 属性值
        src = await img_locator.get_attribute("src")
        original_url = page.url
        print("✅ 图片地址:", src)
        status_queue.put(src)
        # 监听页面的 'framenavigated' 事件，只关注主框架的变化
        page.on('framenavigated',
                lambda frame: asyncio.create_task(on_url_change()) if frame == page.main_frame else None)

        try:
            # 等待 URL 变化或超时
            await asyncio.wait_for(url_changed_event.wait(), timeout=200)  # 最多等待 200 秒
            print("监听页面跳转成功")
        except asyncio.TimeoutError:
            status_queue.put("500")
            print("监听页面跳转超时")
            await page.close()
            await context.close()
            await browser.close()
            return None
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        await context.storage_state(path=Path(BASE_DIR / "cookiesFile" / f"{uuid_v1}.json"))
        result = await check_cookie(4, f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()

        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                                        INSERT INTO user_info (type, filePath, userName, status)
                                        VALUES (?, ?, ?, ?)
                                        ''', (4, f"{uuid_v1}.json", id, 1))
            conn.commit()
            print("✅ 用户状态已记录")
        status_queue.put("200")

# 小红书登录
async def xiaohongshu_cookie_gen(id,status_queue):
    url_changed_event = asyncio.Event()

    async def on_url_change():
        # 检查是否是主框架的变化
        if page.url != original_url:
            url_changed_event.set()

    async with async_playwright() as playwright:
        options = {
            'args': [
                '--lang en-GB'
            ],
            'headless': False,  # Set headless option here
        }
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://creator.xiaohongshu.com/")
        await page.locator('img.css-wemwzq').click()

        img_locator = page.get_by_role("img").nth(2)
        # 获取 src 属性值
        src = await img_locator.get_attribute("src")
        original_url = page.url
        print("✅ 图片地址:", src)
        status_queue.put(src)
        # 监听页面的 'framenavigated' 事件，只关注主框架的变化
        page.on('framenavigated',
                lambda frame: asyncio.create_task(on_url_change()) if frame == page.main_frame else None)

        try:
            # 等待 URL 变化或超时
            await asyncio.wait_for(url_changed_event.wait(), timeout=200)  # 最多等待 200 秒
            print("监听页面跳转成功")
        except asyncio.TimeoutError:
            status_queue.put("500")
            print("监听页面跳转超时")
            await page.close()
            await context.close()
            await browser.close()
            return None
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        await context.storage_state(path=Path(BASE_DIR / "cookiesFile" / f"{uuid_v1}.json"))
        result = await check_cookie(1, f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()

        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           INSERT INTO user_info (type, filePath, userName, status)
                           VALUES (?, ?, ?, ?)
                           ''', (1, f"{uuid_v1}.json", id, 1))
            conn.commit()
            print("✅ 用户状态已记录")
        status_queue.put("200")

# a = asyncio.run(xiaohongshu_cookie_gen(4,None))
# print(a)

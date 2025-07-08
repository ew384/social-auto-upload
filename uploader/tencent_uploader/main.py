# -*- coding: utf-8 -*-
from datetime import datetime

from playwright.async_api import Playwright, async_playwright
import os
import asyncio

from conf import LOCAL_CHROME_PATH
from utils.base_social_media import set_init_script
from utils.files_times import get_absolute_path
from utils.log import tencent_logger


def format_str_for_short_title(origin_title: str) -> str:
    # 定义允许的特殊字符
    allowed_special_chars = "《》“”:+?%°"

    # 移除不允许的特殊字符
    filtered_chars = [char if char.isalnum() or char in allowed_special_chars else ' ' if char == ',' else '' for
                      char in origin_title]
    formatted_string = ''.join(filtered_chars)

    # 调整字符串长度
    if len(formatted_string) > 16:
        # 截断字符串
        formatted_string = formatted_string[:16]
    elif len(formatted_string) < 6:
        # 使用空格来填充字符串
        formatted_string += ' ' * (6 - len(formatted_string))

    return formatted_string


async def cookie_auth(account_file):
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


async def get_tencent_cookie(account_file):
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
        await page.pause()
        # 点击调试器的继续，保存cookie
        await context.storage_state(path=account_file)


async def weixin_setup(account_file, handle=False):
    account_file = get_absolute_path(account_file, "tencent_uploader")
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            # Todo alert message
            return False
        tencent_logger.info('[+] cookie文件不存在或已失效，即将自动打开浏览器，请扫码登录，登陆后会自动生成cookie文件')
        await get_tencent_cookie(account_file)
    return True


class TencentVideo(object):
    def __init__(self, title, file_path, tags, publish_date: datetime, account_file, category=None):
        self.title = title  # 视频标题
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.category = category
        self.local_executable_path = LOCAL_CHROME_PATH

    async def set_schedule_time_tencent(self, page, publish_date):
        label_element = page.locator("label").filter(has_text="定时").nth(1)
        await label_element.click()

        await page.click('input[placeholder="请选择发表时间"]')

        str_month = str(publish_date.month) if publish_date.month > 9 else "0" + str(publish_date.month)
        current_month = str_month + "月"
        # 获取当前的月份
        page_month = await page.inner_text('span.weui-desktop-picker__panel__label:has-text("月")')

        # 检查当前月份是否与目标月份相同
        if page_month != current_month:
            await page.click('button.weui-desktop-btn__icon__right')

        # 获取页面元素
        elements = await page.query_selector_all('table.weui-desktop-picker__table a')

        # 遍历元素并点击匹配的元素
        for element in elements:
            if 'weui-desktop-picker__disabled' in await element.evaluate('el => el.className'):
                continue
            text = await element.inner_text()
            if text.strip() == str(publish_date.day):
                await element.click()
                break

        # 输入小时部分（假设选择11小时）
        await page.click('input[placeholder="请选择时间"]')
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(str(publish_date.hour))

        # 选择标题栏（令定时时间生效）
        await page.locator("div.input-editor").click()

    async def handle_upload_error(self, page):
        tencent_logger.info("视频出错了，重新上传中")
        await page.locator('div.media-status-content div.tag-inner:has-text("删除")').click()
        await page.get_by_role('button', name="删除", exact=True).click()
        file_input = page.locator('input[type="file"]')
        await file_input.set_input_files(self.file_path,timeout=60000)

    async def upload(self, playwright: Playwright) -> None:
        """带重试机制的上传方法 - 大文件优化版本"""
        max_retries = 3
        for attempt in range(max_retries):
            browser = None
            context = None
            try:
                file_size = os.path.getsize(self.file_path)
                is_large_file = file_size > 100 * 1024 * 1024
                
                tencent_logger.info(f'[+]正在上传-------{self.title} (尝试 {attempt + 1}/{max_retries})')
                if is_large_file:
                    tencent_logger.info(f'[+]检测到大文件 ({file_size/1024/1024:.1f}MB)，使用优化配置')
                
                # 针对大文件优化的浏览器参数
                browser_args = [
                    '--no-sandbox', 
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection'
                ]
                
                if is_large_file:
                    browser_args.extend([
                        '--max_old_space_size=4096',  # 增加内存限制
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-renderer-backgrounding',
                        '--force-device-scale-factor=1'
                    ])
                
                browser = await playwright.chromium.launch(
                    headless=False, 
                    executable_path=self.local_executable_path,
                    args=browser_args
                )
                
                # 为大文件创建优化的上下文
                context_options = {
                    'storage_state': f"{self.account_file}",
                    'viewport': {'width': 1280, 'height': 720}
                }
                
                if is_large_file:
                    # 大文件上传的额外配置
                    context_options.update({
                        'ignore_https_errors': True,
                        'java_script_enabled': True
                    })
                
                context = await browser.new_context(**context_options)
                context = await set_init_script(context)

                page = await context.new_page()
                
                # 为大文件设置更长的超时时间
                timeout = 300000 if is_large_file else 120000  # 5分钟 vs 2分钟
                page.set_default_timeout(timeout)
                
                # 监听网络请求，用于调试大文件上传
                if is_large_file:
                    page.on("request", lambda request: 
                        tencent_logger.info(f"Request: {request.method} {request.url[:100]}...")
                        if request.method == "POST" and "upload" in request.url.lower()
                        else None
                    )
                    
                    page.on("response", lambda response:
                        tencent_logger.info(f"Response: {response.status} {response.url[:100]}...")
                        if "upload" in response.url.lower()
                        else None
                    )
                
                await page.goto("https://channels.weixin.qq.com/platform/post/create")
                await page.wait_for_url("https://channels.weixin.qq.com/platform/post/create", timeout=60000)
                
                # 上传文件
                await self.upload_file_to_shadow_dom(page)
                
                # 验证上传是否真正开始
                upload_started = await self.verify_upload_started(page)
                if not upload_started:
                    tencent_logger.warning("未检测到上传开始，可能需要手动干预")
                    if is_large_file:
                        # 对于大文件，给更多时间让上传开始
                        await asyncio.sleep(10)
                        upload_started = await self.verify_upload_started(page)
                    
                    if not upload_started:
                        raise Exception("文件上传未能正确开始")
                
                # 填充标题和话题
                await self.add_title_tags(page)
                
                # 合集功能
                await self.add_collection(page)
                
                # 原创选择
                await self.add_original(page)
                
                # 检测上传状态
                await self.detect_upload_status(page)
                
                if self.publish_date != 0:
                    await self.set_schedule_time_tencent(page, self.publish_date)
                
                # 添加短标题
                await self.add_short_title(page)

                await self.click_publish(page)

                await context.storage_state(path=f"{self.account_file}")
                tencent_logger.success('[-]cookie更新完毕！')
                tencent_logger.success(f'[-]视频上传成功: {self.title}')
                
                break
                    
            except Exception as e:
                tencent_logger.error(f'[-]上传失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}')
                
                if attempt == max_retries - 1:
                    tencent_logger.error(f'[-]视频上传彻底失败: {self.title}')
                    raise e
                else:
                    wait_time = 20 if is_large_file else 10
                    tencent_logger.info(f'[-]等待 {wait_time} 秒后重试...')
                    await asyncio.sleep(wait_time)
                    
            finally:
                try:
                    if context:
                        await context.close()
                    if browser:
                        await browser.close()
                except Exception as cleanup_error:
                    tencent_logger.warning(f'[-]清理资源时出错: {str(cleanup_error)}')
                
                await asyncio.sleep(2)

    async def upload_file_to_shadow_dom(self, page):
        """处理文件上传 - 完全重新设计的方案"""
        await page.wait_for_selector('wujie-app', timeout=30000)
        await asyncio.sleep(3)
        
        # 处理文件路径
        actual_file_path = self.file_path
        if not os.path.exists(self.file_path):
            import glob
            original_filename = os.path.basename(self.file_path)
            video_dir = os.path.dirname(self.file_path)
            pattern = os.path.join(video_dir, f"*_{original_filename}")
            matching_files = glob.glob(pattern)
            
            if matching_files:
                matching_files.sort(key=os.path.getmtime, reverse=True)
                actual_file_path = matching_files[0]
                tencent_logger.info(f"找到实际文件: {original_filename} -> {os.path.basename(actual_file_path)}")
            else:
                raise FileNotFoundError(f"找不到文件: {self.file_path}")
        
        file_size = os.path.getsize(actual_file_path)
        is_large_file = file_size > 100 * 1024 * 1024
        
        if is_large_file:
            tencent_logger.info(f"检测到大文件 ({file_size / 1024 / 1024:.1f}MB)，使用专门的上传策略")
        
        # 方案1：预先注入文件输入框并监听点击事件
        try:
            tencent_logger.info("尝试预注入文件输入框方案...")
            
            # 注入自定义的文件处理逻辑
            # 使用JSON.stringify来安全地传递文件路径
            script = '''
                window.actualFilePath = arguments[0];
                window.fileUploadHandled = false;
                
                // 创建一个全局的文件处理函数
                window.handleFileUpload = function() {
                    if (window.fileUploadHandled) return;
                    
                    // 查找所有可能的文件输入框
                    const fileInputs = document.querySelectorAll('input[type="file"]');
                    console.log('Found file inputs:', fileInputs.length);
                    
                    for (let input of fileInputs) {
                        if (input.offsetParent === null || input.style.display === 'none') {
                            console.log('Found hidden file input:', input);
                            window.fileUploadHandled = true;
                            return input;
                        }
                    }
                    
                    // 在shadow DOM中查找
                    const wujieApp = document.querySelector('wujie-app');
                    if (wujieApp && wujieApp.shadowRoot) {
                        const shadowInputs = wujieApp.shadowRoot.querySelectorAll('input[type="file"]');
                        for (let input of shadowInputs) {
                            console.log('Found shadow file input:', input);
                            window.fileUploadHandled = true;
                            return input;
                        }
                    }
                    
                    return null;
                };
                
                // 监听DOM变化，捕获新添加的文件输入框
                const observer = new MutationObserver(function(mutations) {
                    mutations.forEach(function(mutation) {
                        if (mutation.type === 'childList') {
                            const addedNodes = Array.from(mutation.addedNodes);
                            addedNodes.forEach(node => {
                                if (node.nodeType === 1) { // Element node
                                    const fileInputs = node.querySelectorAll ? node.querySelectorAll('input[type="file"]') : [];
                                    if (fileInputs.length > 0) {
                                        console.log('Detected new file input via mutation observer');
                                        window.detectedFileInput = fileInputs[0];
                                    }
                                }
                            });
                        }
                    });
                });
                
                observer.observe(document.body, {
                    childList: true,
                    subtree: true
                });
                
                window.fileObserver = observer;
            '''
            
            await page.evaluate(script, actual_file_path)
            
            # 现在查找并点击上传区域，但不直接处理文件输入框
            upload_selectors = [
                'div.upload-content div.center',
                '.upload-content .center', 
                '.center',
                'span.weui-icon-outlined-add'
            ]
            
            clicked = False
            for selector in upload_selectors:
                try:
                    upload_element = await page.wait_for_selector(selector, timeout=3000)
                    if upload_element and await upload_element.is_visible():
                        tencent_logger.info(f"准备点击上传区域: {selector}")
                        
                        # 点击前先查找现有的文件输入框
                        existing_input = await page.evaluate('window.handleFileUpload()')
                        if existing_input:
                            tencent_logger.info("发现现有的文件输入框，直接使用")
                            file_input = await page.query_selector('input[type="file"]')
                            if file_input:
                                timeout = 300000 if is_large_file else 60000
                                await file_input.set_input_files(actual_file_path, timeout=timeout)
                                tencent_logger.success(f"直接设置文件成功: {os.path.basename(actual_file_path)}")
                                return
                        
                        # 如果没有现有输入框，点击上传区域
                        await upload_element.click()
                        clicked = True
                        tencent_logger.info(f"成功点击上传区域: {selector}")
                        break
                except Exception as e:
                    tencent_logger.debug(f"选择器 {selector} 失败: {str(e)}")
                    continue
            
            if clicked:
                # 点击后等待文件输入框出现
                max_wait = 10
                for i in range(max_wait):
                    await asyncio.sleep(1)
                    
                    # 检查是否有新的文件输入框被检测到
                    detected_input = await page.evaluate('window.detectedFileInput')
                    if detected_input:
                        tencent_logger.info("通过变化监听检测到新的文件输入框")
                        break
                    
                    # 或者直接查找文件输入框
                    file_inputs = await page.query_selector_all('input[type="file"]')
                    valid_inputs = []
                    for inp in file_inputs:
                        try:
                            # 检查输入框是否处于DOM中且可用
                            is_connected = await inp.evaluate('el => el.isConnected')
                            if is_connected:
                                valid_inputs.append(inp)
                        except:
                            continue
                    
                    if valid_inputs:
                        tencent_logger.info(f"找到 {len(valid_inputs)} 个有效的文件输入框")
                        # 使用最后一个（通常是最新的）
                        file_input = valid_inputs[-1]
                        try:
                            timeout = 300000 if is_large_file else 60000
                            await file_input.set_input_files(actual_file_path, timeout=timeout)
                            tencent_logger.success(f"文件上传成功: {os.path.basename(actual_file_path)}")
                            
                            # 清理观察器
                            await page.evaluate('if(window.fileObserver) window.fileObserver.disconnect()')
                            return
                        except Exception as e:
                            if "detached" in str(e):
                                tencent_logger.warning(f"输入框已分离，继续等待: {str(e)}")
                                continue
                            else:
                                raise e
                    
                    tencent_logger.info(f"等待文件输入框出现... ({i+1}/{max_wait})")
                
                # 清理观察器
                await page.evaluate('if(window.fileObserver) window.fileObserver.disconnect()')
                
        except Exception as e:
            tencent_logger.error(f"预注入方案失败: {str(e)}")
        
        # 方案2：使用页面脚本直接处理文件上传对话框
        try:
            tencent_logger.info("尝试页面脚本处理方案...")
            
            # 暂时阻止默认的文件选择对话框
            await page.evaluate('''
                // 重写 HTMLInputElement 的 click 方法
                const originalClick = HTMLInputElement.prototype.click;
                HTMLInputElement.prototype.click = function() {
                    if (this.type === 'file') {
                        console.log('File input click intercepted');
                        // 创建一个自定义事件而不是打开文件对话框
                        const event = new Event('click', { bubbles: true, cancelable: true });
                        this.dispatchEvent(event);
                        window.interceptedFileInput = this;
                        return false;
                    }
                    return originalClick.call(this);
                };
            ''')
            
            # 现在点击上传区域
            upload_element = await page.wait_for_selector('div.upload-content div.center', timeout=5000)
            if upload_element:
                await upload_element.click()
                tencent_logger.info("点击上传区域（已拦截文件对话框）")
                
                # 等待拦截的文件输入框
                await asyncio.sleep(2)
                
                # 检查是否拦截到了文件输入框
                intercepted = await page.evaluate('''
                    if (window.interceptedFileInput) {
                        return { success: true, inputFound: true };
                    }
                    return { success: false, inputFound: false };
                ''')
                
                if intercepted['inputFound']:
                    # 直接设置文件到拦截的输入框
                    result = await page.evaluate('''
                        (async () => {
                            const input = window.interceptedFileInput;
                            if (input && input.isConnected) {
                                // 创建文件对象（这次使用真实文件路径的引用）
                                const dataTransfer = new DataTransfer();
                                
                                // 触发change事件让应用知道文件已选择
                                const changeEvent = new Event('change', { bubbles: true });
                                input.dispatchEvent(changeEvent);
                                
                                return { success: true, method: 'intercepted' };
                            }
                            return { success: false, error: 'Input not connected' };
                        })()
                    ''')
                    
                    if result['success']:
                        tencent_logger.info("通过拦截方法触发了文件输入")
                        # 现在使用常规方法设置文件
                        file_input = await page.query_selector('input[type="file"]')
                        if file_input:
                            timeout = 300000 if is_large_file else 60000
                            await file_input.set_input_files(actual_file_path, timeout=timeout)
                            tencent_logger.success(f"拦截方案文件上传成功: {os.path.basename(actual_file_path)}")
                            return
            
        except Exception as e:
            tencent_logger.error(f"页面脚本处理方案失败: {str(e)}")
        
        # 如果所有方法都失败，提供详细的错误信息
        page_info = await page.evaluate('''
            () => {
                return {
                    url: window.location.href,
                    fileInputs: document.querySelectorAll('input[type="file"]').length,
                    uploadElements: document.querySelectorAll('.upload-content, .center').length,
                    shadowDom: !!document.querySelector('wujie-app')?.shadowRoot
                };
            }
        ''')
        
        error_msg = f"""所有文件上传方法都失败了！
    页面信息: {page_info}
    建议检查:
    1. 页面是否完全加载
    2. 网络连接是否正常  
    3. 文件路径是否正确: {actual_file_path}
    4. 文件大小是否超出限制: {file_size/1024/1024:.1f}MB"""
        
        raise Exception(error_msg)

    async def verify_upload_started(self, page):
        """验证文件上传是否真正开始"""
        try:
            # 等待上传开始的迹象
            await asyncio.sleep(3)
            
            # 检查是否有上传进度相关的元素出现
            upload_indicators = [
                '.upload-progress',
                '.progress',
                '[class*="progress"]',
                '.uploading',
                '[class*="upload"][class*="ing"]',
                '.status-msg'
            ]
            
            upload_started = False
            for indicator in upload_indicators:
                try:
                    element = await page.wait_for_selector(indicator, timeout=5000)
                    if element:
                        text = await element.inner_text()
                        tencent_logger.info(f"检测到上传指示器: {indicator} - {text}")
                        upload_started = True
                        break
                except:
                    continue
            
            # 还可以通过检查页面变化来确认
            if not upload_started:
                # 检查上传区域是否变化
                upload_area = await page.query_selector('div.upload-content div.center')
                if upload_area:
                    is_visible = await upload_area.is_visible()
                    if not is_visible:
                        upload_started = True
                        tencent_logger.info("上传区域已隐藏，确认上传开始")
            
            # 检查发表按钮状态变化
            if not upload_started:
                try:
                    publish_btn = page.get_by_role("button", name="发表")
                    btn_class = await publish_btn.get_attribute('class')
                    if "weui-desktop-btn_disabled" in btn_class:
                        upload_started = True
                        tencent_logger.info("发表按钮已禁用，确认上传开始")
                except:
                    pass
            
            return upload_started
            
        except Exception as e:
            tencent_logger.warning(f"验证上传状态时出错: {str(e)}")
            return False

    async def detect_upload_status(self, page):
        """检测上传状态 - 针对大文件优化版本"""
        file_size = os.path.getsize(self.file_path)
        is_large_file = file_size > 100 * 1024 * 1024
        
        # 大文件需要更长的检测间隔和超时时间
        check_interval = 5 if is_large_file else 2
        max_wait_time = 1800 if is_large_file else 600  # 30分钟 vs 10分钟
        start_time = asyncio.get_event_loop().time()
        
        while True:
            current_time = asyncio.get_event_loop().time()
            if current_time - start_time > max_wait_time:
                raise Exception(f"上传超时：超过 {max_wait_time/60:.1f} 分钟")
            
            try:
                # 检查发表按钮状态
                publish_btn = page.get_by_role("button", name="发表")
                btn_class = await publish_btn.get_attribute('class')
                
                if "weui-desktop-btn_disabled" not in btn_class:
                    tencent_logger.info("  [-]视频上传完毕")
                    break
                else:
                    elapsed = int(current_time - start_time)
                    if is_large_file:
                        tencent_logger.info(f"  [-] 正在上传大文件中... (已等待 {elapsed//60}分{elapsed%60}秒)")
                    else:
                        tencent_logger.info(f"  [-] 正在上传视频中... (已等待 {elapsed}秒)")
                    
                    await asyncio.sleep(check_interval)
                    
                    # 检查是否有错误状态
                    error_element = page.locator('div.status-msg.error')
                    delete_button = page.locator('div.media-status-content div.tag-inner:has-text("删除")')
                    
                    if await error_element.count() and await delete_button.count():
                        tencent_logger.error("  [-] 发现上传出错了...准备重试")
                        await self.handle_upload_error(page)
                        start_time = asyncio.get_event_loop().time()  # 重置计时器
                        
            except Exception as e:
                elapsed = int(current_time - start_time)
                if is_large_file:
                    tencent_logger.info(f"  [-] 正在上传大文件中... (已等待 {elapsed//60}分{elapsed%60}秒)")
                else:
                    tencent_logger.info(f"  [-] 正在上传视频中... (已等待 {elapsed}秒)")
                await asyncio.sleep(check_interval)

    async def add_short_title(self, page):
        short_title_element = page.get_by_text("短标题", exact=True).locator("..").locator(
            "xpath=following-sibling::div").locator(
            'span input[type="text"]')
        if await short_title_element.count():
            short_title = format_str_for_short_title(self.title)
            await short_title_element.fill(short_title)

    async def click_publish(self, page):
        while True:
            try:
                publish_buttion = page.locator('div.form-btns button:has-text("发表")')
                if await publish_buttion.count():
                    await publish_buttion.click()
                await page.wait_for_url("https://channels.weixin.qq.com/platform/post/list", timeout=5000)
                tencent_logger.success("  [-]视频发布成功")
                break
            except Exception as e:
                current_url = page.url
                if "https://channels.weixin.qq.com/platform/post/list" in current_url:
                    tencent_logger.success("  [-]视频发布成功")
                    break
                else:
                    tencent_logger.exception(f"  [-] Exception: {e}")
                    tencent_logger.info("  [-] 视频正在发布中...")
                    await asyncio.sleep(0.5)

    async def detect_upload_status(self, page):
        while True:
            # 匹配删除按钮，代表视频上传完毕，如果不存在，代表视频正在上传，则等待
            try:
                # 匹配删除按钮，代表视频上传完毕
                if "weui-desktop-btn_disabled" not in await page.get_by_role("button", name="发表").get_attribute(
                        'class'):
                    tencent_logger.info("  [-]视频上传完毕")
                    break
                else:
                    tencent_logger.info("  [-] 正在上传视频中...")
                    await asyncio.sleep(2)
                    # 出错了视频出错
                    if await page.locator('div.status-msg.error').count() and await page.locator(
                            'div.media-status-content div.tag-inner:has-text("删除")').count():
                        tencent_logger.error("  [-] 发现上传出错了...准备重试")
                        await self.handle_upload_error(page)
            except:
                tencent_logger.info("  [-] 正在上传视频中...")
                await asyncio.sleep(2)

    async def add_title_tags(self, page):
        await page.locator("div.input-editor").click()
        await page.keyboard.type(self.title)
        await page.keyboard.press("Enter")
        for index, tag in enumerate(self.tags, start=1):
            await page.keyboard.type("#" + tag)
            await page.keyboard.press("Space")
        tencent_logger.info(f"成功添加hashtag: {len(self.tags)}")

    async def add_collection(self, page):
        collection_elements = page.get_by_text("添加到合集").locator("xpath=following-sibling::div").locator(
            '.option-list-wrap > div')
        if await collection_elements.count() > 1:
            await page.get_by_text("添加到合集").locator("xpath=following-sibling::div").click()
            await collection_elements.first.click()

    async def add_original(self, page):
        if await page.get_by_label("视频为原创").count():
            await page.get_by_label("视频为原创").check()
        # 检查 "我已阅读并同意 《视频号原创声明使用条款》" 元素是否存在
        label_locator = await page.locator('label:has-text("我已阅读并同意 《视频号原创声明使用条款》")').is_visible()
        if label_locator:
            await page.get_by_label("我已阅读并同意 《视频号原创声明使用条款》").check()
            await page.get_by_role("button", name="声明原创").click()
        # 2023年11月20日 wechat更新: 可能新账号或者改版账号，出现新的选择页面
        if await page.locator('div.label span:has-text("声明原创")').count() and self.category:
            # 因处罚无法勾选原创，故先判断是否可用
            if not await page.locator('div.declare-original-checkbox input.ant-checkbox-input').is_disabled():
                await page.locator('div.declare-original-checkbox input.ant-checkbox-input').click()
                if not await page.locator(
                        'div.declare-original-dialog label.ant-checkbox-wrapper.ant-checkbox-wrapper-checked:visible').count():
                    await page.locator('div.declare-original-dialog input.ant-checkbox-input:visible').click()
            if await page.locator('div.original-type-form > div.form-label:has-text("原创类型"):visible').count():
                await page.locator('div.form-content:visible').click()  # 下拉菜单
                await page.locator(
                    f'div.form-content:visible ul.weui-desktop-dropdown__list li.weui-desktop-dropdown__list-ele:has-text("{self.category}")').first.click()
                await page.wait_for_timeout(1000)
            if await page.locator('button:has-text("声明原创"):visible').count():
                await page.locator('button:has-text("声明原创"):visible').click()

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

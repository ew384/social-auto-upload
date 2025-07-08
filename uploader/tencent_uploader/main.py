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

    async def upload_file_to_shadow_dom(self, page):
        """简化版本 - 直接参考成功的render.ts逻辑"""
        await page.wait_for_selector('wujie-app', timeout=30000)
        await asyncio.sleep(2)
        
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
        
        tencent_logger.info(f"准备上传文件: {actual_file_path}")
        
        # 读取文件为binary buffer
        with open(actual_file_path, 'rb') as f:
            file_buffer = f.read()
        
        file_name = os.path.basename(actual_file_path)
        file_size = len(file_buffer)
        
        tencent_logger.info(f"文件读取完成: {file_name}, 大小: {file_size} bytes")
        
        # 直接参考成功代码的核心逻辑
        upload_script = f'''
        (async function() {{
            try {{
                console.log("=== 开始上传流程 ===");
                
                // 步骤1: 查找shadow DOM - 完全按照成功代码的方式
                const shadowm = document.querySelector('.wujie_iframe');
                if (!shadowm) {{
                    console.log("未找到 .wujie_iframe");
                    return {{ success: false, error: '未找到 .wujie_iframe' }};
                }}
                console.log("✓ 找到 .wujie_iframe");
                
                if (!shadowm.shadowRoot) {{
                    console.log("shadowRoot 不存在");
                    return {{ success: false, error: 'shadowRoot 不存在' }};
                }}
                console.log("✓ shadowRoot 存在");
                
                // 步骤2: 查找上传区域 - 完全按照成功代码
                const videoDom = shadowm.shadowRoot.querySelector('.upload');
                if (!videoDom) {{
                    console.log("未找到 .upload 元素");
                    return {{ success: false, error: '未找到 .upload 元素' }};
                }}
                console.log("✓ 找到 .upload 元素");
                
                // 步骤3: 查找文件输入框 - 完全按照成功代码
                const inputDom = videoDom.querySelector('input[type="file"]');
                if (!inputDom) {{
                    console.log("未找到文件输入框");
                    return {{ success: false, error: '未找到文件输入框' }};
                }}
                console.log("✓ 找到文件输入框");
                
                // 步骤4: 创建文件对象 - 使用成功代码的方式
                console.log("开始创建文件对象...");
                const uint8Array = new Uint8Array({list(file_buffer)});
                console.log("✓ Uint8Array 创建完成, 长度:", uint8Array.length);
                
                const file = new File([uint8Array], '{file_name}', {{
                    type: 'video/avi',
                    lastModified: Date.now()
                }});
                console.log("✓ File对象创建完成:", file.name, file.size, file.type);
                
                // 步骤5: 使用DataTransfer - 完全按照成功代码的方式
                const files = new DataTransfer();
                files.items.add(file);
                console.log("✓ DataTransfer 创建完成");
                
                // 步骤6: 设置files属性 - 核心步骤，完全按照成功代码
                Object.defineProperty(inputDom, 'files', {{
                    value: files.files,
                    configurable: true
                }});
                console.log("✓ files 属性设置完成");
                
                // 步骤7: 触发change事件 - 完全按照成功代码的方式
                const changeEvent = new Event('change', {{ bubbles: true }});
                inputDom.dispatchEvent(changeEvent);
                console.log("✓ change事件触发完成");
                
                // 等待一下
                await new Promise(resolve => setTimeout(resolve, 1000));
                console.log("=== 上传流程完成 ===");
                
                return {{ 
                    success: true, 
                    fileName: '{file_name}',
                    fileSize: uint8Array.length
                }};
                
            }} catch (e) {{
                console.error("上传过程出错:", e.message);
                console.error("错误堆栈:", e.stack);
                return {{ success: false, error: e.message, stack: e.stack }};
            }}
        }})()
        '''
        
        tencent_logger.info("开始执行JavaScript上传脚本...")
        
        try:
            result = await page.evaluate(upload_script)
            tencent_logger.info(f"JavaScript执行结果: {result}")
            
            if not result['success']:
                raise Exception(f"JavaScript上传失败: {result.get('error', 'Unknown error')}")
            
            tencent_logger.success(f"文件上传成功: {result['fileName']}")
            
            # 立即检查上传是否开始
            await asyncio.sleep(2)
            await self.check_upload_started(page)
            
        except Exception as e:
            tencent_logger.error(f"JavaScript执行异常: {str(e)}")
            raise


    async def check_upload_started(self, page):
        """检查上传是否真的开始了"""
        check_script = '''
        (function() {
            try {
                const shadowm = document.querySelector('.wujie_iframe');
                if (!shadowm || !shadowm.shadowRoot) {
                    return { started: false, reason: 'no shadow DOM' };
                }
                
                const shadowDoc = shadowm.shadowRoot;
                
                // 检查是否有任何变化
                const checks = {
                    hasVideo: !!shadowDoc.querySelector('video'),
                    hasProgress: !!shadowDoc.querySelector('.progress'),
                    hasUploading: !!shadowDoc.querySelector('[class*="upload"]'),
                    hasStatus: !!shadowDoc.querySelector('[class*="status"]'),
                    inputFiles: shadowDoc.querySelector('input[type="file"]')?.files?.length || 0
                };
                
                const started = checks.hasVideo || checks.hasProgress || checks.inputFiles > 0;
                
                return {
                    started: started,
                    checks: checks,
                    reason: started ? 'upload detected' : 'no upload signs'
                };
                
            } catch (e) {
                return { started: false, reason: e.message };
            }
        })()
        '''
        
        result = await page.evaluate(check_script)
        tencent_logger.info(f"上传状态检查: {result}")
        
        if not result['started']:
            tencent_logger.warning(f"上传可能未开始: {result['reason']}")
        else:
            tencent_logger.success("上传已开始!")

    # 添加一个简单的上传状态检查方法
    async def check_if_uploading_simple(self, page):
        """简单检查是否在上传 - 避免复杂选择器"""
        
        simple_check = '''
        (function() {
            try {
                // 1. 检查shadow DOM中的视频和进度
                const shadowm = document.querySelector('.wujie_iframe');
                let shadowInfo = { found: false };
                
                if (shadowm && shadowm.shadowRoot) {
                    const shadowDoc = shadowm.shadowRoot;
                    shadowInfo = {
                        found: true,
                        hasVideo: shadowDoc.querySelector('video') !== null,
                        hasProgress: shadowDoc.querySelector('.progress') !== null,
                        inputHasFiles: shadowDoc.querySelector('input[type="file"]')?.files?.length > 0
                    };
                }
                
                // 2. 检查发布按钮状态 - 使用原始代码的方式
                let buttonInfo = { found: false };
                try {
                    const button = document.querySelector('div.form-btns button') ||
                                document.querySelector('.weui-desktop-btn');
                    if (button) {
                        buttonInfo = {
                            found: true,
                            disabled: button.disabled,
                            className: button.className,
                            text: button.textContent
                        };
                    }
                } catch (e) {
                    // 按钮查找失败，忽略
                }
                
                // 3. 检查网络活动
                const resources = performance.getEntriesByType('resource');
                const recentUploads = resources.filter(r => 
                    (r.name.includes('upload') || r.name.includes('mmfinder')) && 
                    (Date.now() - r.startTime < 60000) // 最近1分钟
                );
                
                return {
                    success: true,
                    timestamp: Date.now(),
                    shadow: shadowInfo,
                    button: buttonInfo,
                    recentUploads: recentUploads.length,
                    isUploading: shadowInfo.hasVideo || shadowInfo.hasProgress || 
                                shadowInfo.inputHasFiles || recentUploads.length > 0
                };
                
            } catch (e) {
                return { success: false, error: e.message };
            }
        })()
        '''
        
        try:
            result = await page.evaluate(simple_check)
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}


    # 更新监控方法
    async def monitor_upload_simple(self, page, duration_minutes=5):
        """简单监控上传状态"""
        tencent_logger.info(f"开始监控上传状态 {duration_minutes} 分钟...")
        
        checks_per_minute = 6  # 每10秒检查一次
        total_checks = duration_minutes * checks_per_minute
        
        for i in range(total_checks):
            status = await self.check_if_uploading_simple(page)
            
            if status['success']:
                shadow = status['shadow']
                button = status['button']
                is_uploading = status['isUploading']
                recent_uploads = status['recentUploads']
                
                # 格式化输出
                shadow_status = f"视频={shadow.get('hasVideo', False)}, 进度={shadow.get('hasProgress', False)}, 文件={shadow.get('inputHasFiles', False)}"
                button_status = f"按钮={'禁用' if button.get('disabled') else '启用'}" if button.get('found') else "按钮未找到"
                
                tencent_logger.info(f"监控 {i+1}/{total_checks}: {shadow_status}, {button_status}, 网络请求={recent_uploads}")
                
                if is_uploading:
                    tencent_logger.success("✅ 检测到上传活动!")
                    
                    # 检测到上传后，减少检查频率
                    if i > 0 and i % 12 == 0:  # 每2分钟报告一次
                        tencent_logger.info(f"上传进行中... ({i//6}分钟)")
                else:
                    if i < 6:  # 前1分钟
                        tencent_logger.info("🔍 等待上传开始...")
                    elif i < 18:  # 前3分钟
                        tencent_logger.warning("⚠️ 仍未检测到上传活动")
                    else:  # 3分钟后
                        tencent_logger.error("❌ 可能上传失败或未开始")
            else:
                tencent_logger.warning(f"状态检查失败: {status.get('error')}")
            
            await asyncio.sleep(10)  # 每10秒检查一次
        
        tencent_logger.info("监控结束")


    # 立即检查当前状态的方法
    async def check_current_status_now(self, page):
        """立即检查当前状态"""
        tencent_logger.info("=== 立即检查当前状态 ===")
        
        status = await self.check_if_uploading_simple(page)
        
        if status['success']:
            shadow = status['shadow']
            button = status['button']
            
            tencent_logger.info(f"Shadow DOM: {shadow}")
            tencent_logger.info(f"按钮状态: {button}")
            tencent_logger.info(f"最近网络请求: {status['recentUploads']}")
            tencent_logger.info(f"是否正在上传: {status['isUploading']}")
            
            if status['isUploading']:
                tencent_logger.success("🎉 上传正在进行中!")
                return True
            else:
                tencent_logger.warning("❌ 未检测到上传活动")
                return False
        else:
            tencent_logger.error(f"状态检查失败: {status['error']}")
            return False


    async def upload_file_to_shadow_dom(self, page):
        """简化的文件上传方法"""
        await page.wait_for_selector('wujie-app', timeout=30000)
        await asyncio.sleep(2)
        
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
        
        tencent_logger.info(f"准备上传文件: {actual_file_path}")
        
        # 读取文件
        with open(actual_file_path, 'rb') as f:
            file_buffer = f.read()
        
        file_name = os.path.basename(actual_file_path)
        tencent_logger.info(f"文件读取完成: {file_name}, 大小: {len(file_buffer)} bytes")
        
        # 上传脚本
        upload_script = f'''
        (async function() {{
            try {{
                console.log("=== 开始上传 ===");
                
                const shadowm = document.querySelector('.wujie_iframe');
                if (!shadowm?.shadowRoot) {{
                    return {{ success: false, error: '未找到shadow DOM' }};
                }}
                
                const videoDom = shadowm.shadowRoot.querySelector('.upload');
                if (!videoDom) {{
                    return {{ success: false, error: '未找到.upload' }};
                }}
                
                const inputDom = videoDom.querySelector('input[type="file"]');
                if (!inputDom) {{
                    return {{ success: false, error: '未找到input' }};
                }}
                
                console.log("DOM元素检查完成");
                
                const uint8Array = new Uint8Array({list(file_buffer)});
                console.log("Uint8Array创建完成, 长度:", uint8Array.length);
                
                const file = new File([uint8Array], '{file_name}', {{
                    type: 'video/avi',
                    lastModified: Date.now()
                }});
                
                const files = new DataTransfer();
                files.items.add(file);
                
                Object.defineProperty(inputDom, 'files', {{
                    value: files.files,
                    configurable: true
                }});
                
                inputDom.dispatchEvent(new Event('change', {{ bubbles: true }}));
                console.log("=== 上传触发完成 ===");
                
                return {{ success: true, fileName: '{file_name}' }};
                
            }} catch (e) {{
                console.error("上传失败:", e);
                return {{ success: false, error: e.message }};
            }}
        }})()
        '''
        
        tencent_logger.info("开始执行JavaScript上传脚本...")
        
        try:
            # 设置60秒超时，给大文件更多时间
            result = await asyncio.wait_for(page.evaluate(upload_script), timeout=60.0)
            
            if not result['success']:
                raise Exception(f"上传失败: {result.get('error')}")
            
            tencent_logger.success("上传脚本执行成功!")
            
        except asyncio.TimeoutError:
            tencent_logger.warning("JavaScript执行超时，但可能仍在后台处理...")
            # 不要失败，继续监控
        except Exception as e:
            tencent_logger.error(f"JavaScript执行失败: {e}")
            raise


    # ==== 3. 添加简单的检查方法 ====
    async def check_if_uploading_simple(self, page):
        """简单检查是否在上传"""
        simple_check = '''
        (function() {
            try {
                const shadowm = document.querySelector('.wujie_iframe');
                let shadowInfo = { found: false };
                
                if (shadowm && shadowm.shadowRoot) {
                    const shadowDoc = shadowm.shadowRoot;
                    shadowInfo = {
                        found: true,
                        hasVideo: shadowDoc.querySelector('video') !== null,
                        hasProgress: shadowDoc.querySelector('.progress') !== null,
                        inputHasFiles: shadowDoc.querySelector('input[type="file"]')?.files?.length > 0
                    };
                }
                
                let buttonInfo = { found: false };
                try {
                    const button = document.querySelector('div.form-btns button') ||
                                document.querySelector('.weui-desktop-btn');
                    if (button) {
                        buttonInfo = {
                            found: true,
                            disabled: button.disabled,
                            className: button.className
                        };
                    }
                } catch (e) {
                    // 忽略
                }
                
                const resources = performance.getEntriesByType('resource');
                const recentUploads = resources.filter(r => 
                    (r.name.includes('upload') || r.name.includes('mmfinder')) && 
                    (Date.now() - r.startTime < 60000)
                );
                
                return {
                    success: true,
                    shadow: shadowInfo,
                    button: buttonInfo,
                    recentUploads: recentUploads.length,
                    isUploading: shadowInfo.hasVideo || shadowInfo.hasProgress || 
                                shadowInfo.inputHasFiles || recentUploads.length > 0
                };
                
            } catch (e) {
                return { success: false, error: e.message };
            }
        })()
        '''
        
        try:
            result = await page.evaluate(simple_check)
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}


    # ==== 4. 修改主upload方法 ====
    async def upload(self, playwright: Playwright) -> None:
        """主上传方法"""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"文件不存在: {self.file_path}")
        
        file_size_mb = os.path.getsize(self.file_path) / (1024 * 1024)
        tencent_logger.info(f"视频文件大小: {file_size_mb:.2f}MB")
        
        browser = await playwright.chromium.launch(
            headless=False, 
            executable_path=self.local_executable_path
        )
        
        try:
            context = await browser.new_context(storage_state=f"{self.account_file}")
            context = await set_init_script(context)
            page = await context.new_page()
            
            # 网络监控 - 只监控上传相关请求
            page.on("request", lambda req: tencent_logger.info(f"🌐 请求: {req.method} {req.url}") 
                    if 'upload' in req.url or 'mmfinder' in req.url else None)
            page.on("response", lambda res: tencent_logger.info(f"📥 响应: {res.status} {res.url}") 
                    if 'upload' in res.url or 'mmfinder' in res.url else None)
            
            await page.goto("https://channels.weixin.qq.com/platform/post/create")
            tencent_logger.info(f'[+]正在上传-------{self.title}')
            
            await page.wait_for_url("https://channels.weixin.qq.com/platform/post/create")
            await page.wait_for_selector('.wujie_iframe', timeout=30000)
            await asyncio.sleep(3)
            
            # 上传文件
            await self.upload_file_to_shadow_dom(page)
            
            # 立即开始监控上传状态
            tencent_logger.info("开始监控上传状态...")
            upload_detected = False
            
            # 监控5分钟
            for i in range(30):  # 30次检查，每次10秒
                await asyncio.sleep(10)
                
                status = await self.check_if_uploading_simple(page)
                
                if status['success']:
                    shadow = status['shadow']
                    button = status['button']
                    recent_uploads = status['recentUploads']
                    
                    # 状态报告
                    if shadow['hasVideo']:
                        tencent_logger.success(f"✅ 检测到视频! (检查 {i+1}/30)")
                        upload_detected = True
                    elif shadow['hasProgress']:
                        tencent_logger.success(f"✅ 检测到进度条! (检查 {i+1}/30)")
                        upload_detected = True
                    elif shadow['inputHasFiles']:
                        tencent_logger.info(f"📁 文件已选中 (检查 {i+1}/30)")
                        upload_detected = True
                    elif recent_uploads > 0:
                        tencent_logger.info(f"🌐 网络活动 {recent_uploads} 个请求 (检查 {i+1}/30)")
                        upload_detected = True
                    else:
                        tencent_logger.info(f"🔍 等待上传... (检查 {i+1}/30)")
                    
                    # 检查按钮状态
                    if button['found'] and not button['disabled']:
                        tencent_logger.success("✅ 发布按钮已启用，上传可能完成!")
                        break
                        
                else:
                    tencent_logger.warning(f"状态检查失败: {status.get('error')}")
            
            if not upload_detected:
                tencent_logger.error("❌ 5分钟内未检测到上传活动")
                raise Exception("上传可能失败")
            
            # 继续后续流程
            await self.add_title_tags(page)
            await self.detect_upload_status_improved(page)
            await self.click_publish(page)
            
            await context.storage_state(path=f"{self.account_file}")
            tencent_logger.success('上传完成!')
            
        finally:
            try:
                await context.close()
                await browser.close()
            except:
                pass


    # ==== 5. 保留原有的其他方法 ====
    async def add_title_tags(self, page):
        """添加标题和标签"""
        try:
            await page.wait_for_selector("div.input-editor", timeout=10000)
            await page.locator("div.input-editor").click()
            await page.keyboard.type(self.title)
            await page.keyboard.press("Enter")
            
            for tag in self.tags:
                await page.keyboard.type("#" + tag)
                await page.keyboard.press("Space")
            
            tencent_logger.info(f"标题和标签添加完成")
            
        except Exception as e:
            tencent_logger.warning(f"添加标题失败: {e}")


    async def detect_upload_status_improved(self, page):
        """检测上传完成"""
        max_wait = 300  # 5分钟
        start_time = asyncio.get_event_loop().time()
        
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait:
                raise Exception("上传超时")
            
            try:
                button = page.get_by_role("button", name="发表")
                button_class = await button.get_attribute('class')
                
                if "weui-desktop-btn_disabled" not in button_class:
                    tencent_logger.success("上传完成!")
                    break
                
                tencent_logger.info(f"上传中... ({elapsed/60:.1f}分钟)")
                await asyncio.sleep(10)
                
            except Exception as e:
                tencent_logger.warning(f"状态检测异常: {e}")
                await asyncio.sleep(5)


    async def click_publish(self, page):
        """发布视频"""
        try:
            publish_button = page.locator('div.form-btns button:has-text("发表")')
            await publish_button.click()
            await page.wait_for_url("https://channels.weixin.qq.com/platform/post/list", timeout=10000)
            tencent_logger.success("发布成功!")
        except Exception as e:
            tencent_logger.error(f"发布失败: {e}")
            raise

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

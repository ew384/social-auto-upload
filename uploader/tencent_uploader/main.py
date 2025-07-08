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

    async def upload_file_to_shadow_dom_fixed(self, page):
        """修复的文件上传方法 - 使用Playwright原生上传，避免大文件内存问题"""
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
        
        file_size_mb = os.path.getsize(actual_file_path) / (1024 * 1024)
        tencent_logger.info(f"文件大小: {file_size_mb:.2f}MB")
        
        # 方法1: 使用locator操作（之前成功的方案3，现在前置为方案1）
        try:
            tencent_logger.info("尝试方法1: 使用locator操作")
            
            # 等待并点击shadow DOM中的文件输入
            file_input = page.locator('wujie-app').locator('input[type="file"]')
            await file_input.set_input_files(actual_file_path, timeout=30000)
            
            tencent_logger.success(f"方法1成功: 文件已设置")
            return True
            
        except Exception as e:
            tencent_logger.warning(f"方法1失败: {e}")
        
        # 方法2: 完全参考成功产品的代码逻辑
        try:
            tencent_logger.info("方法2: 参考成功产品代码的上传方式")
            
            # 完全按照参考代码的逻辑和选择器
            reference_upload_script = '''
            (async function() {
                try {
                    // 步骤1: 查找 shadow DOM - 完全按照参考代码
                    const shadowm = document.querySelector('.wujie_iframe');
                    if (!shadowm) {
                        return { success: false, error: '未找到 .wujie_iframe' };
                    }
                    
                    if (!shadowm.shadowRoot) {
                        return { success: false, error: 'shadowRoot 不存在' };
                    }
                    
                    // 步骤2: 查找上传区域 - 完全按照参考代码
                    const videoDom = shadowm.shadowRoot.querySelector('.upload');
                    if (!videoDom) {
                        return { success: false, error: '未找到 .upload 元素' };
                    }
                    
                    // 步骤3: 查找文件输入框 - 完全按照参考代码
                    const inputDom = videoDom.querySelector('input[type="file"]');
                    if (!inputDom) {
                        return { success: false, error: '未找到文件输入框' };
                    }
                    
                    // 直接触发点击，让浏览器打开文件选择器
                    inputDom.click();
                    console.log("已触发文件选择器");
                    
                    return { success: true };
                    
                } catch (e) {
                    return { success: false, error: e.message };
                }
            })()
            '''
            
            # 监听文件选择器并设置文件
            async with page.expect_file_chooser(timeout=10000) as fc_info:
                result = await page.evaluate(reference_upload_script)
                if not result['success']:
                    raise Exception(f"参考代码方式失败: {result['error']}")
            
            file_chooser = await fc_info.value
            await file_chooser.set_files(actual_file_path)
            
            tencent_logger.success(f"方法2成功: 文件已选择")
            return True
            
        except Exception as e:
            tencent_logger.warning(f"方法2失败: {e}")
        
        # 方法3: 点击上传区域触发文件选择器（备用方案）
        try:
            tencent_logger.info("尝试方法3: 点击上传区域触发文件选择器")
            
            click_script = '''
            (function() {
                try {
                    const shadowm = document.querySelector('.wujie_iframe');
                    if (!shadowm || !shadowm.shadowRoot) {
                        return { success: false, error: '未找到shadow DOM' };
                    }
                    
                    // 尝试多种可能的上传区域
                    const selectors = ['.upload', '.center', '[class*="upload"]', '[class*="center"]'];
                    
                    for (const selector of selectors) {
                        const element = shadowm.shadowRoot.querySelector(selector);
                        if (element) {
                            element.click();
                            console.log(`已点击 ${selector} 区域`);
                            return { success: true };
                        }
                    }
                    
                    return { success: false, error: '未找到任何上传区域' };
                    
                } catch (e) {
                    return { success: false, error: e.message };
                }
            })()
            '''
            
            async with page.expect_file_chooser(timeout=10000) as fc_info:
                result = await page.evaluate(click_script)
                if not result['success']:
                    raise Exception(f"点击上传区域失败: {result['error']}")
            
            file_chooser = await fc_info.value
            await file_chooser.set_files(actual_file_path)
            
            tencent_logger.success(f"方法3成功: 文件已选择")
            return True
            
        except Exception as e:
            tencent_logger.warning(f"方法3失败: {e}")
        
        raise Exception("所有上传方法都失败")


    async def verify_upload_started(self, page):
        """验证上传是否真正开始"""
        tencent_logger.info("验证上传是否开始...")
        
        # 等待几秒让文件处理开始
        await asyncio.sleep(5)
        
        verify_script = '''
        (function() {
            try {
                const shadowm = document.querySelector('.wujie_iframe');
                if (!shadowm || !shadowm.shadowRoot) {
                    return { started: false, reason: 'no shadow DOM' };
                }
                
                const shadowDoc = shadowm.shadowRoot;
                const fileInput = shadowDoc.querySelector('input[type="file"]');
                const fileCount = fileInput ? fileInput.files.length : 0;
                
                // 检查各种上传指示器
                const hasVideo = !!shadowDoc.querySelector('video');
                const hasProgress = !!shadowDoc.querySelector('.progress');
                const hasLoading = !!shadowDoc.querySelector('[class*="loading"]');
                
                return {
                    started: fileCount > 0 || hasVideo || hasProgress || hasLoading,
                    details: {
                        fileCount: fileCount,
                        hasVideo: hasVideo,
                        hasProgress: hasProgress,
                        hasLoading: hasLoading
                    }
                };
                
            } catch (e) {
                return { started: false, reason: e.message };
            }
        })()
        '''
        
        result = await page.evaluate(verify_script)
        
        if result['started']:
            details = result['details']
            tencent_logger.success(f"✅ 上传已开始! 文件数:{details['fileCount']}, 视频:{details['hasVideo']}, 进度:{details['hasProgress']}")
            return True
        else:
            tencent_logger.warning(f"❌ 上传可能未开始: {result.get('reason')}")
            return False


    async def upload(self, playwright: Playwright) -> None:
        """修复的主上传方法"""
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
            
            # 网络监控
            page.on("request", lambda req: tencent_logger.info(f"🌐 请求: {req.method} {req.url}") 
                    if any(keyword in req.url for keyword in ['upload', 'mmfinder', 'loadChunk']) else None)
            page.on("response", lambda res: tencent_logger.info(f"📥 响应: {res.status} {res.url}") 
                    if any(keyword in res.url for keyword in ['upload', 'mmfinder', 'loadChunk']) else None)
            
            await page.goto("https://channels.weixin.qq.com/platform/post/create")
            tencent_logger.info(f'[+]正在上传-------{self.title}')
            
            await page.wait_for_url("https://channels.weixin.qq.com/platform/post/create")
            await page.wait_for_selector('.wujie_iframe', timeout=30000)
            await asyncio.sleep(3)
            
            # 使用修复的上传方法
            await self.upload_file_to_shadow_dom_fixed(page)
            
            # 验证上传开始
            upload_started = await self.verify_upload_started(page)
            if not upload_started:
                raise Exception("文件上传验证失败")
            
            # 等待处理完成并继续流程
            tencent_logger.info("等待视频处理完成...")
            await asyncio.sleep(10)  # 给视频处理一些时间
            
            # 继续其他步骤
            await self.add_title_tags(page)
            await self.detect_upload_status_no_timeout(page)
            await self.click_publish(page)
            
            await context.storage_state(path=f"{self.account_file}")
            tencent_logger.success('上传完成!')
            
        finally:
            try:
                await context.close()
                await browser.close()
            except:
                pass
    
    async def detect_upload_status_no_timeout(self, page):
        """无超时版本 - 持续等待直到上传完成"""
        start_time = asyncio.get_event_loop().time()
        
        tencent_logger.info("开始检测上传状态（无超时限制）")
        
        while True:
            try:
                elapsed = asyncio.get_event_loop().time() - start_time
                
                # 检查发布按钮状态
                button = page.get_by_role("button", name="发表")
                button_class = await button.get_attribute('class')
                
                if "weui-desktop-btn_disabled" not in button_class:
                    tencent_logger.success("✅ 上传完成!")
                    break
                
                # 每5分钟报告一次进度
                if int(elapsed) % 300 == 0 and elapsed > 0:
                    tencent_logger.info(f"⏳ 上传中... ({elapsed/60:.1f}分钟)")
                
                await asyncio.sleep(15)  # 每15秒检查一次
                
            except Exception as e:
                tencent_logger.warning(f"状态检测异常: {e}")
                await asyncio.sleep(15)
        
        tencent_logger.info("上传检测完成")

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

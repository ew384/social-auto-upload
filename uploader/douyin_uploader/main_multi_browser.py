# 创建新文件: uploader/douyin_uploader/main_multi_browser.py

import asyncio
import os
import time
from datetime import datetime
from pathlib import Path
from utils.browser_adapter import MultiAccountBrowserAdapter
from utils.log import douyin_logger

class DouYinVideoMultiBrowser:
    """使用 multi-account-browser 的抖音视频上传器"""
    
    def __init__(self, title, file_path, tags, publish_date, account_file, thumbnail_path=None):
        self.title = title
        self.file_path = file_path
        self.tags = tags if isinstance(tags, list) else []
        self.publish_date = publish_date
        self.account_file = account_file
        self.thumbnail_path = thumbnail_path
        self.adapter = MultiAccountBrowserAdapter()
        self.tab_id = None
        self.account_name = f"douyin_upload_{int(time.time())}"
    
    async def upload(self):
        """主上传流程"""
        try:
            douyin_logger.info(f'🚀 开始上传视频: {self.title}')
            
            # 1. 创建上传标签页
            await self.create_upload_tab()
            
            # 2. 加载账号cookies
            await self.load_account_cookies()
            
            # 3. 导航到上传页面
            await self.navigate_to_upload_page()
            
            # 4. 处理文件上传
            await self.handle_file_upload()
            
            # 5. 填写视频信息
            await self.fill_video_info()
            
            # 6. 等待视频处理完成
            await self.wait_for_video_processing()
            
            # 7. 设置发布时间（如果需要）
            if self.publish_date and isinstance(self.publish_date, datetime):
                await self.set_schedule_time()
            
            # 8. 发布视频
            await self.publish_video()
            
            # 9. 保存更新的cookies
            await self.save_updated_cookies()
            
            douyin_logger.success(f'✅ 视频上传成功: {self.title}')
            
        except Exception as e:
            douyin_logger.error(f'❌ 视频上传失败: {e}')
            raise
        finally:
            # 清理资源
            if self.tab_id:
                try:
                    await self.adapter.close_tab(self.tab_id)
                except:
                    pass
    
    async def create_upload_tab(self):
        """创建上传标签页"""
        douyin_logger.info('📱 创建抖音上传标签页...')
        
        self.tab_id = await self.adapter.create_account_tab(
            platform="douyin",
            account_name=self.account_name,
            initial_url="about:blank"  # 先创建空白页
        )
        
        douyin_logger.info(f'✅ 标签页创建成功: {self.tab_id}')
    
    async def load_account_cookies(self):
        """加载账号cookies"""
        douyin_logger.info('🍪 加载账号cookies...')
        
        if not await self.adapter.load_cookies(self.tab_id, self.account_file):
            raise Exception("加载cookies失败")
        
        douyin_logger.info('✅ Cookies加载成功')
    
    async def navigate_to_upload_page(self):
        """导航到上传页面"""
        douyin_logger.info('🔗 导航到抖音上传页面...')
        
        upload_url = "https://creator.douyin.com/creator-micro/content/publish"
        
        if not await self.adapter.navigate_to_url(self.tab_id, upload_url):
            raise Exception("导航到上传页面失败")
        
        # 等待页面完全加载
        await asyncio.sleep(5)
        
        # 检查是否成功到达上传页面
        current_url = await self.adapter.get_page_url(self.tab_id)
        if "publish" not in current_url and "upload" not in current_url:
            douyin_logger.warning(f"⚠️ 当前页面可能不是上传页面: {current_url}")
        
        douyin_logger.info('✅ 已到达上传页面')
    
    async def handle_file_upload(self):
        """处理文件上传"""
        douyin_logger.info('📁 开始上传视频文件...')
        
        if not os.path.exists(self.file_path):
            raise Exception(f"视频文件不存在: {self.file_path}")
        
        # 方法1: 尝试直接设置文件（如果multi-account-browser支持）
        file_input_selector = 'input[type="file"][accept*="video"]'
        
        # 首先尝试触发文件选择器
        trigger_success = await self.adapter.click_element(self.tab_id, file_input_selector)
        
        if trigger_success:
            douyin_logger.info('🔔 已触发文件选择器')
            douyin_logger.info(f'👆 请手动选择文件: {self.file_path}')
            douyin_logger.info('⏳ 等待用户手动选择文件...')
            
            # 等待用户手动上传文件
            await self.wait_for_file_upload_completion()
        else:
            # 方法2: 尝试其他文件上传方式
            douyin_logger.warning('⚠️ 无法触发文件选择器，尝试其他方法...')
            
            # 寻找上传区域并点击
            upload_area_selectors = [
                '.upload-area',
                '.video-upload',
                '[class*="upload"]',
                '.drag-upload-area'
            ]
            
            for selector in upload_area_selectors:
                if await self.adapter.click_element(self.tab_id, selector):
                    douyin_logger.info(f'✅ 点击上传区域成功: {selector}')
                    douyin_logger.info(f'👆 请手动选择文件: {self.file_path}')
                    await self.wait_for_file_upload_completion()
                    break
            else:
                raise Exception("无法找到文件上传控件")
    
    async def wait_for_file_upload_completion(self):
        """等待文件上传完成"""
        douyin_logger.info('⏳ 等待文件上传完成...')
        
        max_wait_time = 300  # 最大等待5分钟
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            # 检查上传状态
            upload_status_script = """
            (function() {
                // 检查是否有重新上传按钮（说明上传完成）
                const reuploadBtn = document.querySelector('[text*="重新上传"], .reupload, [class*="reupload"]');
                
                // 检查是否有上传失败提示
                const uploadError = document.querySelector('[text*="上传失败"], .upload-error, [class*="error"]');
                
                // 检查是否有进度条
                const progressBar = document.querySelector('.progress, [class*="progress"]');
                
                // 检查是否有视频预览
                const videoPreview = document.querySelector('video, .video-preview');
                
                return {
                    hasReuploadBtn: !!reuploadBtn,
                    hasUploadError: !!uploadError,
                    hasProgressBar: !!progressBar,
                    hasVideoPreview: !!videoPreview,
                    currentUrl: window.location.href
                };
            })()
            """
            
            try:
                result = await self.adapter.execute_script(self.tab_id, upload_status_script)
                
                if result and isinstance(result, dict):
                    if result.get("hasReuploadBtn") or result.get("hasVideoPreview"):
                        douyin_logger.success('✅ 视频上传完成!')
                        return
                    
                    if result.get("hasUploadError"):
                        raise Exception("视频上传失败，请检查文件格式和大小")
                    
                    if result.get("hasProgressBar"):
                        douyin_logger.info('📊 视频正在上传中...')
                
            except Exception as e:
                douyin_logger.warning(f'⚠️ 检查上传状态时出错: {e}')
            
            await asyncio.sleep(10)  # 每10秒检查一次
        
        raise Exception("视频上传超时")
    
    async def fill_video_info(self):
        """填写视频信息"""
        douyin_logger.info('✏️ 填写视频标题和标签...')
        
        # 填写标题
        title_selectors = [
            'input[placeholder*="标题"]',
            'input[placeholder*="填写作品标题"]',
            '.title-input',
            'textarea[placeholder*="标题"]'
        ]
        
        title_filled = False
        for selector in title_selectors:
            if await self.adapter.type_text(self.tab_id, selector, self.title[:30]):
                douyin_logger.info(f'✅ 标题填写成功: {self.title[:30]}')
                title_filled = True
                break
        
        if not title_filled:
            douyin_logger.warning('⚠️ 无法找到标题输入框，尝试通用方法...')
            # 尝试通用方法
            generic_title_script = f"""
            (function() {{
                const inputs = document.querySelectorAll('input, textarea');
                for (let input of inputs) {{
                    if (input.placeholder && input.placeholder.includes('标题')) {{
                        input.focus();
                        input.value = '{self.title[:30]}';
                        input.dispatchEvent(new Event('input', {{bubbles: true}}));
                        input.dispatchEvent(new Event('change', {{bubbles: true}}));
                        return true;
                    }}
                }}
                return false;
            }})()
            """
            
            if await self.adapter.execute_script(self.tab_id, generic_title_script):
                douyin_logger.info('✅ 通用方法填写标题成功')
            else:
                douyin_logger.error('❌ 标题填写失败')
        
        # 添加标签
        if self.tags:
            await self.add_tags()
        
        await asyncio.sleep(2)  # 等待页面响应
    
    async def add_tags(self):
        """添加标签"""
        douyin_logger.info(f'🏷️ 添加 {len(self.tags)} 个标签...')
        
        # 寻找标签输入区域
        tag_area_selectors = [
            '.zone-container',
            '.tag-input',
            '.hashtag-input',
            '[class*="tag"]',
            '[class*="zone"]'
        ]
        
        for selector in tag_area_selectors:
            # 为每个标签添加#前缀并输入
            for tag in self.tags:
                tag_script = f"""
                (function() {{
                    const tagArea = document.querySelector('{selector}');
                    if (tagArea) {{
                        tagArea.focus();
                        const event = new KeyboardEvent('keydown', {{
                            key: '#',
                            bubbles: true
                        }});
                        tagArea.dispatchEvent(event);
                        
                        setTimeout(() => {{
                            tagArea.innerText += '#{tag} ';
                            tagArea.dispatchEvent(new Event('input', {{bubbles: true}}));
                        }}, 100);
                        
                        return true;
                    }}
                    return false;
                }})()
                """
                
                if await self.adapter.execute_script(self.tab_id, tag_script):
                    douyin_logger.info(f'✅ 添加标签: #{tag}')
                    await asyncio.sleep(1)  # 等待标签输入生效
                    break
        
        douyin_logger.info('✅ 标签添加完成')
    
    async def wait_for_video_processing(self):
        """等待视频处理完成"""
        douyin_logger.info('⏳ 等待视频处理完成...')
        
        max_wait_time = 300  # 最大等待5分钟
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            # 检查发布按钮是否可用
            publish_button_script = """
            (function() {
                const publishBtn = document.querySelector('button[text*="发布"], .publish-btn, [class*="publish"]');
                if (publishBtn) {
                    return {
                        found: true,
                        disabled: publishBtn.disabled || publishBtn.classList.contains('disabled'),
                        text: publishBtn.textContent || publishBtn.innerText
                    };
                }
                return {found: false};
            })()
            """
            
            try:
                result = await self.adapter.execute_script(self.tab_id, publish_button_script)
                
                if result and isinstance(result, dict):
                    if result.get("found") and not result.get("disabled"):
                        douyin_logger.success('✅ 视频处理完成，可以发布!')
                        return
                    
                    if result.get("found"):
                        douyin_logger.info('📊 视频正在处理中...')
                
            except Exception as e:
                douyin_logger.warning(f'⚠️ 检查视频处理状态时出错: {e}')
            
            await asyncio.sleep(10)  # 每10秒检查一次
        
        douyin_logger.warning('⚠️ 视频处理等待超时，尝试继续发布...')
    
    async def set_schedule_time(self):
        """设置定时发布"""
        douyin_logger.info('⏰ 设置定时发布...')
        
        try:
            # 点击定时发布选项
            schedule_click_script = """
            (function() {
                const scheduleLabel = document.querySelector("label:has-text('定时发布'), [text*='定时发布']");
                if (scheduleLabel) {
                    scheduleLabel.click();
                    return true;
                }
                return false;
            })()
            """
            
            if await self.adapter.execute_script(self.tab_id, schedule_click_script):
                await asyncio.sleep(2)
                
                # 设置发布时间
                publish_date_str = self.publish_date.strftime("%Y-%m-%d %H:%M")
                
                time_input_script = f"""
                (function() {{
                    const timeInput = document.querySelector('.semi-input[placeholder*="日期"], input[placeholder*="时间"]');
                    if (timeInput) {{
                        timeInput.focus();
                        timeInput.value = '{publish_date_str}';
                        timeInput.dispatchEvent(new Event('input', {{bubbles: true}}));
                        timeInput.dispatchEvent(new Event('change', {{bubbles: true}}));
                        
                        // 模拟按回车确认
                        const enterEvent = new KeyboardEvent('keydown', {{
                            key: 'Enter',
                            bubbles: true
                        }});
                        timeInput.dispatchEvent(enterEvent);
                        
                        return true;
                    }}
                    return false;
                }})()
                """
                
                if await self.adapter.execute_script(self.tab_id, time_input_script):
                    douyin_logger.info(f'✅ 定时发布时间设置成功: {publish_date_str}')
                else:
                    douyin_logger.warning('⚠️ 定时发布时间设置失败')
            else:
                douyin_logger.warning('⚠️ 无法找到定时发布选项')
                
        except Exception as e:
            douyin_logger.warning(f'⚠️ 设置定时发布时出错: {e}')
    
    async def publish_video(self):
        """发布视频"""
        douyin_logger.info('🚀 发布视频...')
        
        # 点击发布按钮
        publish_script = """
        (function() {
            const publishBtn = document.querySelector('button[text*="发布"], .publish-btn, [class*="publish"]');
            if (publishBtn && !publishBtn.disabled) {
                publishBtn.click();
                return true;
            }
            return false;
        })()
        """
        
        if not await self.adapter.execute_script(self.tab_id, publish_script):
            raise Exception("无法点击发布按钮")
        
        douyin_logger.info('✅ 发布按钮已点击')
        
        # 等待发布完成
        await self.wait_for_publish_completion()
    
    async def wait_for_publish_completion(self):
        """等待发布完成"""
        douyin_logger.info('⏳ 等待发布完成...')
        
        max_wait_time = 60  # 最大等待1分钟
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            # 检查是否跳转到管理页面
            current_url = await self.adapter.get_page_url(self.tab_id)
            
            if "manage" in current_url or "content" in current_url:
                douyin_logger.success('✅ 发布成功! 已跳转到管理页面')
                return
            
            # 检查是否有发布成功的提示
            success_check_script = """
            (function() {
                const successMsg = document.querySelector('[text*="发布成功"], [text*="发表成功"], .success');
                return !!successMsg;
            })()
            """
            
            try:
                if await self.adapter.execute_script(self.tab_id, success_check_script):
                    douyin_logger.success('✅ 检测到发布成功提示!')
                    return
            except:
                pass
            
            await asyncio.sleep(3)  # 每3秒检查一次
        
        douyin_logger.warning('⚠️ 发布完成检测超时，可能已成功发布')
    
    async def save_updated_cookies(self):
        """保存更新后的cookies"""
        douyin_logger.info('💾 保存更新后的cookies...')
        
        if await self.adapter.save_cookies(self.tab_id, self.account_file):
            douyin_logger.success('✅ Cookies保存成功')
        else:
            douyin_logger.warning('⚠️ Cookies保存失败')
    
    async def main(self):
        """主入口函数"""
        await self.upload()

# 工厂函数，根据配置选择使用哪种上传器
def create_douyin_uploader(title, file_path, tags, publish_date, account_file, thumbnail_path=None, use_multi_browser=True):
    """创建抖音上传器"""
    if use_multi_browser:
        return DouYinVideoMultiBrowser(title, file_path, tags, publish_date, account_file, thumbnail_path)
    else:
        # 导入原有的上传器
        from uploader.douyin_uploader.main import DouYinVideo
        return DouYinVideo(title, file_path, tags, publish_date, account_file, thumbnail_path)
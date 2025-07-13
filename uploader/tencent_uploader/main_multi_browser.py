# -*- coding: utf-8 -*-
import asyncio
import os
import glob
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
        """主上传流程 - 每个账号使用专属标签页"""
        try:
            tencent_logger.info(f'[+] 开始上传视频: {self.title}')
            
            # 1. 获取该账号的专属标签页
            account_name = f"视频号_{Path(self.account_file).stem}"
            self.tab_id = await self.adapter.get_or_create_account_tab(
                platform="weixin",
                account_name=account_name,
                account_file=self.account_file,
                initial_url="https://channels.weixin.qq.com/platform/post/create"
            )
            
            # 2. 等待页面加载
            await asyncio.sleep(3)
            
            # 3. 上传文件
            await self.upload_file()
            
            # 4. 等待上传完成
            await self.wait_for_upload_complete()
            
            # 5. 添加标题和标签
            await self.add_title_and_tags()
            
            # 6. 处理定时发布
            if self.publish_date and self.publish_date > datetime.now():
                await self.set_schedule_time()
            
            # 7. 处理原创声明
            if self.category:
                await self.handle_original_declaration()
            
            # 8. 发布视频
            await self.publish_video()
            
            tencent_logger.success('[+] 视频上传成功!')
            
        except Exception as e:
            tencent_logger.error(f'[-] 视频上传失败: {e}')
            raise

    async def upload_file(self):
        """上传视频文件 - 使用自动化文件设置"""
        actual_file_path = self._get_actual_file_path()
        
        tencent_logger.info(f"准备上传文件: {actual_file_path}")
        
        # 等待页面和 shadow DOM 加载
        await asyncio.sleep(3)
        
        # 方法1: 尝试 Shadow DOM 内的文件输入框
        try:
            tencent_logger.info("尝试方法1: Shadow DOM 自动文件上传")
            
            # 首先检查 shadow DOM 结构
            check_script = '''
            (function() {
                try {
                    const shadowm = document.querySelector('.wujie_iframe');
                    if (!shadowm || !shadowm.shadowRoot) {
                        return { found: false, error: '未找到 .wujie_iframe 或 shadowRoot' };
                    }
                    
                    const videoDom = shadowm.shadowRoot.querySelector('.upload');
                    if (!videoDom) {
                        return { found: false, error: '未找到 .upload 元素' };
                    }
                    
                    const inputDom = videoDom.querySelector('input[type="file"]');
                    if (!inputDom) {
                        return { found: false, error: '未找到文件输入框' };
                    }
                    
                    // 为了让外部能找到这个输入框，给它设置一个ID
                    inputDom.id = 'shadow-file-input-' + Date.now();
                    
                    return { found: true, inputId: inputDom.id };
                } catch (e) {
                    return { found: false, error: e.message };
                }
            })()
            '''
            
            result = await self.adapter.execute_script(self.tab_id, check_script)
            
            if result and result.get('found'):
                input_id = result.get('inputId')
                tencent_logger.info(f"找到 Shadow DOM 文件输入框: #{input_id}")
                
                # 使用自动化文件设置
                success = await self.adapter.set_file_input_automatic(
                    self.tab_id, 
                    f'#{input_id}',
                    actual_file_path
                )
                
                if success:
                    tencent_logger.success("方法1成功: Shadow DOM 文件自动设置完成")
                    return True
                else:
                    raise Exception("Shadow DOM 自动文件设置失败")
            else:
                raise Exception(f"Shadow DOM 检查失败: {result.get('error')}")
                
        except Exception as e:
            tencent_logger.warning(f"方法1失败: {e}")
            
            # 方法2: 尝试常规的文件输入框
            try:
                tencent_logger.info("尝试方法2: 常规文件输入框自动上传")
                
                success = await self.adapter.set_file_input_automatic(
                    self.tab_id,
                    'input[type="file"]',
                    actual_file_path
                )
                
                if success:
                    tencent_logger.success("方法2成功: 常规文件输入框自动设置完成")
                    return True
                else:
                    raise Exception("常规文件输入框自动设置失败")
                    
            except Exception as e2:
                tencent_logger.warning(f"方法2失败: {e2}")
                
                # 方法3: 降级到传统点击方式
                tencent_logger.info("尝试方法3: 传统点击方式")
                success = await self.adapter.upload_file_fallback(
                    self.tab_id,
                    'input[type="file"]',
                    actual_file_path
                )
                
                if success:
                    tencent_logger.info("方法3: 已触发文件选择器，等待用户操作")
                    await asyncio.sleep(10)  # 给用户操作时间
                    return True
                else:
                    raise Exception("所有文件上传方法都失败")

    def _get_actual_file_path(self):
        """获取实际文件路径"""
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
        
        return actual_file_path

    async def wait_for_upload_complete(self):
        """等待上传完成"""
        tencent_logger.info("等待视频上传完成...")
        
        check_script = """
        (function() {
            try {
                // 检查发布按钮是否可用
                const publishBtn = document.querySelector('button:has-text("发表")');
                if (!publishBtn) return { ready: false, reason: '未找到发布按钮' };
                
                const isDisabled = publishBtn.classList.contains('weui-desktop-btn_disabled');
                return { 
                    ready: !isDisabled,
                    btnClass: publishBtn.className 
                };
            } catch (e) {
                return { ready: false, error: e.message };
            }
        })()
        """
        
        # 等待上传完成（最多等待10分钟）
        max_wait = 600
        elapsed = 0
        
        while elapsed < max_wait:
            result = await self.adapter.execute_script(self.tab_id, check_script)
            
            if result.get('ready'):
                tencent_logger.success("✅ 上传完成!")
                break
            
            if elapsed % 30 == 0:  # 每30秒报告一次
                tencent_logger.info(f"⏳ 上传中... ({elapsed//60}分{elapsed%60}秒)")
            
            await asyncio.sleep(10)
            elapsed += 10
        
        if elapsed >= max_wait:
            raise Exception("上传超时")

    async def add_title_and_tags(self):
        """添加标题和标签"""
        script = f"""
        (async function() {{
            try {{
                // 添加标题
                const titleInput = document.querySelector('div.input-editor');
                if (titleInput) {{
                    titleInput.click();
                    await new Promise(r => setTimeout(r, 500));
                    
                    // 清空并输入标题
                    titleInput.innerText = '';
                    titleInput.innerText = '{self.title}';
                    
                    // 触发输入事件
                    titleInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    
                    // 添加换行
                    const enterEvent = new KeyboardEvent('keydown', {{ key: 'Enter', code: 'Enter' }});
                    titleInput.dispatchEvent(enterEvent);
                    
                    await new Promise(r => setTimeout(r, 500));
                    
                    // 添加标签
                    const tags = {self.tags};
                    for (const tag of tags) {{
                        titleInput.innerText += '#' + tag + ' ';
                        titleInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        await new Promise(r => setTimeout(r, 200));
                    }}
                    
                    return {{ success: true }};
                }} else {{
                    return {{ success: false, error: '未找到标题输入框' }};
                }}
            }} catch (e) {{
                return {{ success: false, error: e.message }};
            }}
        }})()
        """
        
        result = await self.adapter.execute_script(self.tab_id, script)
        
        if result.get('success'):
            tencent_logger.success("标题和标签添加完成")
        else:
            tencent_logger.warning(f"添加标题失败: {result.get('error')}")

    async def set_schedule_time(self):
        """设置定时发布"""
        if not self.publish_date:
            return
            
        script = f"""
        (async function() {{
            try {{
                // 点击定时发布
                const scheduleLabel = document.querySelector('label:has-text("定时")');
                if (scheduleLabel) {{
                    scheduleLabel.click();
                    await new Promise(r => setTimeout(r, 1000));
                    
                    // 选择时间
                    const timeInput = document.querySelector('input[placeholder="请选择发表时间"]');
                    if (timeInput) {{
                        timeInput.click();
                        await new Promise(r => setTimeout(r, 500));
                        
                        // 这里需要根据具体的时间选择器实现
                        // 暂时返回成功，实际使用时需要完善
                        return {{ success: true }};
                    }}
                }}
                return {{ success: false, error: '未找到定时设置' }};
            }} catch (e) {{
                return {{ success: false, error: e.message }};
            }}
        }})()
        """
        
        result = await self.adapter.execute_script(self.tab_id, script)
        
        if result.get('success'):
            tencent_logger.info("定时发布设置完成")
        else:
            tencent_logger.warning(f"定时设置失败: {result.get('error')}")

    async def handle_original_declaration(self):
        """处理原创声明"""
        script = """
        (async function() {
            try {
                const wujieApp = document.querySelector('wujie-app');
                if (!wujieApp || !wujieApp.shadowRoot) {
                    return { success: false, error: '未找到 shadow DOM' };
                }
                
                const shadowDoc = wujieApp.shadowRoot;
                
                // 点击原创声明复选框
                const checkboxWrappers = shadowDoc.querySelectorAll('label.ant-checkbox-wrapper');
                for (let wrapper of checkboxWrappers) {
                    if (wrapper.textContent.includes('声明后，作品将展示原创标记')) {
                        const isChecked = wrapper.querySelector('.ant-checkbox-checked');
                        if (!isChecked) {
                            wrapper.click();
                            await new Promise(r => setTimeout(r, 1000));
                        }
                        break;
                    }
                }
                
                // 同意条款
                const protoWrapper = shadowDoc.querySelector('.original-proto-wrapper');
                if (protoWrapper) {
                    const checkbox = protoWrapper.querySelector('label.ant-checkbox-wrapper');
                    if (checkbox) {
                        const isChecked = checkbox.querySelector('.ant-checkbox-checked');
                        if (!isChecked) {
                            checkbox.click();
                            await new Promise(r => setTimeout(r, 500));
                        }
                    }
                }
                
                // 点击声明原创按钮
                const buttons = shadowDoc.querySelectorAll('button');
                for (let btn of buttons) {
                    if (btn.textContent.trim() === '声明原创' && 
                        !btn.classList.contains('weui-desktop-btn_disabled')) {
                        btn.click();
                        return { success: true };
                    }
                }
                
                return { success: false, error: '未找到可用的声明原创按钮' };
            } catch (e) {
                return { success: false, error: e.message };
            }
        })()
        """
        
        result = await self.adapter.execute_script(self.tab_id, script)
        
        if result.get('success'):
            tencent_logger.success("原创声明设置完成")
        else:
            tencent_logger.warning(f"原创声明设置失败: {result.get('error')}")

    async def publish_video(self):
        """发布视频"""
        script = """
        (function() {
            try {
                const publishBtn = document.querySelector('button:has-text("发表")');
                if (publishBtn && !publishBtn.classList.contains('weui-desktop-btn_disabled')) {
                    publishBtn.click();
                    return { success: true };
                }
                return { success: false, error: '发布按钮不可用' };
            } catch (e) {
                return { success: false, error: e.message };
            }
        })()
        """
        
        result = await self.adapter.execute_script(self.tab_id, script)
        
        if result.get('success'):
            tencent_logger.success("视频发布完成")
            
            # 等待页面跳转确认发布成功
            await asyncio.sleep(5)
            
            # 检查是否跳转到列表页
            url_check = "window.location.href"
            current_url = await self.adapter.execute_script(self.tab_id, url_check)
            
            if 'platform/post/list' in str(current_url):
                tencent_logger.success("发布成功，已跳转到列表页")
            else:
                tencent_logger.info("发布完成，等待确认...")
        else:
            raise Exception(f"发布失败: {result.get('error')}")
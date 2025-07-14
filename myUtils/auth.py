import asyncio
import configparser
import os

from utils.smart_playwright import async_playwright, Playwright
from xhs import XhsClient

from conf import BASE_DIR
from utils.base_social_media import set_init_script
from utils.log import tencent_logger, kuaishou_logger
from pathlib import Path
from uploader.xhs_uploader.main import sign_local
from typing import Optional, Dict, Any, List
async def check_cookie(platform_type: int, cookie_file_path: str) -> bool:
    """
    检查Cookie有效性 - 自动选择浏览器模式
    
    Args:
        platform_type: 平台类型 (1:小红书, 2:视频号, 3:抖音, 4:快手)
        cookie_file_path: Cookie文件路径
    
    Returns:
        bool: Cookie是否有效
    """
    
    platform_map = {1: '小红书', 2: '视频号', 3: '抖音', 4: '快手'}
    platform_name = platform_map.get(platform_type, f'平台{platform_type}')
    
    cookie_file = Path(BASE_DIR / "cookiesFile" / cookie_file_path)
    
    if not cookie_file.exists():
        print(f"⚠️ {platform_name} Cookie文件不存在: {cookie_file}")
        return False
    
    print(f"🔍 检查 {platform_name} Cookie有效性: {cookie_file.name}")
    from utils.smart_playwright import async_playwright
    print(f"🔍 调试: async_playwright 类型: {type(async_playwright)}")
    print(f"🔍 调试: 模块路径: {async_playwright.__module__}")
    try:
        playwright_instance = await async_playwright()
        async with playwright_instance as playwright:
            browser = await playwright.chromium.launch(headless=True)
            
            # 使用Cookie文件创建上下文 - 会自动映射到对应账号标签页
            context = await browser.new_context(storage_state=str(cookie_file))
            page = await context.new_page()
            
            # 根据平台类型选择验证URL和方法
            is_valid = False
            
            if platform_type == 1:  # 小红书
                is_valid = await _check_xiaohongshu_cookie(page)
            elif platform_type == 2:  # 视频号
                is_valid = await _check_tencent_cookie(page)
            elif platform_type == 3:  # 抖音
                is_valid = await _check_douyin_cookie(page)
            elif platform_type == 4:  # 快手
                is_valid = await _check_kuaishou_cookie(page)
            else:
                print(f"❌ 不支持的平台类型: {platform_type}")
                is_valid = False
            
            await context.close()
            await browser.close()
            
            status_text = "✅ 有效" if is_valid else "❌ 无效"
            print(f"🔍 {platform_name} Cookie验证结果: {status_text}")
            
            return is_valid
            
    except Exception as e:
        print(f"❌ {platform_name} Cookie验证失败: {e}")
        return False

async def _check_tencent_cookie(page) -> bool:
    """检查视频号Cookie有效性"""
    try:
        await page.goto("https://channels.weixin.qq.com/platform", timeout=30000)
        
        # 等待页面加载
        await asyncio.sleep(3)
        
        # 检查是否跳转到登录页
        current_url = page.url
        if "login" in current_url.lower():
            return False
        
        # 检查是否有登录后的元素
        try:
            # 等待用户相关元素出现
            await page.wait_for_selector('.avatar, .user-avatar, .nickname, .username', timeout=10000)
            return True
        except:
            # 检查是否在创作者页面
            if "platform" in current_url:
                return True
            return False
            
    except Exception as e:
        print(f"视频号Cookie检查异常: {e}")
        return False

async def _check_douyin_cookie(page) -> bool:
    """检查抖音Cookie有效性"""
    try:
        await page.goto("https://creator.douyin.com", timeout=30000)
        
        await asyncio.sleep(3)
        
        current_url = page.url
        if "login" in current_url.lower():
            return False
        
        try:
            # 检查创作者页面的元素
            await page.wait_for_selector('.semi-avatar, .creator-header, .user-info', timeout=10000)
            return True
        except:
            if "creator.douyin.com" in current_url and "login" not in current_url:
                return True
            return False
            
    except Exception as e:
        print(f"抖音Cookie检查异常: {e}")
        return False

async def _check_xiaohongshu_cookie(page) -> bool:
    """检查小红书Cookie有效性"""
    try:
        await page.goto("https://creator.xiaohongshu.com", timeout=30000)
        
        await asyncio.sleep(3)
        
        current_url = page.url
        if "login" in current_url.lower():
            return False
        
        try:
            await page.wait_for_selector('.header-avatar, .user-avatar, .creator-info', timeout=10000)
            return True
        except:
            if "creator.xiaohongshu.com" in current_url and "login" not in current_url:
                return True
            return False
            
    except Exception as e:
        print(f"小红书Cookie检查异常: {e}")
        return False

async def _check_kuaishou_cookie(page) -> bool:
    """检查快手Cookie有效性"""
    try:
        await page.goto("https://cp.kuaishou.com", timeout=30000)
        
        await asyncio.sleep(3)
        
        current_url = page.url
        if "login" in current_url.lower():
            return False
        
        try:
            await page.wait_for_selector('.header-userinfo, .user-avatar, .creator-header', timeout=10000)
            return True
        except:
            if "cp.kuaishou.com" in current_url and "login" not in current_url:
                return True
            return False
            
    except Exception as e:
        print(f"快手Cookie检查异常: {e}")
        return False

# ========================================
# 批量验证函数（可选的高级功能）
# ========================================

async def batch_check_cookies(cookie_files: list) -> dict:
    """
    批量检查Cookie有效性
    
    Args:
        cookie_files: Cookie文件列表 [{"platform": 2, "file": "account1_tencent.json"}, ...]
    
    Returns:
        dict: 验证结果 {"valid": [...], "invalid": [...]}
    """
    results = {"valid": [], "invalid": []}
    
    print(f"🔍 开始批量验证 {len(cookie_files)} 个Cookie文件...")
    
    for i, cookie_info in enumerate(cookie_files, 1):
        platform_type = cookie_info.get("platform")
        file_path = cookie_info.get("file")
        
        print(f"📋 验证进度: {i}/{len(cookie_files)} - {file_path}")
        
        try:
            is_valid = await check_cookie(platform_type, file_path)
            
            result_item = {
                "platform": platform_type,
                "file": file_path,
                "valid": is_valid
            }
            
            if is_valid:
                results["valid"].append(result_item)
            else:
                results["invalid"].append(result_item)
                
        except Exception as e:
            print(f"❌ 验证 {file_path} 时出错: {e}")
            results["invalid"].append({
                "platform": platform_type,
                "file": file_path,
                "valid": False,
                "error": str(e)
            })
    
    print(f"📊 批量验证完成:")
    print(f"   有效: {len(results['valid'])} 个")
    print(f"   无效: {len(results['invalid'])} 个")
    
    return results
# a = asyncio.run(check_cookie(1,"3a6cfdc0-3d51-11f0-8507-44e51723d63c.json"))
# print(a)
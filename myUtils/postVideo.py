import asyncio
from pathlib import Path

from conf import BASE_DIR

from uploader.douyin_uploader.main import DouYinVideo
from uploader.ks_uploader.main import KSVideo
from uploader.tencent_uploader.main import TencentVideo
from uploader.xiaohongshu_uploader.main import XiaoHongShuVideo

from utils.constant import TencentZoneTypes
from utils.files_times import generate_schedule_time_next_day

def get_current_browser_mode():
    """获取当前浏览器模式"""
    try:
        from utils.smart_playwright import async_playwright, Playwright
        # 通过模块路径判断当前使用的实现
        module_path = str(async_playwright.__module__)
        if 'playwright_compat' in module_path:
            return "multi-account-browser"
        else:
            return "playwright"
    except:
        return "unknown"

# 原来的函数完全不变，但现在会自动使用正确的 playwright 实现
def post_video_tencent(title, files, tags, account_file, category=TencentZoneTypes.LIFESTYLE.value, enableTimer=False, videos_per_day=1, daily_times=None, start_days=0):
    """视频号发布 - 自动选择浏览器实现"""
    
    print(f"🎯 视频号发布模式: {get_current_browser_mode()}")
    
    # 生成文件的完整路径
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(files), videos_per_day, daily_times, start_days)
    else:
        publish_datetimes = [0 for i in range(len(files))]
    
    for index, file in enumerate(files):
        for cookie in account_file:
            print(f"文件路径{str(file)}")
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            
            app = TencentVideo(title, str(file), tags, publish_datetimes[index], cookie, category)
            asyncio.run(app.main(), debug=False)

def post_video_DouYin(title, files, tags, account_file, category=None, enableTimer=False, videos_per_day=1, daily_times=None, start_days=0):
    """抖音发布 - 自动选择浏览器实现"""
    
    print(f"🎯 抖音发布模式: {get_current_browser_mode()}")
    
    # 原来的代码完全不变
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(files), videos_per_day, daily_times, start_days)
    else:
        publish_datetimes = [0 for i in range(len(files))]
    
    for index, file in enumerate(files):
        for cookie in account_file:
            print(f"文件路径{str(file)}")
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            
            app = DouYinVideo(title, str(file), tags, publish_datetimes[index], cookie, category)
            asyncio.run(app.main(), debug=False)

def post_video_ks(title, files, tags, account_file, category=None, enableTimer=False, videos_per_day=1, daily_times=None, start_days=0):
    """快手发布 - 自动选择浏览器实现"""
    print(f"🎯 快手发布模式: {get_current_browser_mode()}")
    
    # 原来的代码完全不变...
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(files), videos_per_day, daily_times, start_days)
    else:
        publish_datetimes = [0 for i in range(len(files))]
    
    for index, file in enumerate(files):
        for cookie in account_file:
            print(f"文件路径{str(file)}")
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            
            app = KSVideo(title, str(file), tags, publish_datetimes[index], cookie)
            asyncio.run(app.main(), debug=False)

def post_video_xhs(title, files, tags, account_file, category=None, enableTimer=False, videos_per_day=1, daily_times=None, start_days=0):
    """小红书发布 - 自动选择浏览器实现"""
    print(f"🎯 小红书发布模式: {get_current_browser_mode()}")
    
    # 原来的代码完全不变...
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    
    file_num = len(files)
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(file_num, videos_per_day, daily_times, start_days)
    else:
        publish_datetimes = 0
    
    for index, file in enumerate(files):
        for cookie in account_file:
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            
            app = XiaoHongShuVideo(title, file, tags, publish_datetimes, cookie)
            asyncio.run(app.main(), debug=False)

def show_browser_status():
    """显示当前浏览器状态"""
    mode = get_current_browser_mode()
    print(f"📊 当前浏览器模式: {mode}")
    
    if mode == "multi-account-browser":
        try:
            from utils.playwright_compat import get_account_tab_manager
            manager = get_account_tab_manager()
            manager.debug_print_tabs()
        except:
            print("   无法获取标签页信息")

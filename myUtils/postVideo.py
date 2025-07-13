import asyncio
from pathlib import Path

from conf import BASE_DIR
from uploader.douyin_uploader.main_multi_browser import DouYinVideoMultiBrowser
from uploader.douyin_uploader.main import DouYinVideo
from uploader.ks_uploader.main import KSVideo
from uploader.tencent_uploader.main import TencentVideo
from uploader.xiaohongshu_uploader.main import XiaoHongShuVideo
from utils.constant import TencentZoneTypes
from utils.files_times import generate_schedule_time_next_day

# 全局配置，控制是否使用 multi-account-browser
USE_MULTI_ACCOUNT_BROWSER = True
try:
    from uploader.tencent_uploader.main_multi_browser import TencentVideoMultiBrowser
    TENCENT_MULTI_BROWSER_AVAILABLE = True
except ImportError:
    TENCENT_MULTI_BROWSER_AVAILABLE = False
    print("⚠️ 视频号 multi-account-browser 模块未找到")

def set_browser_mode(use_multi_browser: bool):
    """设置浏览器模式"""
    global USE_MULTI_ACCOUNT_BROWSER
    USE_MULTI_ACCOUNT_BROWSER = use_multi_browser
    print(f"🔄 浏览器模式已切换到: {'multi-account-browser' if use_multi_browser else 'playwright'}")

def get_browser_mode() -> bool:
    """获取当前浏览器模式"""
    return USE_MULTI_ACCOUNT_BROWSER

async def post_video_douyin_multi_browser(title, files, tags, account_file, category=None, enableTimer=False, videos_per_day=1, daily_times=None, start_days=0):
    """使用 multi-account-browser 发布抖音视频"""
    print(f"🚀 使用 multi-account-browser 发布抖音视频")
    
    # 生成文件的完整路径
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(files), videos_per_day, daily_times, start_days)
    else:
        publish_datetimes = [0 for i in range(len(files))]
    
    for index, file in enumerate(files):
        for cookie in account_file:
            print(f"📁 文件路径: {str(file)}")
            print(f"🎬 视频文件名: {file}")
            print(f"📝 标题: {title}")
            print(f"🏷️ 标签: {tags}")
            
            # 使用新的 multi-account-browser 上传器
            app = DouYinVideoMultiBrowser(
                title=title, 
                file_path=str(file), 
                tags=tags, 
                publish_date=publish_datetimes[index], 
                account_file=str(cookie)
            )
            
            try:
                asyncio.run(app.main())
                print(f"✅ 抖音视频发布成功: {title}")
            except Exception as e:
                print(f"❌ 抖音视频发布失败: {e}")

async def post_video_DouYin_smart(title, files, tags, account_file, category=None, enableTimer=False, videos_per_day=1, daily_times=None, start_days=0):
    """智能选择抖音发布方式"""
    if USE_MULTI_ACCOUNT_BROWSER:
        print("🌟 使用 multi-account-browser 发布抖音视频")
        await post_video_douyin_multi_browser(title, files, tags, account_file, category, enableTimer, videos_per_day, daily_times, start_days)
    else:
        print("🔧 使用传统 playwright 发布抖音视频")
        post_video_DouYin(title, files, tags, account_file, category, enableTimer, videos_per_day, daily_times, start_days)

async def post_video_tencent_smart(title, files, tags, account_file, category=TencentZoneTypes.LIFESTYLE.value, enableTimer=False, videos_per_day=1, daily_times=None, start_days=0):
    """智能选择视频号发布方式"""
    if USE_MULTI_ACCOUNT_BROWSER:
        print("🌟 使用 multi-account-browser 发布视频号")
        await post_video_tencent_multi_browser(title, files, tags, account_file, category, enableTimer, videos_per_day, daily_times, start_days)
    else:
        print("🔧 使用传统 playwright 发布视频号")
        post_video_tencent(title, files, tags, account_file, category, enableTimer, videos_per_day, daily_times, start_days)

async def post_video_tencent_multi_browser(title, files, tags, account_file, category=TencentZoneTypes.LIFESTYLE.value, enableTimer=False, videos_per_day=1, daily_times=None, start_days=0):
    """使用 multi-account-browser 发布视频号视频 - 每账号一标签页"""
    print(f"🚀 使用 multi-account-browser 发布视频号视频")
    
    from uploader.tencent_uploader.main_multi_browser import TencentVideoMultiBrowser
    
    # 生成文件的完整路径
    account_files = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    video_files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(video_files), videos_per_day, daily_times, start_days)
    else:
        publish_datetimes = [0 for i in range(len(video_files))]
    
    # 为每个视频文件 x 每个账号 组合创建上传任务
    for index, video_file in enumerate(video_files):
        print(f"\n📹 处理视频: {video_file.name}")
        
        for account in account_files:
            print(f"👤 使用账号: {account.name}")
            
            # 每个账号都有自己的专属标签页
            uploader = TencentVideoMultiBrowser(
                title=title, 
                file_path=str(video_file), 
                tags=tags, 
                publish_date=publish_datetimes[index], 
                account_file=str(account),
                category=category
            )
            
            try:
                await uploader.main()  # 这里需要 await
                print(f"✅ 账号 {account.stem} 发布视频成功: {title}")
                
            except Exception as e:
                print(f"❌ 账号 {account.stem} 发布视频失败: {e}")
                
            # 短暂间隔，避免请求过于频繁
            await asyncio.sleep(2)  # 这里需要 await
        
        # 一个视频发布到所有账号后，稍作间隔
        if index < len(video_files) - 1:
            print(f"⏳ 视频 {video_file.name} 发布完成，等待处理下一个视频...")
            await asyncio.sleep(5)  # 这里需要 await

# 新增：查看所有账号标签页状态
async def show_all_account_tabs():
    """显示所有账号的标签页状态"""
    from utils.browser_adapter import MultiAccountBrowserAdapter
    
    adapter = MultiAccountBrowserAdapter()
    account_tabs = adapter.get_all_account_tabs()
    
    print(f"\n📊 当前账号标签页状态 ({len(account_tabs)} 个账号):")
    for account_file, tab_id in account_tabs.items():
        account_name = Path(account_file).stem
        is_valid = await adapter.is_tab_valid(tab_id)
        status = "🟢 活跃" if is_valid else "🔴 失效"
        print(f"  {account_name}: {tab_id} - {status}")

# 新增：关闭所有账号标签页（可选）
async def close_all_account_tabs():
    """关闭所有账号的标签页"""
    from utils.browser_adapter import MultiAccountBrowserAdapter
    
    adapter = MultiAccountBrowserAdapter()
    account_tabs = adapter.get_all_account_tabs()
    
    for account_file in list(account_tabs.keys()):
        await adapter.close_account_tab(account_file)
    
    print(f"🗑️ 已关闭所有 {len(account_tabs)} 个账号标签页")

async def post_video_ks_smart(title, files, tags, account_file, category=None, enableTimer=False, videos_per_day=1, daily_times=None, start_days=0):
    """智能选择快手发布方式"""
    if USE_MULTI_ACCOUNT_BROWSER:
        print("🌟 快手暂时使用传统方式，multi-account-browser 支持开发中...")
        await post_video_ks(title, files, tags, account_file, category, enableTimer, videos_per_day, daily_times, start_days)
    else:
        print("🔧 使用传统 playwright 发布快手")
        post_video_ks(title, files, tags, account_file, category, enableTimer, videos_per_day, daily_times, start_days)

async def post_video_xhs_smart(title, files, tags, account_file, category=None, enableTimer=False, videos_per_day=1, daily_times=None, start_days=0):
    """智能选择小红书发布方式"""
    if USE_MULTI_ACCOUNT_BROWSER:
        print("🌟 小红书暂时使用传统方式，multi-account-browser 支持开发中...")
        await post_video_xhs(title, files, tags, account_file, category, enableTimer, videos_per_day, daily_times, start_days)
    else:
        print("🔧 使用传统 playwright 发布小红书")
        post_video_xhs(title, files, tags, account_file, category, enableTimer, videos_per_day, daily_times, start_days)

# 批量发布函数 - 支持混合模式
async def batch_publish_videos_multi_browser(video_tasks):
    """批量发布视频 - 使用 multi-account-browser 可以并发处理多个账号"""
    print(f"🚀 开始批量发布 {len(video_tasks)} 个视频任务")
    
    results = []
    
    if USE_MULTI_ACCOUNT_BROWSER:
        # 使用 multi-account-browser 可以并发处理
        print("🌟 使用 multi-account-browser 并发发布")
        
        async def publish_single_task(task):
            try:
                platform = task.get('platform', 'douyin')
                
                if platform == 'douyin':
                    app = DouYinVideoMultiBrowser(
                        title=task['title'],
                        file_path=task['file_path'],
                        tags=task['tags'],
                        publish_date=task.get('publish_date', 0),
                        account_file=task['account_file']
                    )
                    await app.main()
                    return {'success': True, 'task': task['title']}
                else:
                    return {'success': False, 'task': task['title'], 'error': f'平台 {platform} 暂不支持并发'}
                    
            except Exception as e:
                return {'success': False, 'task': task.get('title', 'Unknown'), 'error': str(e)}
        
        # 并发执行（但限制并发数量以避免资源过载）
        semaphore = asyncio.Semaphore(3)  # 最多同时3个任务
        
        async def limited_publish(task):
            async with semaphore:
                return await publish_single_task(task)
        
        results = await asyncio.gather(*[limited_publish(task) for task in video_tasks], return_exceptions=True)
        
    else:
        # 使用传统方式串行处理
        print("🔧 使用传统方式串行发布")
        for task in video_tasks:
            try:
                platform = task.get('platform', 'douyin')
                
                if platform == 'douyin':
                    post_video_DouYin(
                        task['title'],
                        [task['file_path']],
                        task['tags'],
                        [task['account_file']]
                    )
                # 可以添加其他平台的处理...
                
                results.append({'success': True, 'task': task['title']})
                
            except Exception as e:
                results.append({'success': False, 'task': task.get('title', 'Unknown'), 'error': str(e)})
    
    # 统计结果
    success_count = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
    total_count = len(results)
    
    print(f"📊 批量发布完成: {success_count}/{total_count} 成功")
    
    return results

# 测试函数
async def test_multi_browser_upload():
    """测试 multi-account-browser 上传功能"""
    print("🧪 测试 multi-account-browser 上传功能")
    
    # 创建测试任务
    test_video = DouYinVideoMultiBrowser(
        title="测试视频标题",
        file_path="/path/to/test/video.mp4",  # 请替换为实际的测试视频路径
        tags=["测试", "multi-browser"],
        publish_date=0,
        account_file="/path/to/test/cookies.json"  # 请替换为实际的cookies文件路径
    )
    
    try:
        await test_video.main()
        print("✅ multi-account-browser 上传测试成功!")
        return True
    except Exception as e:
        print(f"❌ multi-account-browser 上传测试失败: {e}")
        return False

# 性能监控函数
def monitor_upload_performance():
    """监控上传性能"""
    import time
    import psutil
    
    start_time = time.time()
    start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
    
    def get_performance_stats():
        elapsed_time = time.time() - start_time
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        memory_diff = current_memory - start_memory
        
        return {
            'elapsed_time': round(elapsed_time, 2),
            'memory_usage': round(current_memory, 2),
            'memory_diff': round(memory_diff, 2),
            'browser_mode': 'multi-account-browser' if USE_MULTI_ACCOUNT_BROWSER else 'playwright'
        }
    
    return get_performance_stats

def post_video_tencent(title,files,tags,account_file,category=TencentZoneTypes.LIFESTYLE.value,enableTimer=False,videos_per_day = 1, daily_times=None,start_days = 0):
    # 生成文件的完整路径
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(files), videos_per_day, daily_times,start_days)
    else:
        publish_datetimes = [0 for i in range(len(files))]
    for index, file in enumerate(files):
        for cookie in account_file:
            print(f"文件路径{str(file)}")
            # 打印视频文件名、标题和 hashtag
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            app = TencentVideo(title, str(file), tags, publish_datetimes[index], cookie, category)
            asyncio.run(app.main(), debug=False)


def post_video_DouYin(title,files,tags,account_file,category=TencentZoneTypes.LIFESTYLE.value,enableTimer=False,videos_per_day = 1, daily_times=None,start_days = 0):
    # 生成文件的完整路径
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(files), videos_per_day, daily_times,start_days)
    else:
        publish_datetimes = [0 for i in range(len(files))]
    for index, file in enumerate(files):
        for cookie in account_file:
            print(f"文件路径{str(file)}")
            # 打印视频文件名、标题和 hashtag
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            app = DouYinVideo(title, str(file), tags, publish_datetimes[index], cookie, category)
            asyncio.run(app.main(), debug=False)


def post_video_ks(title,files,tags,account_file,category=TencentZoneTypes.LIFESTYLE.value,enableTimer=False,videos_per_day = 1, daily_times=None,start_days = 0):
    # 生成文件的完整路径
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(files), videos_per_day, daily_times,start_days)
    else:
        publish_datetimes = [0 for i in range(len(files))]
    for index, file in enumerate(files):
        for cookie in account_file:
            print(f"文件路径{str(file)}")
            # 打印视频文件名、标题和 hashtag
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            app = KSVideo(title, str(file), tags, publish_datetimes[index], cookie)
            asyncio.run(app.main(), debug=False)

def post_video_xhs(title,files,tags,account_file,category=TencentZoneTypes.LIFESTYLE.value,enableTimer=False,videos_per_day = 1, daily_times=None,start_days = 0):
    # 生成文件的完整路径
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    file_num = len(files)
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(file_num, videos_per_day, daily_times,start_days)
    else:
        publish_datetimes = 0
    for index, file in enumerate(files):
        for cookie in account_file:
            # 打印视频文件名、标题和 hashtag
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            app = XiaoHongShuVideo(title, file, tags, publish_datetimes, cookie)
            asyncio.run(app.main(), debug=False)

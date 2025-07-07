from datetime import timedelta

from datetime import datetime
from pathlib import Path

from conf import BASE_DIR

def get_video_extension(filename):
    """获取视频文件的扩展名"""
    return Path(filename).suffix.lower()

def get_txt_filename(video_filename):
    """根据视频文件名生成对应的txt文件名"""
    return str(Path(video_filename).with_suffix('.txt'))
def get_absolute_path(relative_path: str, base_dir: str = None) -> str:
    # Convert the relative path to an absolute path
    absolute_path = Path(BASE_DIR) / base_dir / relative_path
    return str(absolute_path)

def get_title_and_hashtags(filename, title_override=None, tags_override=None):
    """
    获取视频标题和 hashtag

    Args:
        filename: 视频文件名
        title_override: 可选的标题覆盖
        tags_override: 可选的标签覆盖 (格式: "#tag1 #tag2")

    Returns:
        视频标题和 hashtag 列表
    """
    import os
    
    # 如果提供了覆盖参数，直接使用
    if title_override and tags_override:
        hashtags = tags_override.replace("#", "").split()
        return title_override, hashtags
    
    # 使用新的工具函数生成txt文件名（支持所有视频格式）
    txt_filename = get_txt_filename(filename)
    
    # 初始化变量
    title = title_override if title_override else ""
    hashtags = []
    
    if tags_override:
        hashtags = tags_override.replace("#", "").split()
    
    # 如果已经有完整信息，直接返回
    if title and hashtags:
        return title, hashtags
    
    # 尝试从txt文件读取缺失的信息
    if os.path.exists(txt_filename):
        try:
            # 尝试多种编码读取文件
            content = None
            for encoding in ['utf-8', 'gbk', 'gb2312', 'utf-8-sig']:
                try:
                    with open(txt_filename, "r", encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if content:
                splite_str = content.strip().split("\n")
                if not title and len(splite_str) > 0:
                    title = splite_str[0]
                
                if not hashtags and len(splite_str) > 1:
                    hashtags = splite_str[1].replace("#", "").split(" ")
                    
        except Exception as e:
            print(f"警告：读取txt文件失败 {txt_filename}: {e}")
    
    # 如果仍然没有标题，使用文件名作为默认标题
    if not title:
        title = Path(filename).stem
    
    # 如果仍然没有标签，使用空列表
    if not hashtags:
        hashtags = []
    
    return title, hashtags


def generate_schedule_time_next_day(total_videos, videos_per_day = 1, daily_times=None, timestamps=False, start_days=0):
    """
    Generate a schedule for video uploads, starting from the next day.

    Args:
    - total_videos: Total number of videos to be uploaded.
    - videos_per_day: Number of videos to be uploaded each day.
    - daily_times: Optional list of specific times of the day to publish the videos.
    - timestamps: Boolean to decide whether to return timestamps or datetime objects.
    - start_days: Start from after start_days.

    Returns:
    - A list of scheduling times for the videos, either as timestamps or datetime objects.
    """
    if videos_per_day <= 0:
        raise ValueError("videos_per_day should be a positive integer")

    if daily_times is None:
        # Default times to publish videos if not provided
        daily_times = [6, 11, 14, 16, 22]
    daily_times = [int(time) for time in daily_times]
    if videos_per_day > len(daily_times):
        raise ValueError("videos_per_day should not exceed the length of daily_times")

    # Generate timestamps
    schedule = []
    current_time = datetime.now()

    for video in range(total_videos):
        day = video // videos_per_day + start_days + 1  # +1 to start from the next day
        daily_video_index = video % videos_per_day

        # Calculate the time for the current video
        hour = daily_times[daily_video_index]
        time_offset = timedelta(days=day, hours=hour - current_time.hour, minutes=-current_time.minute,
                                seconds=-current_time.second, microseconds=-current_time.microsecond)
        timestamp = current_time + time_offset

        schedule.append(timestamp)

    if timestamps:
        schedule = [int(time.timestamp()) for time in schedule]
    return schedule

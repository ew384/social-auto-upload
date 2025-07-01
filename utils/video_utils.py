import os
from pathlib import Path

SUPPORTED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm'}

def is_video_file(file_path):
    """检查文件是否为支持的视频格式"""
    return Path(file_path).suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS

def get_video_files(folder_path):
    """获取文件夹中所有支持的视频文件"""
    folder = Path(folder_path)
    video_files = []
    for file in folder.iterdir():
        if file.is_file() and is_video_file(file):
            video_files.append(file)
    return video_files
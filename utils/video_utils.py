# utils/video_utils.py
from pathlib import Path

def is_video_file(filename):
    """检查文件是否为视频格式"""
    video_extensions = {
        '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', 
        '.m4v', '.3gp', '.3g2', '.f4v', '.asf', '.rm', '.rmvb',
        '.vob', '.mpg', '.mpeg', '.mpe', '.mpv', '.m2v', '.m4p',
        '.ogv', '.ogg', '.dv', '.qt', '.yuv', '.divx', '.xvid'
    }
    return Path(filename).suffix.lower() in video_extensions

def get_video_files(directory_path):
    """获取目录中的所有视频文件"""
    directory = Path(directory_path)
    video_files = []
    
    for file_path in directory.iterdir():
        if file_path.is_file() and is_video_file(file_path.name):
            video_files.append(file_path)
    
    return sorted(video_files)
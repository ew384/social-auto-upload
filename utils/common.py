# utils/common.py - 合并通用功能到一个文件
import sqlite3
from pathlib import Path
from conf import BASE_DIR

def get_account_info_from_db(cookie_file: str):
    """从数据库获取账号信息 - 从 TencentVideo 移出来的通用方法"""
    try:
        cookie_filename = Path(cookie_file).name
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT userName, type FROM user_info WHERE filePath = ?', (cookie_filename,))
            result = cursor.fetchone()
            if result:
                username, platform_type = result
                platform_map = {1: 'xiaohongshu', 2: 'weixin', 3: 'douyin', 4: 'kuaishou'}
                return {
                    'username': username,
                    'platform': platform_map.get(platform_type, 'unknown'),
                    'platform_type': platform_type
                }
            return None
    except Exception as e:
        print(f"⚠️ 获取账号信息失败: {e}")
        return None
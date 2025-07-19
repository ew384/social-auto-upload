# utils/common.py
import sqlite3
import uuid
import asyncio
from pathlib import Path
from conf import BASE_DIR

def get_account_info_from_db(cookie_file: str):
    """从数据库获取账号信息 """
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

def save_complete_account_info(user_input_id: str, platform_type: int, cookie_file: str, account_info: dict = None) -> bool:
    """一次性保存完整账号信息（cookies + avatar + account info）"""
    try:
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            
            # 🔥 检查并添加新字段（如果不存在）
            cursor.execute("PRAGMA table_info(user_info)")
            columns = [column[1] for column in cursor.fetchall()]
            
            new_columns = {
                'account_id': 'TEXT',
                'real_name': 'TEXT', 
                'followers_count': 'INTEGER',
                'videos_count': 'INTEGER',
                'bio': 'TEXT',
                'avatar_url': 'TEXT',
                'local_avatar': 'TEXT',
                'updated_at': 'TEXT'
            }
            
            for column_name, column_type in new_columns.items():
                if column_name not in columns:
                    try:
                        cursor.execute(f'ALTER TABLE user_info ADD COLUMN {column_name} {column_type}')
                    except sqlite3.OperationalError:
                        pass
            
            # 🔥 一次性插入所有信息
            if account_info:
                # 有账号信息：插入完整数据
                cursor.execute('''
                    INSERT INTO user_info (
                        type, filePath, userName, status, 
                        account_id, real_name, followers_count, videos_count, 
                        bio, avatar_url, local_avatar, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ''', (
                    platform_type,
                    cookie_file,
                    user_input_id,
                    1,
                    account_info.get('accountId'),
                    account_info.get('accountName') or user_input_id,  # 优先使用真实名称
                    account_info.get('followersCount'),
                    account_info.get('videosCount'),
                    account_info.get('bio'),
                    account_info.get('avatar'),
                    account_info.get('localAvatar')
                ))
                print(f"✅ 完整账号信息已保存: {account_info.get('accountName')} (粉丝: {account_info.get('followersCount')})")
            else:
                # 无账号信息：只插入基础数据
                cursor.execute('''
                    INSERT INTO user_info (
                        type, filePath, userName, status, updated_at
                    ) VALUES (?, ?, ?, ?, datetime('now'))
                ''', (platform_type, cookie_file, user_input_id, 1))
                print(f"⚠️ 仅保存基础登录信息: {user_input_id}")
            
            conn.commit()
            return True
            
    except Exception as e:
        print(f"❌ 保存账号信息失败: {e}")
        return False

async def process_login_success(adapter, tab_id: str, user_id: str, platform_type: int, platform_name: str, status_queue, sleep_time: int = 2):
    """🔥 登录成功后的通用处理流程"""
    try:
        # 等待页面稳定
        await asyncio.sleep(sleep_time)
        
        # 生成cookie文件名并保存
        uuid_v1 = uuid.uuid1()
        cookie_file = f"{uuid_v1}.json"
        await adapter.save_cookies(tab_id, str(Path(BASE_DIR / "cookiesFile" / cookie_file)))
        
        # 验证cookie有效性
        from myUtils.auth import check_cookie
        if not await check_cookie(platform_type, cookie_file):
            status_queue.put("500")
            return
        
        # 获取账号信息并下载头像
        account_info = adapter.get_account_info_with_avatar(tab_id, platform_name, str(BASE_DIR))
        
        # 保存到数据库
        save_complete_account_info(user_id, platform_type, cookie_file, account_info)
        
        status_queue.put("200")
        
    except Exception as e:
        print(f"❌ 登录后处理失败: {e}")
        status_queue.put("500")

def get_platform_name(platform_type: int) -> str:
    """获取平台名称"""
    platform_map = {1: 'xiaohongshu', 2: 'wechat', 3: 'douyin', 4: 'kuaishou'}
    return platform_map.get(platform_type, 'unknown')
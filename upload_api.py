#!/usr/bin/env python3
# upload_api.py - 包装现有CLI的HTTP API服务

import os
import json
import asyncio
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import threading
import time
from utils.video_utils import is_video_file
import sqlite3
from utils.files_times import get_title_and_hashtags
# 导入现有的上传模块
from cli_main import main as cli_main
import sys

app = Flask(__name__)

# 配置
app.config['JSON_AS_ASCII'] = False
UPLOAD_FOLDER = './temp_uploads'

ALLOWED_EXTENSIONS = {
    'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv', 'webm', 
    'm4v', '3gp', '3g2', 'f4v', 'asf', 'rm', 'rmvb',
    'vob', 'mpg', 'mpeg', 'mpe', 'mpv', 'm2v'
}
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 任务状态存储（生产环境建议用Redis）
task_status = {}

def allowed_file(filename):
    return is_video_file(filename)

class UploadTask:
    def __init__(self, task_id, platform, account, video_file, title, description, publish_type=0, schedule=None):
        self.task_id = task_id
        self.platform = platform
        self.account = account
        self.video_file = video_file
        self.title = title
        self.description = description
        self.publish_type = publish_type
        self.schedule = schedule
        self.status = 'pending'
        self.progress = 0
        self.message = ''
        self.error = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None

    def to_dict(self):
        return {
            'task_id': self.task_id,
            'platform': self.platform,
            'account': self.account,
            'status': self.status,
            'progress': self.progress,
            'message': self.message,
            'error': self.error,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

async def run_upload_task(task):
    """异步执行上传任务 - 直接调用上传逻辑"""
    try:
        task.status = 'running'
        task.started_at = datetime.now()
        task.message = '开始上传...'
        task.progress = 10
        
        # 验证文件存在
        if not os.path.exists(task.video_file):
            raise FileNotFoundError(f"视频文件不存在: {task.video_file}")
        
        # 验证文件格式
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v', '.3gp', '.3g2'}
        file_ext = Path(task.video_file).suffix.lower()
        if file_ext not in video_extensions:
            print(f"警告：{file_ext} 可能不是支持的视频格式")
        
        task.message = '获取账号信息...'
        task.progress = 20
        
        # 获取账号文件路径
        account_file = get_account_file_from_db_api(task.platform, task.account)
        if not account_file.exists():
            raise FileNotFoundError(f"未找到平台 {task.platform} 账号 {task.account} 的有效cookie文件")
        
        task.message = '解析标题和标签...'
        task.progress = 30
        
        # 获取标题和标签
        title, tags = get_title_and_hashtags(task.video_file, task.title, task.description)
        
        # 处理发布时间
        if task.publish_type == 0:
            publish_date = 0  # 立即发布
        else:
            if task.schedule:
                publish_date = datetime.strptime(task.schedule, '%Y-%m-%d %H:%M')
            else:
                publish_date = 0
        
        task.message = '初始化上传器...'
        task.progress = 40
        
        # 根据平台选择对应的上传器
        if task.platform == 'douyin':
            from uploader.douyin_uploader.main import douyin_setup, DouYinVideo
            
            task.message = '设置抖音环境...'
            await douyin_setup(str(account_file), handle=False)
            
            task.message = '开始上传到抖音...'
            task.progress = 60
            
            app = DouYinVideo(title, task.video_file, tags, publish_date, str(account_file))
            await app.main()
            
        elif task.platform == 'tencent':
            from uploader.tencent_uploader.main import weixin_setup, TencentVideo
            from utils.constant import TencentZoneTypes
            
            task.message = '设置微信视频号环境...'
            await weixin_setup(str(account_file), handle=True)
            
            task.message = '开始上传到微信视频号...'
            task.progress = 60
            
            category = TencentZoneTypes.LIFESTYLE.value
            app = TencentVideo(title, task.video_file, tags, publish_date, str(account_file), category)
            await app.main()
            
        elif task.platform == 'tiktok':
            from uploader.tk_uploader.main_chrome import tiktok_setup, TiktokVideo
            
            task.message = '设置TikTok环境...'
            await tiktok_setup(str(account_file), handle=True)
            
            task.message = '开始上传到TikTok...'
            task.progress = 60
            
            app = TiktokVideo(title, task.video_file, tags, publish_date, str(account_file))
            await app.main()
            
        elif task.platform == 'kuaishou':
            from uploader.ks_uploader.main import ks_setup, KSVideo
            
            task.message = '设置快手环境...'
            await ks_setup(str(account_file), handle=True)
            
            task.message = '开始上传到快手...'
            task.progress = 60
            
            app = KSVideo(title, task.video_file, tags, publish_date, str(account_file))
            await app.main()
            
        else:
            raise ValueError(f"不支持的平台: {task.platform}")
        
        task.status = 'completed'
        task.progress = 100
        task.message = '上传成功'
        task.completed_at = datetime.now()
        
    except Exception as e:
        task.status = 'failed'
        task.error = f"上传失败: {str(e)}"
        task.message = '上传失败'
        task.completed_at = datetime.now()
        print(f"任务执行异常: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理临时文件（只清理上传的临时文件，不清理用户指定的文件）
        try:
            if task.video_file.startswith(app.config['UPLOAD_FOLDER']):
                if os.path.exists(task.video_file):
                    os.remove(task.video_file)
        except:
            pass

def get_account_file_from_db_api(platform, account_name):
    """API版本的获取账号文件函数"""
    platform_map = {
        "xiaohongshu": 1,
        "tencent": 2, 
        "douyin": 3,
        "kuaishou": 4,
        "tiktok": 5,
        "小红书": 1,
        "微信视频号": 2,
        "抖音": 3,
        "快手": 4,
        "TikTok": 5
    }
    
    # 导入BASE_DIR
    from conf import BASE_DIR
    
    with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT filePath FROM user_info 
            WHERE type = ? AND userName = ? AND status = 1
        ''', (platform_map[platform], account_name))
        
        result = cursor.fetchone()
        if result:
            return Path(BASE_DIR / "cookiesFile" / result[0])
        else:
            raise FileNotFoundError(f"未找到平台 {platform} 账号 {account_name} 的有效cookie文件")
def run_task_in_thread(task):
    """在新线程中运行异步任务"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_upload_task(task))
    finally:
        loop.close()

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'success': True,
        'service': 'Video Upload API',
        'version': '1.0.0',
        'supported_platforms': ['douyin', 'tencent', 'tiktok', 'kuaishou'],
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/upload', methods=['POST'])
def upload_video():
    """上传并发布视频"""
    try:
        # 检查文件
        if 'video' not in request.files:
            return jsonify({'success': False, 'error': '未找到视频文件'}), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({'success': False, 'error': '未选择文件'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': '不支持的文件格式'}), 400
        
        # 获取参数
        platform = request.form.get('platform')
        account = request.form.get('account')
        title = request.form.get('title', '')
        description = request.form.get('description', '')
        publish_type = int(request.form.get('publish_type', 0))
        schedule = request.form.get('schedule', None)
        
        # 验证必需参数
        if not platform or not account:
            return jsonify({'success': False, 'error': '平台和账号参数必填'}), 400
        
        if platform not in ['douyin', 'tencent', 'tiktok', 'kuaishou']:
            return jsonify({'success': False, 'error': '不支持的平台'}), 400
        
        # 保存文件
        filename = secure_filename(file.filename)
        task_id = str(uuid.uuid4())
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{task_id}_{filename}")
        file.save(file_path)
        
        # 如果没有标题，使用文件名
        if not title:
            title = os.path.splitext(filename)[0]
        
        # 创建任务
        task = UploadTask(
            task_id=task_id,
            platform=platform,
            account=account,
            video_file=file_path,
            title=title,
            description=description,
            publish_type=publish_type,
            schedule=schedule
        )
        
        task_status[task_id] = task
        
        # 在后台线程中执行任务
        thread = threading.Thread(target=run_task_in_thread, args=(task,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': '上传任务已创建',
            'status_url': f'/api/task/{task_id}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload/simple', methods=['POST'])
def simple_upload():
    """简化的上传接口 - 适合Agent调用"""
    try:
        data = request.get_json()
        
        platform = data.get('platform')
        account = data.get('account')
        video_file = data.get('video_file')  # 已存在的视频文件路径
        title = data.get('title', '')
        description = data.get('description', '')
        publish_type = data.get('publish_type', 0)
        schedule = data.get('schedule', None)
        
        # 验证必需参数
        if not all([platform, account, video_file]):
            return jsonify({'success': False, 'error': '平台、账号和视频文件路径必填'}), 400
        
        if not os.path.exists(video_file):
            return jsonify({'success': False, 'error': '视频文件不存在'}), 400
        
        # 创建任务
        task_id = str(uuid.uuid4())
        task = UploadTask(
            task_id=task_id,
            platform=platform,
            account=account,
            video_file=video_file,
            title=title,
            description=description,
            publish_type=publish_type,
            schedule=schedule
        )
        
        task_status[task_id] = task
        
        # 在后台线程中执行任务
        thread = threading.Thread(target=run_task_in_thread, args=(task,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': '上传任务已创建',
            'status': task.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/task/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """获取任务状态"""
    task = task_status.get(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    return jsonify({
        'success': True,
        'task': task.to_dict()
    })

@app.route('/api/tasks', methods=['GET'])
def list_tasks():
    """获取所有任务列表"""
    tasks = [task.to_dict() for task in task_status.values()]
    return jsonify({
        'success': True,
        'tasks': tasks,
        'total': len(tasks)
    })

@app.route('/api/platforms', methods=['GET'])
def get_platforms():
    """获取支持的平台列表"""
    return jsonify({
        'success': True,
        'platforms': [
            {'id': 'douyin', 'name': '抖音', 'description': '抖音短视频平台'},
            {'id': 'tencent', 'name': '微信视频号', 'description': '腾讯微信视频号'},
            {'id': 'tiktok', 'name': 'TikTok', 'description': 'TikTok国际版'},
            {'id': 'kuaishou', 'name': '快手', 'description': '快手短视频平台'}
        ]
    })

if __name__ == '__main__':
    print("🚀 启动视频上传API服务...")
    print("📋 支持的接口:")
    print("   GET  /api/health - 健康检查")
    print("   POST /api/upload - 上传视频文件并发布")
    print("   POST /api/upload/simple - 简化上传接口（适合Agent调用）")
    print("   GET  /api/task/<id> - 获取任务状态")
    print("   GET  /api/tasks - 获取所有任务")
    print("   GET  /api/platforms - 获取支持的平台")
    print("\n💡 使用示例:")
    print("curl -X POST http://127.0.0.1:5001/api/upload/simple \\")
    print("  -H 'Content-Type: application/json' \\")
    print("  -d '{\"platform\":\"douyin\",\"account\":\"endian\",\"video_file\":\"./videos/demo.mp4\",\"title\":\"测试视频\"}'")
    
    app.run(host='127.0.0.1', port=5001, debug=True)

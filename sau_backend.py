import asyncio
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from queue import Queue
from flask_cors import CORS
from myUtils.auth import check_cookie
from flask import Flask, request, jsonify, Response, render_template, send_from_directory
from conf import BASE_DIR
from myUtils.login import get_tencent_cookie, douyin_cookie_gen, get_ks_cookie, xiaohongshu_cookie_gen
from myUtils.postVideo import post_video_tencent, post_video_DouYin, post_video_ks, post_video_xhs,get_current_browser_mode,show_browser_status
from utils.video_utils import is_video_file
from datetime import datetime
import requests



active_queues = {}
app = Flask(__name__)

#允许所有来源跨域访问
CORS(app)

# 限制上传文件大小为1GB
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024

# 获取当前目录（假设 index.html 和 assets 在这里）
current_dir = os.path.dirname(os.path.abspath(__file__))

# 处理所有静态资源请求（未来打包用）
@app.route('/assets/<filename>')
def custom_static(filename):
    return send_from_directory(os.path.join(current_dir, 'assets'), filename)

# 处理 favicon.ico 静态资源（未来打包用）
@app.route('/favicon.ico')
def favicon(filename):
    return send_from_directory(os.path.join(current_dir, 'assets'), 'favicon.ico')

# （未来打包用）
@app.route('/')
def hello_world():  # put application's code here
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({
            "code": 200,
            "data": None,
            "msg": "No file part in the request"
        }), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            "code": 200,
            "data": None,
            "msg": "No selected file"
        }), 400
    try:
        # 保存文件到指定位置
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        filepath = Path(BASE_DIR / "videoFile" / f"{uuid_v1}_{file.filename}")
        file.save(filepath)
        return jsonify({"code":200,"msg": "File uploaded successfully", "data": f"{uuid_v1}_{file.filename}"}), 200
    except Exception as e:
        return jsonify({"code":200,"msg": str(e),"data":None}), 500

@app.route('/getFile', methods=['GET'])
def get_file():
    # 获取 filename 参数
    filename = request.args.get('filename')

    if not filename:
        return {"error": "filename is required"}, 400

    # 防止路径穿越攻击
    if '..' in filename or filename.startswith('/'):
        return {"error": "Invalid filename"}, 400

    # 拼接完整路径
    file_path = str(Path(BASE_DIR / "videoFile"))

    # 返回文件
    return send_from_directory(file_path,filename)


@app.route('/uploadSave', methods=['POST'])
def upload_save():
    if 'file' not in request.files:
        return jsonify({
            "code": 400,
            "data": None,
            "msg": "No file part in the request"
        }), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({
            "code": 400,
            "data": None,
            "msg": "No selected file"
        }), 400

    # 获取表单中的自定义文件名（可选）
    custom_filename = request.form.get('filename', None)
    if custom_filename:
        filename = custom_filename + "." + file.filename.split('.')[-1]
    else:
        filename = file.filename
    if not is_video_file(filename):
        return jsonify({
            "code": 400,
            "msg": "不支持的视频格式，请上传 MP4、MOV、AVI 等格式的视频",
            "data": None
        }), 400
    try:
        # 生成 UUID v1
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")

        # 构造文件名和路径
        final_filename = f"{uuid_v1}_{filename}"
        filepath = Path(BASE_DIR / "videoFile" / f"{uuid_v1}_{filename}")

        # 保存文件
        file.save(filepath)

        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                                INSERT INTO file_records (filename, filesize, file_path)
            VALUES (?, ?, ?)
                                ''', (filename, round(float(os.path.getsize(filepath)) / (1024 * 1024),2), final_filename))
            conn.commit()
            print("✅ 上传文件已记录")

        return jsonify({
            "code": 200,
            "msg": "File uploaded and saved successfully",
            "data": {
                "filename": filename,
                "filepath": final_filename
            }
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str("upload failed!"),
            "data": None
        }), 500

@app.route('/getFiles', methods=['GET'])
def get_all_files():
    try:
        # 使用 with 自动管理数据库连接
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row  # 允许通过列名访问结果
            cursor = conn.cursor()

            # 查询所有记录
            cursor.execute("SELECT * FROM file_records")
            rows = cursor.fetchall()

            # 将结果转为字典列表
            data = [dict(row) for row in rows]

        return jsonify({
            "code": 200,
            "msg": "success",
            "data": data
        }), 200
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str("get file failed!"),
            "data": None
        }), 500


@app.route("/getValidAccounts", methods=['GET'])
async def getValidAccounts():
    force_check = request.args.get('force', 'false').lower() == 'true'
    
    with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, type, filePath, userName, status, last_check_time, check_interval 
        FROM user_info''')
        rows = cursor.fetchall()
        
        current_time = datetime.now()
        platform_map = {1: '小红书', 2: '视频号', 3: '抖音', 4: '快手', 5: 'TikTok'}
        accounts = []
        
        for row in rows:
            user_id, type_val, file_path, user_name, status, last_check_time, check_interval = row
            
            # 判断是否需要验证（逻辑保持不变）
            should_check = force_check
            if not should_check and last_check_time:
                try:
                    last_check = datetime.fromisoformat(last_check_time)
                    should_check = (current_time - last_check).total_seconds() > (check_interval or 3600)
                except (ValueError, TypeError):
                    should_check = True
            elif not last_check_time:
                should_check = True
                
            # 🔥 简化：直接调用验证函数，底层自动选择最优模式
            if should_check:
                try:
                    flag = await check_cookie(type_val, file_path)
                    new_status = 1 if flag else 0
                    
                    cursor.execute('''
                    UPDATE user_info 
                    SET status = ?, last_check_time = ?
                    WHERE id = ?
                    ''', (new_status, current_time.isoformat(), user_id))
                    conn.commit()
                    
                    status = new_status
                    print(f"✅ 验证账号 {user_name}: {'正常' if new_status else '异常'}")
                except Exception as e:
                    print(f"❌ 验证账号 {user_name} 失败: {e}")
            
            # 构建账号信息
            account = {
                'id': user_id,
                'type': type_val, 
                'filePath': file_path,
                'name': user_name,
                'userName': user_name,
                'platform': platform_map.get(type_val, '未知'),
                'status': '正常' if status == 1 else '异常',
                'avatar': '/default-avatar.png'
            }
            
            accounts.append(account)
        
        return jsonify({
            "code": 200,
            "msg": "success", 
            "data": accounts,
            "browserMode": get_current_browser_mode()  # 简化的模式获取
        }), 200

@app.route('/deleteFile', methods=['GET'])
def delete_file():
    file_id = request.args.get('id')

    if not file_id or not file_id.isdigit():
        return jsonify({
            "code": 400,
            "msg": "Invalid or missing file ID",
            "data": None
        }), 400

    try:
        # 获取数据库连接
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 查询要删除的记录
            cursor.execute("SELECT * FROM file_records WHERE id = ?", (file_id,))
            record = cursor.fetchone()

            if not record:
                return jsonify({
                    "code": 404,
                    "msg": "File not found",
                    "data": None
                }), 404

            record = dict(record)

            # 删除数据库记录
            cursor.execute("DELETE FROM file_records WHERE id = ?", (file_id,))
            conn.commit()

        return jsonify({
            "code": 200,
            "msg": "File deleted successfully",
            "data": {
                "id": record['id'],
                "filename": record['filename']
            }
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str("delete failed!"),
            "data": None
        }), 500

@app.route('/deleteAccount', methods=['GET'])
def delete_account():
    account_id = int(request.args.get('id'))

    try:
        # 获取数据库连接
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 查询要删除的记录
            cursor.execute("SELECT * FROM user_info WHERE id = ?", (account_id,))
            record = cursor.fetchone()

            if not record:
                return jsonify({
                    "code": 404,
                    "msg": "account not found",
                    "data": None
                }), 404

            record = dict(record)

            # 删除数据库记录
            cursor.execute("DELETE FROM user_info WHERE id = ?", (account_id,))
            conn.commit()

        return jsonify({
            "code": 200,
            "msg": "account deleted successfully",
            "data": None
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str("delete failed!"),
            "data": None
        }), 500


# SSE 登录接口
@app.route('/login')
def login():
    """
    ✅ 保留并简化
    自动选择最优登录方式，无需判断浏览器模式
    """
    type = request.args.get('type')
    id = request.args.get('id')

    # 模拟一个用于异步通信的队列
    status_queue = Queue()
    active_queues[id] = status_queue

    # 🔥 简化：直接使用统一的登录函数，底层自动选择最优实现
    thread = threading.Thread(target=run_async_function, args=(type, id, status_queue), daemon=True)
    thread.start()
    
    response = Response(sse_stream(status_queue,), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Content-Type'] = 'text/event-stream'
    response.headers['Connection'] = 'keep-alive'
    return response

@app.route('/setBrowserMode', methods=['POST'])
def set_browser_mode():
    """
    ✅ 保留 - 用于开发调试
    虽然现在是自动模式，但保留手动切换功能用于测试
    """
    data = request.get_json()
    use_multi_browser = data.get('useMultiBrowser', True)
    
    # 通过环境变量临时切换模式
    import os
    os.environ['USE_MULTI_BROWSER'] = str(use_multi_browser).lower()
    
    # 重新加载智能导入模块
    try:
        import importlib
        import utils.smart_playwright
        importlib.reload(utils.smart_playwright)
        
        mode_name = "multi-account-browser" if use_multi_browser else "playwright"
        
        return jsonify({
            "code": 200,
            "msg": f"浏览器模式已切换到: {mode_name}",
            "data": {
                "mode": mode_name,
                "useMultiBrowser": use_multi_browser,
                "note": "重新加载模块成功"
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": f"切换模式失败: {str(e)}",
            "data": None
        }), 500

# 添加新的API端点：获取当前浏览器模式
@app.route('/getBrowserMode', methods=['GET'])
def get_browser_mode():
    """获取当前浏览器模式"""
    mode_name = "multi-account-browser" if USE_MULTI_ACCOUNT_BROWSER else "playwright"
    
    return jsonify({
        "code": 200,
        "msg": "success",
        "data": {
            "mode": mode_name,
            "useMultiBrowser": USE_MULTI_ACCOUNT_BROWSER
        }
    }), 200

@app.route('/getBrowserStatus', methods=['GET'])
def get_browser_status():
    """
    ✅ 保留并简化 - 合并了原来的 check_multi_browser_status 功能
    """
    from myUtils.postVideo import get_current_browser_mode
    
    current_mode = get_current_browser_mode()
    
    multi_browser_available = False
    multi_browser_info = {}
    
    if current_mode == "multi-account-browser":
        try:
            import requests
            response = requests.get('http://localhost:3000/api/health', timeout=3)
            
            if response.status_code == 200:
                multi_browser_available = True
                result = response.json()
                multi_browser_info = {
                    "connected": True,
                    "version": result.get("version", "unknown"),
                    "renderer": result.get("renderer", "unknown"),
                    "uptime": result.get("uptime", 0)
                }
            else:
                multi_browser_info = {
                    "connected": False,
                    "error": f"HTTP {response.status_code}"
                }
        except Exception as e:
            multi_browser_info = {
                "connected": False,
                "error": str(e)
            }
    else:
        multi_browser_info = {
            "connected": False,
            "reason": "使用传统模式"
        }
    
    return jsonify({
        "code": 200,
        "msg": "success",
        "data": {
            "currentMode": current_mode,
            "multiBrowserAvailable": multi_browser_available,
            "multiBrowserInfo": multi_browser_info,
            "apiUrl": "http://localhost:3000"
        }
    }), 200


@app.route('/postVideo', methods=['POST'])
def postVideo():
    """发布视频 - 自动选择最优模式"""
    data = request.get_json()
    
    file_list = data.get('fileList', [])
    account_list = data.get('accountList', [])
    type_val = data.get('type')
    title = data.get('title')
    tags = data.get('tags')
    category = data.get('category')
    enableTimer = data.get('enableTimer')
    
    if category == 0:
        category = None

    videos_per_day = data.get('videosPerDay')
    daily_times = data.get('dailyTimes')
    start_days = data.get('startDays')
    
    current_mode = get_current_browser_mode()
    print(f"🔧 当前浏览器模式: {current_mode}")
    
    try:
        # 🔥 最简单的调用 - 底层自动选择最优实现
        match type_val:
            case 1:  # 小红书
                post_video_xhs(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times, start_days)
            case 2:  # 视频号
                post_video_tencent(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times, start_days)
            case 3:  # 抖音
                post_video_DouYin(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times, start_days)
            case 4:  # 快手
                post_video_ks(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times, start_days)
        
        return jsonify({
            "code": 200,
            "msg": "发布任务已提交",
            "data": {
                "browserMode": current_mode
            }
        }), 200
        
    except Exception as e:
        print(f"❌ 发布失败: {e}")
        return jsonify({
            "code": 500,
            "msg": f"发布失败: {str(e)}",
            "data": None
        }), 500


@app.route('/postVideoBatch', methods=['POST'])
def postVideoBatch():
    """
    批量发布视频 - 超简化版本
    自动使用最优浏览器模式，无需复杂的判断逻辑
    """
    try:
        data_list = request.get_json()

        if not isinstance(data_list, list):
            return jsonify({
                "code": 400, 
                "msg": "请求数据应为数组格式", 
                "data": None
            }), 400

        total_tasks = len(data_list)
        current_mode = get_current_browser_mode()
        
        print(f"🚀 接收到 {total_tasks} 个批量发布任务")
        print(f"🔧 当前浏览器模式: {current_mode}")
        
        # 🔥 关键简化：无需判断模式，直接调用原有函数
        # 底层会自动选择最优的浏览器实现
        
        success_count = 0
        failed_count = 0
        results = []
        
        for index, data in enumerate(data_list, 1):
            print(f"\n📋 处理任务 {index}/{total_tasks}")
            
            try:
                # 提取任务参数
                file_list = data.get('fileList', [])
                account_list = data.get('accountList', [])
                type_val = data.get('type')
                title = data.get('title', f'批量任务_{index}')
                tags = data.get('tags', [])
                category = data.get('category')
                enableTimer = data.get('enableTimer', False)
                
                if category == 0:
                    category = None

                videos_per_day = data.get('videosPerDay', 1)
                daily_times = data.get('dailyTimes')
                start_days = data.get('startDays', 0)
                
                # 平台名称映射
                platform_names = {1: "小红书", 2: "视频号", 3: "抖音", 4: "快手"}
                platform_name = platform_names.get(type_val, f"平台{type_val}")
                
                print(f"   平台: {platform_name}")
                print(f"   标题: {title}")
                print(f"   文件: {len(file_list)} 个")
                print(f"   账号: {len(account_list)} 个")
                
                # 🔥 核心简化：直接调用对应的发布函数
                # 所有复杂的浏览器模式选择都由底层自动处理
                match type_val:
                    case 1:  # 小红书
                        post_video_xhs(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times, start_days)
                    case 2:  # 视频号
                        post_video_tencent(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times, start_days)
                    case 3:  # 抖音
                        post_video_DouYin(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times, start_days)
                    case 4:  # 快手
                        post_video_ks(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times, start_days)
                    case _:
                        raise ValueError(f"不支持的平台类型: {type_val}")
                
                # 计算成功的任务数量
                task_success_count = len(file_list) * len(account_list)
                success_count += task_success_count
                
                results.append({
                    "index": index,
                    "platform": platform_name,
                    "title": title,
                    "success": True,
                    "files": len(file_list),
                    "accounts": len(account_list),
                    "total_uploads": task_success_count,
                    "message": f"成功提交 {task_success_count} 个上传任务"
                })
                
                print(f"   ✅ 任务 {index} 提交成功")
                
            except Exception as task_error:
                print(f"   ❌ 任务 {index} 失败: {task_error}")
                
                # 估算失败的任务数量
                file_count = len(data.get('fileList', []))
                account_count = len(data.get('accountList', []))
                task_failed_count = file_count * account_count
                failed_count += task_failed_count
                
                results.append({
                    "index": index,
                    "platform": platform_names.get(data.get('type'), "未知"),
                    "title": data.get('title', f'任务_{index}'),
                    "success": False,
                    "files": file_count,
                    "accounts": account_count,
                    "total_uploads": 0,
                    "error": str(task_error),
                    "message": f"任务失败: {str(task_error)}"
                })
        
        # 生成总结报告
        total_estimated_uploads = success_count + failed_count
        success_rate = (success_count / total_estimated_uploads * 100) if total_estimated_uploads > 0 else 0
        
        summary = {
            "total_tasks": total_tasks,
            "total_estimated_uploads": total_estimated_uploads,
            "success_uploads": success_count,
            "failed_uploads": failed_count,
            "success_rate": round(success_rate, 1),
            "browser_mode": current_mode
        }
        
        print(f"\n📊 批量发布总结:")
        print(f"   总任务数: {total_tasks}")
        print(f"   预计上传数: {total_estimated_uploads}")
        print(f"   成功提交: {success_count}")
        print(f"   提交失败: {failed_count}")
        print(f"   成功率: {success_rate:.1f}%")
        print(f"   浏览器模式: {current_mode}")
        
        return jsonify({
            "code": 200,
            "msg": f"批量发布完成: {success_count}/{total_estimated_uploads} 成功提交",
            "data": {
                "summary": summary,
                "results": results
            }
        }), 200

    except Exception as e:
        print(f"❌ 批量发布系统错误: {e}")
        return jsonify({
            "code": 500,
            "msg": f"批量发布失败: {str(e)}",
            "data": None
        }), 500


# ========================================
# 可选：添加批量任务状态查询接口
# ========================================

# 全局任务状态存储（可选，用于更高级的任务管理）
batch_task_status = {}

@app.route('/postVideoBatchAsync', methods=['POST'])
def postVideoBatchAsync():
    """
    异步批量发布视频 - 高级版本
    返回任务ID，可以通过其他接口查询进度
    """
    try:
        data_list = request.get_json()
        
        if not isinstance(data_list, list):
            return jsonify({
                "code": 400,
                "msg": "请求数据应为数组格式",
                "data": None
            }), 400
        
        # 生成任务ID
        import uuid
        import threading
        from datetime import datetime
        
        task_id = str(uuid.uuid4())[:8]
        current_mode = get_current_browser_mode()
        
        # 初始化任务状态
        batch_task_status[task_id] = {
            "task_id": task_id,
            "status": "running",
            "total_tasks": len(data_list),
            "completed_tasks": 0,
            "success_count": 0,
            "failed_count": 0,
            "browser_mode": current_mode,
            "start_time": datetime.now().isoformat(),
            "results": []
        }
        
        print(f"🚀 启动异步批量任务: {task_id} ({len(data_list)} 个任务)")
        
        # 异步执行批量任务
        def run_batch_async():
            try:
                for index, data in enumerate(data_list, 1):
                    try:
                        # 更新进度
                        batch_task_status[task_id]["completed_tasks"] = index - 1
                        
                        # 执行任务（与同步版本相同的逻辑）
                        file_list = data.get('fileList', [])
                        account_list = data.get('accountList', [])
                        type_val = data.get('type')
                        title = data.get('title', f'批量任务_{index}')
                        tags = data.get('tags', [])
                        category = data.get('category')
                        enableTimer = data.get('enableTimer', False)
                        
                        if category == 0:
                            category = None

                        videos_per_day = data.get('videosPerDay', 1)
                        daily_times = data.get('dailyTimes')
                        start_days = data.get('startDays', 0)
                        
                        # 执行发布
                        match type_val:
                            case 1:
                                post_video_xhs(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times, start_days)
                            case 2:
                                post_video_tencent(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times, start_days)
                            case 3:
                                post_video_DouYin(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times, start_days)
                            case 4:
                                post_video_ks(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times, start_days)
                        
                        # 记录成功
                        success_uploads = len(file_list) * len(account_list)
                        batch_task_status[task_id]["success_count"] += success_uploads
                        batch_task_status[task_id]["results"].append({
                            "index": index,
                            "success": True,
                            "uploads": success_uploads,
                            "title": title
                        })
                        
                        print(f"✅ 异步任务 {task_id} - 子任务 {index} 完成")
                        
                    except Exception as task_error:
                        # 记录失败
                        failed_uploads = len(data.get('fileList', [])) * len(data.get('accountList', []))
                        batch_task_status[task_id]["failed_count"] += failed_uploads
                        batch_task_status[task_id]["results"].append({
                            "index": index,
                            "success": False,
                            "uploads": 0,
                            "error": str(task_error),
                            "title": data.get('title', f'任务_{index}')
                        })
                        
                        print(f"❌ 异步任务 {task_id} - 子任务 {index} 失败: {task_error}")
                
                # 任务完成
                batch_task_status[task_id]["status"] = "completed"
                batch_task_status[task_id]["completed_tasks"] = len(data_list)
                batch_task_status[task_id]["end_time"] = datetime.now().isoformat()
                
                print(f"🎉 异步批量任务 {task_id} 完成")
                
            except Exception as e:
                batch_task_status[task_id]["status"] = "failed"
                batch_task_status[task_id]["error"] = str(e)
                print(f"❌ 异步批量任务 {task_id} 系统错误: {e}")
        
        # 启动后台线程
        thread = threading.Thread(target=run_batch_async, daemon=True)
        thread.start()
        
        return jsonify({
            "code": 200,
            "msg": "异步批量任务已启动",
            "data": {
                "task_id": task_id,
                "total_tasks": len(data_list),
                "browser_mode": current_mode,
                "status_url": f"/getBatchTaskStatus?task_id={task_id}"
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": f"启动异步批量任务失败: {str(e)}",
            "data": None
        }), 500

@app.route('/getBatchTaskStatus', methods=['GET'])
def getBatchTaskStatus():
    """查询批量任务状态"""
    task_id = request.args.get('task_id')
    
    if not task_id:
        return jsonify({
            "code": 400,
            "msg": "缺少 task_id 参数",
            "data": None
        }), 400
    
    if task_id not in batch_task_status:
        return jsonify({
            "code": 404,
            "msg": "任务不存在",
            "data": None
        }), 404
    
    task_info = batch_task_status[task_id]
    
    # 计算进度百分比
    progress = 0
    if task_info["total_tasks"] > 0:
        progress = round(task_info["completed_tasks"] / task_info["total_tasks"] * 100, 1)
    
    return jsonify({
        "code": 200,
        "msg": "success",
        "data": {
            **task_info,
            "progress": progress
        }
    }), 200

@app.route('/getAllBatchTasks', methods=['GET'])
def getAllBatchTasks():
    """获取所有批量任务状态"""
    tasks = []
    
    for task_id, task_info in batch_task_status.items():
        progress = 0
        if task_info["total_tasks"] > 0:
            progress = round(task_info["completed_tasks"] / task_info["total_tasks"] * 100, 1)
        
        tasks.append({
            "task_id": task_id,
            "status": task_info["status"],
            "progress": progress,
            "total_tasks": task_info["total_tasks"],
            "completed_tasks": task_info["completed_tasks"],
            "success_count": task_info["success_count"],
            "failed_count": task_info["failed_count"],
            "browser_mode": task_info["browser_mode"],
            "start_time": task_info["start_time"]
        })
    
    return jsonify({
        "code": 200,
        "msg": "success",
        "data": {
            "tasks": tasks,
            "total": len(tasks)
        }
    }), 200

@app.route('/updateUserinfo', methods=['POST'])
def updateUserinfo():
    # 获取JSON数据
    data = request.get_json()

    # 从JSON数据中提取 type 和 userName
    user_id = data.get('id')
    type = data.get('type')
    userName = data.get('userName')
    try:
        # 获取数据库连接
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 更新数据库记录
            cursor.execute('''
                           UPDATE user_info
                           SET type     = ?,
                               userName = ?
                           WHERE id = ?;
                           ''', (type, userName, user_id))
            conn.commit()

        return jsonify({
            "code": 200,
            "msg": "account update successfully",
            "data": None
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str("update failed!"),
            "data": None
        }), 500


# 包装函数：在线程中运行异步函数
def run_async_function(type,id,status_queue):
    match type:
        case '1':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(xiaohongshu_cookie_gen(id, status_queue))
            loop.close()
        case '2':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(get_tencent_cookie(id,status_queue))
            loop.close()
        case '3':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(douyin_cookie_gen(id,status_queue))
            loop.close()
        case '4':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(get_ks_cookie(id,status_queue))
            loop.close()

# SSE 流生成器函数
def sse_stream(status_queue):
    while True:
        if not status_queue.empty():
            msg = status_queue.get()
            yield f"data: {msg}\n\n"
            if msg == "200" or msg == "500":
                print(f"✅ SSE 发送完成状态: {msg}")
                break
        else:
            # 避免 CPU 占满
            time.sleep(0.1)

# 获取所有分组
@app.route('/getGroups', methods=['GET'])
def get_groups():
    try:
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    g.id, 
                    g.name, 
                    g.description, 
                    g.color,
                    g.icon,
                    g.sort_order,
                    g.created_at,
                    g.updated_at,
                    COUNT(u.id) as account_count
                FROM account_groups g
                LEFT JOIN user_info u ON g.id = u.group_id
                GROUP BY g.id, g.name, g.description, g.color, g.icon, g.sort_order, g.created_at, g.updated_at
                ORDER BY g.sort_order ASC, g.id ASC
            ''')
            groups = [dict(row) for row in cursor.fetchall()]
            
        return jsonify({"code": 200, "msg": "success", "data": groups}), 200
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e), "data": None}), 500

# 创建分组
@app.route('/createGroup', methods=['POST'])
def create_group():
    data = request.get_json()
    name = data.get('name')
    description = data.get('description', '')
    color = data.get('color', '#5B73DE')
    icon = data.get('icon', 'Users')
    sort_order = data.get('sort_order', 0)
    
    if not name:
        return jsonify({"code": 400, "msg": "分组名称不能为空", "data": None}), 400
    
    try:
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO account_groups (name, description, color, icon, sort_order, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            ''', (name, description, color, icon, sort_order))
            group_id = cursor.lastrowid
            conn.commit()
            
        return jsonify({"code": 200, "msg": "分组创建成功", "data": {"id": group_id}}), 200
    except sqlite3.IntegrityError:
        return jsonify({"code": 400, "msg": "分组名称已存在", "data": None}), 400
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e), "data": None}), 500

# 更新分组
@app.route('/updateGroup', methods=['POST'])
def update_group():
    data = request.get_json()
    group_id = data.get('id')
    name = data.get('name')
    description = data.get('description', '')
    color = data.get('color', '#5B73DE')
    icon = data.get('icon', 'Users')
    sort_order = data.get('sort_order', 0)
    
    if not group_id or not name:
        return jsonify({"code": 400, "msg": "分组ID和名称不能为空", "data": None}), 400
    
    try:
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE account_groups 
                SET name = ?, description = ?, color = ?, icon = ?, sort_order = ?, updated_at = datetime('now')
                WHERE id = ?
            ''', (name, description, color, icon, sort_order, group_id))
            conn.commit()
            
        return jsonify({"code": 200, "msg": "分组更新成功", "data": None}), 200
    except sqlite3.IntegrityError:
        return jsonify({"code": 400, "msg": "分组名称已存在", "data": None}), 400
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e), "data": None}), 500

# 更新账号分组
@app.route('/updateAccountGroup', methods=['POST'])
def update_account_group():
    data = request.get_json()
    account_id = data.get('account_id')
    group_id = data.get('group_id')  # None 表示移出分组
    
    try:
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_info
                SET group_id = ?
                WHERE id = ?
            ''', (group_id, account_id))
            conn.commit()
            
        return jsonify({"code": 200, "msg": "账号分组更新成功", "data": None}), 200
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e), "data": None}), 500

# 删除分组
@app.route('/deleteGroup', methods=['GET'])
def delete_group():
    group_id = request.args.get('id')
    
    try:
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            
            # 先将该分组的账号设为未分组
            cursor.execute('UPDATE user_info SET group_id = NULL WHERE group_id = ?', (group_id,))
            
            # 删除分组
            cursor.execute('DELETE FROM account_groups WHERE id = ?', (group_id,))
            conn.commit()
            
        return jsonify({"code": 200, "msg": "分组删除成功", "data": None}), 200
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e), "data": None}), 500

# 获取带分组信息的账号列表
@app.route("/getAccountsWithGroups", methods=['GET'])
async def getAccountsWithGroups():
    force_check = request.args.get('force', 'false').lower() == 'true'
    
    with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT u.id, u.type, u.filePath, u.userName, u.status, u.group_id, 
               u.last_check_time, u.check_interval, 
               g.name as group_name, g.color as group_color, g.icon as group_icon
        FROM user_info u
        LEFT JOIN account_groups g ON u.group_id = g.id
        ''')
        rows = cursor.fetchall()
        
        current_time = datetime.now()
        platform_map = {1: '小红书', 2: '视频号', 3: '抖音', 4: '快手', 5: 'TikTok'}
        accounts = []
        
        for row in rows:
            user_id, type_val, file_path, user_name, status, group_id, last_check_time, check_interval, group_name, group_color, group_icon = row
            
            # 保持与原有API完全相同的验证逻辑
            should_check = force_check
            if not should_check and last_check_time:
                try:
                    last_check = datetime.fromisoformat(last_check_time)
                    should_check = (current_time - last_check).total_seconds() > (check_interval or 3600)
                except (ValueError, TypeError):
                    should_check = True
            elif not last_check_time:
                should_check = True
                
            if should_check:
                try:
                    flag = await check_cookie(type_val, file_path)
                    new_status = 1 if flag else 0
                    
                    cursor.execute('''
                    UPDATE user_info 
                    SET status = ?, last_check_time = ?
                    WHERE id = ?
                    ''', (new_status, current_time.isoformat(), user_id))
                    conn.commit()
                    
                    status = new_status
                    print(f"✅ 验证账号 {user_name}: {'正常' if new_status else '异常'}")
                except Exception as e:
                    print(f"❌ 验证账号 {user_name} 失败: {e}")
            
            # 构建账号信息
            account = {
                'id': user_id,
                'type': type_val, 
                'filePath': file_path,
                'name': user_name,
                'userName': user_name,
                'platform': platform_map.get(type_val, '未知'),
                'status': '正常' if status == 1 else '异常',
                'avatar': '/default-avatar.png',
                # 分组相关字段
                'group_id': group_id,
                'group_name': group_name,
                'group_color': group_color,
                'group_icon': group_icon
            }
            
            accounts.append(account)
        
        return jsonify({
            "code": 200,
            "msg": "success", 
            "data": accounts
        }), 200
if __name__ == '__main__':
    print("🚀 Social Auto Upload 启动")
    print("=" * 50)
    show_browser_status()
    app.run(host='127.0.0.1' ,port=5409)

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
from myUtils.postVideo import post_video_tencent, post_video_DouYin, post_video_ks, post_video_xhs
from utils.video_utils import is_video_file
from datetime import datetime
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
        
        # 获取所有账号信息（包括新添加的字段）
        cursor.execute('''
        SELECT id, type, filePath, userName, status, last_check_time, check_interval 
        FROM user_info''')
        rows = cursor.fetchall()
        
        current_time = datetime.now()
        platform_map = {1: '小红书', 2: '视频号', 3: '抖音', 4: '快手', 5: 'TikTok'}
        accounts = []
        
        for row in rows:
            user_id, type_val, file_path, user_name, status, last_check_time, check_interval = row
            
            # 判断是否需要验证
            should_check = force_check
            if not should_check and last_check_time:
                try:
                    last_check = datetime.fromisoformat(last_check_time)
                    should_check = (current_time - last_check).total_seconds() > (check_interval or 3600)
                except (ValueError, TypeError):
                    should_check = True
            elif not last_check_time:
                should_check = True
                
            # 如果需要验证，则进行验证
            if should_check:
                try:
                    flag = await check_cookie(type_val, file_path)
                    new_status = 1 if flag else 0
                    
                    # 更新状态和检查时间
                    cursor.execute('''
                    UPDATE user_info 
                    SET status = ?, last_check_time = ?
                    WHERE id = ?
                    ''', (new_status, current_time.isoformat(), user_id))
                    conn.commit()
                    
                    status = new_status  # 更新当前状态
                    print(f"✅ 验证账号 {user_name}: {'正常' if new_status else '异常'}")
                except Exception as e:
                    print(f"❌ 验证账号 {user_name} 失败: {e}")
                    # 验证失败时不更新状态，保持原状态
            
            # 构建账号信息（保持原有的数据结构）
            account = {
                'id': user_id,
                'type': type_val, 
                'filePath': file_path,  # 保持原有字段名
                'name': user_name,
                'userName': user_name,
                'platform': platform_map.get(type_val, '未知'),
                'status': '正常' if status == 1 else '异常',
                'avatar': '/default-avatar.png'
            }
            
            # 返回所有账号（包括异常账号）
            accounts.append(account)
        
        return jsonify({
            "code": 200,
            "msg": "success", 
            "data": accounts
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
    # 1 小红书 2 视频号 3 抖音 4 快手
    type = request.args.get('type')
    # 账号名
    id = request.args.get('id')

    # 模拟一个用于异步通信的队列
    status_queue = Queue()
    active_queues[id] = status_queue

    def on_close():
        print(f"清理队列: {id}")
        del active_queues[id]
    # 启动异步任务线程
    thread = threading.Thread(target=run_async_function, args=(type,id,status_queue), daemon=True)
    thread.start()
    response = Response(sse_stream(status_queue,), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'  # 关键：禁用 Nginx 缓冲
    response.headers['Content-Type'] = 'text/event-stream'
    response.headers['Connection'] = 'keep-alive'
    return response

@app.route('/postVideo', methods=['POST'])
def postVideo():
    # 获取JSON数据
    data = request.get_json()

    # 从JSON数据中提取fileList和accountList
    file_list = data.get('fileList', [])
    account_list = data.get('accountList', [])
    type = data.get('type')
    title = data.get('title')
    tags = data.get('tags')
    category = data.get('category')
    enableTimer = data.get('enableTimer')
    if category == 0:
        category = None

    videos_per_day = data.get('videosPerDay')
    daily_times = data.get('dailyTimes')
    start_days = data.get('startDays')
    # 打印获取到的数据（仅作为示例）
    print("File List:", file_list)
    print("Account List:", account_list)
    match type:
        case 1:
            post_video_xhs(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                               start_days)
        case 2:
            post_video_tencent(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                               start_days)
        case 3:
            post_video_DouYin(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                      start_days)
        case 4:
            post_video_ks(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                      start_days)
    # 返回响应给客户端
    return jsonify(
        {
            "code": 200,
            "msg": None,
            "data": None
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

@app.route('/postVideoBatch', methods=['POST'])
def postVideoBatch():
    data_list = request.get_json()

    if not isinstance(data_list, list):
        return jsonify({"error": "Expected a JSON array"}), 400
    for data in data_list:
        # 从JSON数据中提取fileList和accountList
        file_list = data.get('fileList', [])
        account_list = data.get('accountList', [])
        type = data.get('type')
        title = data.get('title')
        tags = data.get('tags')
        category = data.get('category')
        enableTimer = data.get('enableTimer')
        if category == 0:
            category = None

        videos_per_day = data.get('videosPerDay')
        daily_times = data.get('dailyTimes')
        start_days = data.get('startDays')
        # 打印获取到的数据（仅作为示例）
        print("File List:", file_list)
        print("Account List:", account_list)
        match type:
            case 1:
                return
            case 2:
                post_video_tencent(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                                   start_days)
            case 3:
                post_video_DouYin(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days)
            case 4:
                post_video_ks(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days)
    # 返回响应给客户端
    return jsonify(
        {
            "code": 200,
            "msg": None,
            "data": None
        }), 200

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
    app.run(host='127.0.0.1' ,port=5409)

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

active_queues = {}
app = Flask(__name__)

#允许所有来源跨域访问
CORS(app)

# 限制上传文件大小为160MB
app.config['MAX_CONTENT_LENGTH'] = 160 * 1024 * 1024

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

# 在 sau_backend.py 中添加以下路由和方法

# ============ 分组管理相关API ============

@app.route('/groups', methods=['GET'])
def get_all_groups():
    """获取所有分组"""
    try:
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 获取分组及其账号数量
            cursor.execute('''
                SELECT 
                    g.*,
                    COUNT(u.id) as account_count
                FROM account_groups g
                LEFT JOIN user_info u ON g.id = u.group_id
                GROUP BY g.id
                ORDER BY g.sort_order, g.name
            ''')
            
            groups = [dict(row) for row in cursor.fetchall()]
            
            return jsonify({
                "code": 200,
                "msg": "success",
                "data": groups
            }), 200
            
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": f"获取分组失败: {str(e)}",
            "data": None
        }), 500

@app.route('/groups', methods=['POST'])
def create_group():
    """创建新分组"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        color = data.get('color', '#5B73DE')
        icon = data.get('icon', 'Users')
        
        if not name:
            return jsonify({
                "code": 400,
                "msg": "分组名称不能为空",
                "data": None
            }), 400
        
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            
            # 检查分组名是否已存在
            cursor.execute("SELECT COUNT(*) FROM account_groups WHERE name = ?", (name,))
            if cursor.fetchone()[0] > 0:
                return jsonify({
                    "code": 400,
                    "msg": "分组名称已存在",
                    "data": None
                }), 400
            
            # 获取最大排序号
            cursor.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM account_groups")
            sort_order = cursor.fetchone()[0]
            
            # 插入新分组
            cursor.execute('''
                INSERT INTO account_groups (name, description, color, icon, sort_order)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, description, color, icon, sort_order))
            
            group_id = cursor.lastrowid
            conn.commit()
            
            return jsonify({
                "code": 200,
                "msg": "分组创建成功",
                "data": {"id": group_id}
            }), 200
            
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": f"创建分组失败: {str(e)}",
            "data": None
        }), 500

@app.route('/groups/<int:group_id>', methods=['PUT'])
def update_group(group_id):
    """更新分组信息"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        color = data.get('color', '#5B73DE')
        icon = data.get('icon', 'Users')
        
        if not name:
            return jsonify({
                "code": 400,
                "msg": "分组名称不能为空",
                "data": None
            }), 400
        
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            
            # 检查分组是否存在
            cursor.execute("SELECT COUNT(*) FROM account_groups WHERE id = ?", (group_id,))
            if cursor.fetchone()[0] == 0:
                return jsonify({
                    "code": 404,
                    "msg": "分组不存在",
                    "data": None
                }), 404
            
            # 检查名称是否与其他分组冲突
            cursor.execute("SELECT COUNT(*) FROM account_groups WHERE name = ? AND id != ?", (name, group_id))
            if cursor.fetchone()[0] > 0:
                return jsonify({
                    "code": 400,
                    "msg": "分组名称已存在",
                    "data": None
                }), 400
            
            # 更新分组
            cursor.execute('''
                UPDATE account_groups 
                SET name = ?, description = ?, color = ?, icon = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (name, description, color, icon, group_id))
            
            conn.commit()
            
            return jsonify({
                "code": 200,
                "msg": "分组更新成功",
                "data": None
            }), 200
            
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": f"更新分组失败: {str(e)}",
            "data": None
        }), 500

@app.route('/groups/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    """删除分组"""
    try:
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            
            # 检查分组是否存在
            cursor.execute("SELECT name FROM account_groups WHERE id = ?", (group_id,))
            group = cursor.fetchone()
            if not group:
                return jsonify({
                    "code": 404,
                    "msg": "分组不存在",
                    "data": None
                }), 404
            
            # 检查是否为默认分组
            if group[0] == '默认分组':
                return jsonify({
                    "code": 400,
                    "msg": "默认分组不能删除",
                    "data": None
                }), 400
            
            # 检查分组下是否有账号
            cursor.execute("SELECT COUNT(*) FROM user_info WHERE group_id = ?", (group_id,))
            account_count = cursor.fetchone()[0]
            
            if account_count > 0:
                # 将账号移动到默认分组
                cursor.execute('''
                    UPDATE user_info 
                    SET group_id = (SELECT id FROM account_groups WHERE name = '默认分组' LIMIT 1)
                    WHERE group_id = ?
                ''', (group_id,))
            
            # 删除分组
            cursor.execute("DELETE FROM account_groups WHERE id = ?", (group_id,))
            conn.commit()
            
            return jsonify({
                "code": 200,
                "msg": f"分组删除成功，{account_count}个账号已移至默认分组",
                "data": None
            }), 200
            
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": f"删除分组失败: {str(e)}",
            "data": None
        }), 500

@app.route('/groups/<int:group_id>/accounts', methods=['GET'])
def get_group_accounts(group_id):
    """获取分组下的账号列表"""
    try:
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT u.*, g.name as group_name, g.color as group_color
                FROM user_info u
                LEFT JOIN account_groups g ON u.group_id = g.id
                WHERE u.group_id = ?
                ORDER BY u.userName
            ''', (group_id,))
            
            accounts = [dict(row) for row in cursor.fetchall()]
            
            return jsonify({
                "code": 200,
                "msg": "success",
                "data": accounts
            }), 200
            
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": f"获取分组账号失败: {str(e)}",
            "data": None
        }), 500

@app.route('/accounts/<int:account_id>/group', methods=['PUT'])
def move_account_to_group():
    """移动账号到指定分组"""
    try:
        data = request.get_json()
        account_id = data.get('account_id')
        group_id = data.get('group_id')
        
        if not account_id or not group_id:
            return jsonify({
                "code": 400,
                "msg": "账号ID和分组ID不能为空",
                "data": None
            }), 400
        
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            
            # 验证账号和分组是否存在
            cursor.execute("SELECT COUNT(*) FROM user_info WHERE id = ?", (account_id,))
            if cursor.fetchone()[0] == 0:
                return jsonify({
                    "code": 404,
                    "msg": "账号不存在",
                    "data": None
                }), 404
            
            cursor.execute("SELECT COUNT(*) FROM account_groups WHERE id = ?", (group_id,))
            if cursor.fetchone()[0] == 0:
                return jsonify({
                    "code": 404,
                    "msg": "分组不存在",
                    "data": None
                }), 404
            
            # 更新账号分组
            cursor.execute("UPDATE user_info SET group_id = ? WHERE id = ?", (group_id, account_id))
            conn.commit()
            
            return jsonify({
                "code": 200,
                "msg": "账号分组更新成功",
                "data": None
            }), 200
            
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": f"移动账号失败: {str(e)}",
            "data": None
        }), 500

@app.route('/accounts/batch-group', methods=['PUT'])
def batch_move_accounts_to_group():
    """批量移动账号到指定分组"""
    try:
        data = request.get_json()
        account_ids = data.get('account_ids', [])
        group_id = data.get('group_id')
        
        if not account_ids or not group_id:
            return jsonify({
                "code": 400,
                "msg": "账号列表和分组ID不能为空",
                "data": None
            }), 400
        
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            
            # 验证分组是否存在
            cursor.execute("SELECT COUNT(*) FROM account_groups WHERE id = ?", (group_id,))
            if cursor.fetchone()[0] == 0:
                return jsonify({
                    "code": 404,
                    "msg": "分组不存在",
                    "data": None
                }), 404
            
            # 批量更新账号分组
            placeholders = ','.join(['?' for _ in account_ids])
            cursor.execute(
                f"UPDATE user_info SET group_id = ? WHERE id IN ({placeholders})",
                [group_id] + account_ids
            )
            
            affected_rows = cursor.rowcount
            conn.commit()
            
            return jsonify({
                "code": 200,
                "msg": f"成功移动{affected_rows}个账号到新分组",
                "data": {"affected_count": affected_rows}
            }), 200
            
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": f"批量移动账号失败: {str(e)}",
            "data": None
        }), 500

# 修改现有的 getValidAccounts 接口，返回分组信息
@app.route("/getValidAccountsWithGroups", methods=['GET'])
async def getValidAccountsWithGroups():
    """获取带分组信息的账号列表"""
    try:
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 使用视图查询账号和分组信息
            cursor.execute('''
                SELECT 
                    u.id, u.type, u.filePath, u.userName, u.status, u.group_id,
                    g.name as group_name, g.color as group_color, g.icon as group_icon
                FROM user_info u
                LEFT JOIN account_groups g ON u.group_id = g.id
                ORDER BY g.sort_order, g.name, u.userName
            ''')
            
            accounts = [dict(row) for row in cursor.fetchall()]
            
            # 验证账号状态
            for account in accounts:
                flag = await check_cookie(account['type'], account['filePath'])
                if not flag:
                    account['status'] = 0
                    cursor.execute('UPDATE user_info SET status = ? WHERE id = ?', (0, account['id']))
            
            conn.commit()
            
            return jsonify({
                "code": 200,
                "msg": "success",
                "data": accounts
            }), 200
            
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": f"获取账号列表失败: {str(e)}",
            "data": None
        }), 500
@app.route("/getValidAccounts",methods=['GET'])
async def getValidAccounts():
    with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT * FROM user_info''')
        rows = cursor.fetchall()
        rows_list = [list(row) for row in rows]
        print("\n📋 当前数据表内容：")
        for row in rows:
            print(row)
        for row in rows_list:
            flag = await check_cookie(row[1],row[2])
            if not flag:
                row[4] = 0
                cursor.execute('''
                UPDATE user_info 
                SET status = ? 
                WHERE id = ?
                ''', (0,row[0]))
                conn.commit()
                print("✅ 用户状态已更新")
        for row in rows:
            print(row)
        return jsonify(
                        {
                            "code": 200,
                            "msg": None,
                            "data": rows_list
                        }),200

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
def init_database():
    """应用启动时初始化数据库"""
    try:
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'db'))
        
        from database_manager import DatabaseManager
        manager = DatabaseManager(Path(BASE_DIR / "db" / "database.db"))
        manager.auto_manage()
        
    except Exception as e:
        print(f"数据库初始化失败: {e}")

# 在应用启动时调用
if __name__ == '__main__':
    init_database()  # 🆕 添加这行
    app.run(host='0.0.0.0' ,port=5409)

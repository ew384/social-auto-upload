import sqlite3
import json
import os

# 数据库文件路径（如果不存在会自动创建）
db_file = './database.db'

# 连接到SQLite数据库（如果文件不存在则会自动创建）
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# 创建账号记录表
cursor.execute('''
CREATE TABLE IF NOT EXISTS user_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type INTEGER NOT NULL,
    filePath TEXT NOT NULL,  -- 存储文件路径
    userName TEXT NOT NULL,
    status INTEGER DEFAULT 0,
    group_id INTEGER DEFAULT NULL,                       -- 分组ID，NULL表示未分组
    last_check_time DATETIME DEFAULT CURRENT_TIMESTAMP,  -- 最后检查时间
    check_interval INTEGER DEFAULT 3600,                 -- 检查间隔（秒），默认1小时
    FOREIGN KEY (group_id) REFERENCES account_groups(id) ON DELETE SET NULL
)
''')

# 创建文件记录表
cursor.execute('''CREATE TABLE IF NOT EXISTS file_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT, -- 唯一标识每条记录
    filename TEXT NOT NULL,               -- 文件名
    filesize REAL,                     -- 文件大小（单位：MB）
    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP, -- 上传时间，默认当前时间
    file_path TEXT                        -- 文件路径
)
''')

# 新增：创建分组表
cursor.execute('''
CREATE TABLE IF NOT EXISTS account_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    color VARCHAR(20) DEFAULT '#5B73DE',
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_time DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

# 提交更改
conn.commit()
print("✅ 表创建成功")
# 关闭连接
conn.close()
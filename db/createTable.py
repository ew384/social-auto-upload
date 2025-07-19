import sqlite3
import os
from pathlib import Path

# 数据库文件路径（如果不存在会自动创建）
db_file = './database.db'

# 连接到SQLite数据库（如果文件不存在则会自动创建）
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

print("🚀 开始创建数据库表...")

# 创建分组表
cursor.execute('''
CREATE TABLE IF NOT EXISTS account_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    color VARCHAR(20) DEFAULT '#5B73DE',
    icon VARCHAR(50) DEFAULT 'Users',
    sort_order INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
print("✅ account_groups 表创建成功")

# 创建账号记录表（包含所有新字段）
cursor.execute('''
CREATE TABLE IF NOT EXISTS user_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type INTEGER NOT NULL,
    filePath TEXT NOT NULL,
    userName TEXT NOT NULL,
    status INTEGER DEFAULT 0,
    group_id INTEGER DEFAULT NULL,
    last_check_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    check_interval INTEGER DEFAULT 3600,
    account_id TEXT,
    real_name TEXT, 
    followers_count INTEGER,
    videos_count INTEGER,
    bio TEXT,
    avatar_url TEXT,
    local_avatar TEXT,
    updated_at TEXT,
    FOREIGN KEY (group_id) REFERENCES account_groups(id) ON DELETE SET NULL
)
''')
print("✅ user_info 表创建成功（包含账号信息字段）")

# 创建文件记录表
cursor.execute('''
CREATE TABLE IF NOT EXISTS file_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    filesize REAL,
    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    file_path TEXT
)
''')
print("✅ file_records 表创建成功")

# 创建索引以提高查询性能
cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_info_type ON user_info(type)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_info_filepath ON user_info(filePath)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_info_group ON user_info(group_id)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_records_filename ON file_records(filename)')
print("✅ 数据库索引创建成功")

# 插入默认分组数据
default_groups = [
    ('微信视频号', '微信视频号账号分组', '#10B981', 'Video', 1),
    ('抖音', '抖音账号分组', '#EF4444', 'Music', 2),
    ('快手', '快手账号分组', '#F59E0B', 'Zap', 3),
    ('小红书', '小红书账号分组', '#EC4899', 'Heart', 4),
]

for group_name, description, color, icon, sort_order in default_groups:
    cursor.execute('''
        INSERT OR IGNORE INTO account_groups (name, description, color, icon, sort_order)
        VALUES (?, ?, ?, ?, ?)
    ''', (group_name, description, color, icon, sort_order))

print("✅ 默认分组数据插入成功")

# 提交更改
conn.commit()

# 显示表结构信息
print("\n📋 数据库表结构信息:")
tables = ['account_groups', 'user_info', 'file_records']

for table in tables:
    print(f"\n📊 {table} 表结构:")
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()
    for col in columns:
        print(f"   {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULL'}")

# 显示统计信息
cursor.execute("SELECT COUNT(*) FROM account_groups")
groups_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM user_info")
users_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM file_records")
files_count = cursor.fetchone()[0]

print(f"\n📈 数据库统计:")
print(f"   分组数量: {groups_count}")
print(f"   账号数量: {users_count}")
print(f"   文件数量: {files_count}")

print(f"\n🎉 数据库创建完成！")
print(f"   数据库文件: {os.path.abspath(db_file)}")
print(f"   支持功能: 账号管理、分组管理、文件管理、头像存储")

# 关闭连接
conn.close()
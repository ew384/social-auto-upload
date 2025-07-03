import sqlite3
from pathlib import Path
from datetime import datetime

# 获取当前文件所在目录，然后找到database.db
current_dir = Path(__file__).parent
db_path = current_dir / "database.db"

# 连接到现有数据库
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # 检查字段是否已存在
    cursor.execute("PRAGMA table_info(user_info)")
    columns = [column[1] for column in cursor.fetchall()]
    
    print(f"当前表字段: {columns}")
    
    # 添加字段时不使用 CURRENT_TIMESTAMP，而是使用 NULL
    if 'last_check_time' not in columns:
        cursor.execute('ALTER TABLE user_info ADD COLUMN last_check_time DATETIME')
        print("✅ 添加 last_check_time 字段成功")
    else:
        print("⚠️ last_check_time 字段已存在")
    
    if 'check_interval' not in columns:
        cursor.execute('ALTER TABLE user_info ADD COLUMN check_interval INTEGER DEFAULT 3600')
        print("✅ 添加 check_interval 字段成功")
    else:
        print("⚠️ check_interval 字段已存在")
    
    # 为所有现有记录设置默认的检查时间（当前时间）
    current_time = datetime.now().isoformat()
    cursor.execute('UPDATE user_info SET last_check_time = ? WHERE last_check_time IS NULL', (current_time,))
    updated_rows = cursor.rowcount
    
    if updated_rows > 0:
        print(f"✅ 为 {updated_rows} 条现有记录设置了默认检查时间")
    
    conn.commit()
    print("✅ 数据库迁移完成")
    
    #验证迁移结果
    cursor.execute("PRAGMA table_info(user_info)")
    new_columns = [column[1] for column in cursor.fetchall()]
    print(f"迁移后表字段: {new_columns}")
    
    # 检查数据
    cursor.execute("SELECT id, type, filePath, userName, status,group_id, last_check_time, check_interval FROM user_info LIMIT 10")
    sample_data = cursor.fetchall()
    for sample in sample_data:
        print(f"{sample}")
    
except Exception as e:
    print(f"❌ 迁移失败: {e}")
    conn.rollback()
    raise
finally:
    conn.close()

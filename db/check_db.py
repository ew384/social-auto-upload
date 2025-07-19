import sqlite3
from pathlib import Path

# 获取数据库路径
current_dir = Path(__file__).parent
db_path = current_dir / "database.db"

# 连接数据库
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # 检查 account_groups 表结构
    cursor.execute("PRAGMA table_info(account_groups)")
    columns = cursor.fetchall()
    print("account_groups 表结构:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    
    # 检查表中的数据
    cursor.execute("SELECT * FROM account_groups")
    data = cursor.fetchall()
    print(f"\naccount_groups 表数据 ({len(data)} 条):")
    for row in data:
        print(f"  {row}")
        
    # 检查 user_info 表的 group_id 字段
    cursor.execute("PRAGMA table_info(user_info)")
    user_columns = [col[1] for col in cursor.fetchall()]
    print(f"\nuser_info 表字段: {user_columns}")
    cursor.execute("UPDATE user_info SET type = 2 WHERE id = 16")

    # 提交更改
    conn.commit()

    # 验证更新结果
    cursor.execute("SELECT id, type, userName FROM user_info WHERE id = 16")
    cursor.execute("SELECT id, type, filePath, userName, status,group_id, last_check_time, check_interval FROM user_info LIMIT 10")
    sample_data = cursor.fetchall()
    for sample in sample_data:
        print(f"{sample}")
    # 检查有分组的账号
    #cursor.execute('''
    #                INSERT INTO user_info (type, filePath, userName, status)
    #                VALUES (?, ?, ?, ?)
    #                ''', (2, "2a928562-643c-11f0-8a24-a45e60e0141b.json", "endian", 1))
    #conn.commit()
    cursor.execute("SELECT id, userName, group_id FROM user_info WHERE group_id IS NOT NULL")
    grouped_accounts = cursor.fetchall()
    print(f"\n已分组账号 ({len(grouped_accounts)} 个):")
    for acc in grouped_accounts:
        print(f"  账号ID: {acc[0]}, 用户名: {acc[1]}, 分组ID: {acc[2]}")

except Exception as e:
    print(f"❌ 检查失败: {e}")
finally:
    conn.close()

import sqlite3
from pathlib import Path

# 获取数据库路径
db_path = Path("database.db")

print("开始修复数据库...")

try:
    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. 查看修复前的状态
    print("\n=== 修复前的状态 ===")
    cursor.execute("SELECT id, userName, group_id FROM user_info WHERE group_id IS NOT NULL")
    before_data = cursor.fetchall()
    print(f"有分组的账号数量: {len(before_data)}")
    for row in before_data:
        print(f"  账号ID: {row[0]}, 用户名: {row[1]}, 分组ID: {row[2]}")
    
    # 2. 执行修复：清空所有账号的分组关系
    print("\n=== 执行修复操作 ===")
    cursor.execute("UPDATE user_info SET group_id = NULL")
    affected_rows = cursor.rowcount
    print(f"已更新 {affected_rows} 个账号的分组关系")
    
    # 3. 提交更改
    conn.commit()
    print("数据库更改已提交")
    
    # 4. 验证修复结果
    print("\n=== 修复后的状态 ===")
    cursor.execute("SELECT id, userName, group_id FROM user_info WHERE group_id IS NOT NULL")
    after_data = cursor.fetchall()
    print(f"有分组的账号数量: {len(after_data)}")
    
    cursor.execute("SELECT id, userName, group_id FROM user_info")
    all_data = cursor.fetchall()
    print(f"所有账号状态:")
    for row in all_data:
        group_status = "未分组" if row[2] is None else f"分组ID: {row[2]}"
        print(f"  账号ID: {row[0]}, 用户名: {row[1]}, {group_status}")
    
    print("\n✅ 数据库修复完成！")
    print("现在所有账号都已移除分组关系，可以刷新前端页面测试了。")

except Exception as e:
    print(f"❌ 修复失败: {e}")
    if 'conn' in locals():
        conn.rollback()
        print("已回滚更改")
finally:
    if 'conn' in locals():
        conn.close()
        print("数据库连接已关闭")

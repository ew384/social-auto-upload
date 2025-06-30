# db/upgrade_database.py
import sqlite3
from pathlib import Path

def check_need_upgrade():
    """检查是否需要升级数据库"""
    db_path = Path('./database.db')
    
    if not db_path.exists():
        print("❌ 数据库文件不存在，请先运行 createTable.py")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查是否存在分组表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='account_groups'
        """)
        
        if cursor.fetchone():
            print("✅ 数据库已包含分组功能，无需升级")
            return False
        else:
            return True
            
    except Exception as e:
        print(f"检查数据库失败: {e}")
        return False
    finally:
        conn.close()

def upgrade_database():
    """升级数据库，添加分组功能相关表"""
    
    # 首先检查是否需要升级
    if not check_need_upgrade():
        return True
    
    db_path = Path('./database.db')
    
    # 备份原数据库
    backup_path = db_path.with_suffix('.db.backup')
    import shutil
    shutil.copy2(db_path, backup_path)
    print(f"📋 已备份原数据库到: {backup_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🔄 开始升级数据库...")
        # 创建分组表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS account_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,           -- 分组名称
            description TEXT,                    -- 分组描述
            color TEXT DEFAULT '#5B73DE',        -- 分组颜色
            icon TEXT DEFAULT 'Users',           -- 分组图标
            sort_order INTEGER DEFAULT 0,       -- 排序顺序
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 为用户表添加分组字段
        try:
            cursor.execute('ALTER TABLE user_info ADD COLUMN group_id INTEGER')
            print("✅ 已添加 group_id 字段到 user_info 表")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("⚠️  group_id 字段已存在")
            else:
                raise e
        
        # 创建默认分组
        cursor.execute('''
        INSERT OR IGNORE INTO account_groups (name, description, color, icon, sort_order) 
        VALUES 
            ('默认分组', '系统默认分组', '#5B73DE', 'Users', 0),
            ('工作账号', '用于工作相关内容发布的账号', '#10B981', 'Briefcase', 1),
            ('个人账号', '个人生活内容发布账号', '#F59E0B', 'User', 2)
        ''')
        
        # 将现有账号分配到默认分组
        cursor.execute('''
        UPDATE user_info 
        SET group_id = (SELECT id FROM account_groups WHERE name = '默认分组' LIMIT 1)
        WHERE group_id IS NULL
        ''')
        
        # 创建分组账号关联视图（用于查询优化）
        cursor.execute('''
        CREATE VIEW IF NOT EXISTS v_accounts_with_groups AS
        SELECT 
            u.id,
            u.type,
            u.filePath,
            u.userName,
            u.status,
            u.group_id,
            g.name as group_name,
            g.description as group_description,
            g.color as group_color,
            g.icon as group_icon
        FROM user_info u
        LEFT JOIN account_groups g ON u.group_id = g.id
        ''')
        
        conn.commit()
        print("✅ 数据库升级成功")
        
        # 验证数据
        cursor.execute("SELECT COUNT(*) FROM account_groups")
        group_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_info WHERE group_id IS NOT NULL")
        account_with_group_count = cursor.fetchone()[0]
        
        print(f"📊 分组数量: {group_count}")
        print(f"📊 已分组账号数量: {account_with_group_count}")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 数据库升级失败: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    upgrade_database()
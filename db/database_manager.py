# db/database_manager.py - 数据库管理统一入口
import sqlite3
import sys
import os
from pathlib import Path
import shutil
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path='./database.db'):
        self.db_path = Path(db_path)
        self.backup_dir = Path('./backups')
        self.backup_dir.mkdir(exist_ok=True)
    
    def get_database_version(self):
        """获取数据库版本"""
        if not self.db_path.exists():
            return "none"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查是否存在分组表
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='account_groups'
            """)
            
            if cursor.fetchone():
                # 检查是否有group_id字段
                cursor.execute("PRAGMA table_info(user_info)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'group_id' in columns:
                    return "v2.0"  # 包含分组功能的版本
                else:
                    return "v1.5"  # 部分升级
            else:
                return "v1.0"  # 原始版本
                
        except Exception as e:
            print(f"检查数据库版本失败: {e}")
            return "unknown"
        finally:
            conn.close()
    
    def backup_database(self):
        """备份数据库"""
        if not self.db_path.exists():
            print("❌ 数据库文件不存在，无需备份")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"database_backup_{timestamp}.db"
        
        try:
            shutil.copy2(self.db_path, backup_path)
            print(f"📋 数据库已备份到: {backup_path}")
            return backup_path
        except Exception as e:
            print(f"❌ 备份失败: {e}")
            return None
    
    def create_fresh_database(self):
        """创建全新的数据库（包含所有功能）"""
        print("🆕 创建全新数据库...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 创建分组表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS account_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                color TEXT DEFAULT '#5B73DE',
                icon TEXT DEFAULT 'Users',
                sort_order INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # 创建用户表（包含分组字段）
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type INTEGER NOT NULL,
                filePath TEXT NOT NULL,
                userName TEXT NOT NULL,
                status INTEGER DEFAULT 0,
                group_id INTEGER,
                FOREIGN KEY (group_id) REFERENCES account_groups (id)
            )
            ''')
            
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
            
            # 插入默认分组
            cursor.execute('''
            INSERT OR IGNORE INTO account_groups (name, description, color, icon, sort_order) 
            VALUES 
                ('默认分组', '系统默认分组', '#5B73DE', 'Users', 0),
                ('工作账号', '用于工作相关内容发布的账号', '#10B981', 'Briefcase', 1),
                ('个人账号', '个人生活内容发布账号', '#F59E0B', 'User', 2)
            ''')
            
            # 创建视图
            cursor.execute('''
            CREATE VIEW IF NOT EXISTS v_accounts_with_groups AS
            SELECT 
                u.id, u.type, u.filePath, u.userName, u.status, u.group_id,
                g.name as group_name, g.description as group_description,
                g.color as group_color, g.icon as group_icon
            FROM user_info u
            LEFT JOIN account_groups g ON u.group_id = g.id
            ''')
            
            conn.commit()
            print("✅ 全新数据库创建成功")
            
        except Exception as e:
            conn.rollback()
            print(f"❌ 创建数据库失败: {e}")
            raise e
        finally:
            conn.close()
    
    def upgrade_to_v2(self):
        """升级到v2.0版本（添加分组功能）"""
        print("🔄 升级数据库到v2.0版本...")
        
        # 先备份
        self.backup_database()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 创建分组表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS account_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                color TEXT DEFAULT '#5B73DE',
                icon TEXT DEFAULT 'Users',
                sort_order INTEGER DEFAULT 0,
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
            
            # 创建视图
            cursor.execute('''
            CREATE VIEW IF NOT EXISTS v_accounts_with_groups AS
            SELECT 
                u.id, u.type, u.filePath, u.userName, u.status, u.group_id,
                g.name as group_name, g.description as group_description,
                g.color as group_color, g.icon as group_icon
            FROM user_info u
            LEFT JOIN account_groups g ON u.group_id = g.id
            ''')
            
            conn.commit()
            print("✅ 数据库升级到v2.0成功")
            
            # 验证升级结果
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
    
    def auto_manage(self):
        """自动管理数据库（智能判断需要执行的操作）"""
        version = self.get_database_version()
        print(f"🔍 当前数据库版本: {version}")
        
        if version == "none":
            print("📝 未发现数据库，创建全新数据库...")
            self.create_fresh_database()
            
        elif version == "v1.0":
            print("📝 发现v1.0版本，升级到v2.0...")
            self.upgrade_to_v2()
            
        elif version == "v1.5":
            print("📝 发现v1.5版本，完成升级到v2.0...")
            self.upgrade_to_v2()
            
        elif version == "v2.0":
            print("✅ 数据库已是最新版本v2.0")
            
        else:
            print("⚠️  数据库版本未知，请手动处理")
    
    def show_status(self):
        """显示数据库状态"""
        version = self.get_database_version()
        print(f"\n📊 数据库状态报告")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"📍 数据库路径: {self.db_path.absolute()}")
        print(f"📋 当前版本: {version}")
        print(f"📁 文件大小: {self.db_path.stat().st_size / 1024:.1f} KB" if self.db_path.exists() else "文件不存在")
        
        if version in ["v1.5", "v2.0"]:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                # 统计信息
                cursor.execute("SELECT COUNT(*) FROM account_groups")
                group_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM user_info")
                account_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM file_records")
                file_count = cursor.fetchone()[0]
                
                print(f"👥 分组数量: {group_count}")
                print(f"📱 账号数量: {account_count}")
                print(f"📄 文件数量: {file_count}")
                
            except Exception as e:
                print(f"❌ 获取统计信息失败: {e}")
            finally:
                conn.close()

def main():
    if len(sys.argv) < 2:
        print("""
🗄️  数据库管理工具
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

使用方法:
  python database_manager.py <command>

可用命令:
  auto     - 自动管理（推荐）
  create   - 创建全新数据库  
  upgrade  - 升级现有数据库
  status   - 显示数据库状态
  backup   - 备份数据库

示例:
  python database_manager.py auto
  python database_manager.py status
        """)
        return
    
    command = sys.argv[1].lower()
    manager = DatabaseManager()
    
    try:
        if command == "auto":
            manager.auto_manage()
        elif command == "create":
            manager.create_fresh_database()
        elif command == "upgrade":
            manager.upgrade_to_v2()
        elif command == "status":
            manager.show_status()
        elif command == "backup":
            manager.backup_database()
        else:
            print(f"❌ 未知命令: {command}")
            
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
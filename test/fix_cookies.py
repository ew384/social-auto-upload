import json
import os
import glob

def fix_existing_cookies():
    """修复现有的 Cookie 文件"""
    cookie_files = glob.glob("./cookiesFile/*.json")
    
    print(f"🔍 找到 {len(cookie_files)} 个 Cookie 文件需要检查")
    
    for cookie_file in cookie_files:
        try:
            with open(cookie_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'cookies' not in data:
                continue
                
            modified = False
            for cookie in data['cookies']:
                if 'sameSite' in cookie:
                    original = cookie['sameSite']
                    
                    # 修复不兼容的值
                    if original in ['unspecified', 'no_restriction', '', None]:
                        cookie['sameSite'] = 'Lax'
                        modified = True
                    elif original not in ['Strict', 'Lax', 'None']:
                        cookie['sameSite'] = 'Lax'
                        modified = True
            
            if modified:
                with open(cookie_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"🔧 已修复: {os.path.basename(cookie_file)}")
            else:
                print(f"✅ 无需修复: {os.path.basename(cookie_file)}")
                
        except Exception as e:
            print(f"❌ 处理 {cookie_file} 时出错: {e}")

if __name__ == "__main__":
    fix_existing_cookies()
    print("🎉 Cookie 修复完成！")
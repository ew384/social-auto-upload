#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试微信视频号用户信息提取功能
"""

import asyncio
import sys
from pathlib import Path

current_dir = Path(__file__).parent
project_root = current_dir.parent  # 上一级目录
sys.path.insert(0, str(project_root))

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.browser_adapter import MultiAccountBrowserAdapter

async def test_wechat_account_info():
    """测试微信视频号用户信息提取"""
    
    # 初始化适配器
    adapter = MultiAccountBrowserAdapter(api_base_url="http://localhost:3000/api")
    
    # 测试参数 - 使用你的微信cookie文件
    cookie_file = "/Users/endian/Desktop/social-auto-upload/cookiesFile/545c6c00-64a5-11f0-bbf2-a45e60e0141b.json"
    platform = "wechat"
    initial_url = "https://channels.weixin.qq.com"
    
    print("🧪 测试微信视频号用户信息提取")
    print("=" * 60)
    print(f"Cookie文件: {Path(cookie_file).name}")
    print(f"平台: {platform}")
    print(f"初始URL: {initial_url}")
    print("-" * 60)
    
    try:
        # 1. 获取或创建标签页（应该复用现有的）
        print("📋 获取微信视频号标签页...")
        tab_id = await adapter.get_or_create_tab(
            cookie_file=cookie_file,
            platform=platform,
            initial_url=initial_url,
            tab_name_prefix="视频号_"
        )
        print(f"✅ 标签页ID: {tab_id}")
        
        # 2. 等待页面完全加载
        print("\n⏳ 等待页面加载...")
        await asyncio.sleep(3)
        
        # 3. 检查当前页面状态
        print("\n📍 检查页面状态...")
        try:
            current_url = await adapter.get_page_url(tab_id)
            print(f"当前URL: {current_url}")
            
            # 获取页面标题
            page_title = await adapter.execute_script(tab_id, "document.title")
            print(f"页面标题: {page_title}")
            
        except Exception as e:
            print(f"⚠️ 获取页面信息失败: {e}")
        
        # 4. 测试账号信息提取
        print("\n🔍 开始提取用户账号信息...")
        print("=" * 40)
        
        # 使用项目根目录作为 base_dir
        base_dir = str(project_root)
        account_info = adapter.get_account_info_with_avatar(tab_id, platform, base_dir)
        print(account_info)
        if account_info:
            print("✅ 账号信息提取成功！")
            print("-" * 40)
            print(f"📝 账号名称: {account_info.get('accountName', 'N/A')}")
            print(f"🆔 账号ID: {account_info.get('accountId', 'N/A')}")
            print(f"👥 粉丝数量: {account_info.get('followersCount', 'N/A')}")
            print(f"📹 视频数量: {account_info.get('videosCount', 'N/A')}")
            print(f"📝 个人简介: {account_info.get('bio', 'N/A')}")
            print(f"🌐 头像URL: {account_info.get('avatar', 'N/A')}")
            print(f"💾 本地头像: {account_info.get('localAvatar', 'N/A')}")
            
            # 5. 验证头像下载
            if account_info.get('localAvatar'):
                avatar_path = Path(base_dir) / account_info['localAvatar']
                if avatar_path.exists():
                    print(f"✅ 头像文件已下载: {avatar_path}")
                    print(f"📏 文件大小: {avatar_path.stat().st_size} bytes")
                else:
                    print(f"❌ 头像文件不存在: {avatar_path}")
            
        else:
            print("❌ 账号信息提取失败")
            
        # 6. 调试：手动检查页面元素
        print("\n🔧 调试：检查页面元素...")
        try:
            debug_script = """
            (function() {
                const info = {
                    url: window.location.href,
                    title: document.title,
                    hasUserElements: {
                        avatar: !!document.querySelector('.avatar, .user-avatar, .profile-avatar, img[alt*="头像"], img[src*="avatar"]'),
                        username: !!document.querySelector('.username, .user-name, .nickname, .account-name'),
                        followers: !!document.querySelector('[class*="follow"], [class*="fan"], .follower-count'),
                        profileInfo: !!document.querySelector('.profile, .user-info, .account-info')
                    },
                    foundElements: {
                        images: Array.from(document.querySelectorAll('img')).slice(0, 5).map(img => ({
                            src: img.src,
                            alt: img.alt,
                            className: img.className
                        })),
                        textElements: Array.from(document.querySelectorAll('.username, .user-name, .nickname, .account-name')).map(el => el.textContent)
                    }
                };
                return info;
            })()
            """
            
            debug_result = await adapter.execute_script(tab_id, debug_script)
            print("🔍 页面元素检查结果:")
            print(f"   URL: {debug_result.get('url')}")
            print(f"   标题: {debug_result.get('title')}")
            print(f"   找到头像元素: {debug_result.get('hasUserElements', {}).get('avatar', False)}")
            print(f"   找到用户名元素: {debug_result.get('hasUserElements', {}).get('username', False)}")
            print(f"   找到粉丝元素: {debug_result.get('hasUserElements', {}).get('followers', False)}")
            print(f"   找到资料元素: {debug_result.get('hasUserElements', {}).get('profileInfo', False)}")
            
            # 显示找到的图片
            images = debug_result.get('foundElements', {}).get('images', [])
            if images:
                print(f"   找到 {len(images)} 个图片:")
                for i, img in enumerate(images):
                    print(f"     {i+1}. {img.get('src', '')[:60]}... (alt: {img.get('alt', 'N/A')})")
            
            # 显示找到的文本
            texts = debug_result.get('foundElements', {}).get('textElements', [])
            if texts:
                print(f"   找到文本元素: {texts}")
                
        except Exception as e:
            print(f"❌ 调试脚本执行失败: {e}")
        
        # 7. 建议下一步操作
        print("\n💡 建议:")
        if not account_info:
            print("   1. 检查是否已正确登录微信视频号")
            print("   2. 尝试导航到个人资料页面")
            print("   3. 检查页面是否完全加载")
            print("   4. 确认平台选择器配置是否正确")
            
        print("\n" + "="*60)
        print("🎯 测试完成！")
        
        # 可选：保持标签页打开用于进一步调试
        keep_open = input("\n是否保持标签页打开以便调试? (y/N): ").strip().lower()
        if keep_open != 'y':
            await adapter.close_tab(tab_id)
            print("🗑️ 标签页已关闭")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """主测试函数"""
    # 先测试连接
    adapter = MultiAccountBrowserAdapter()
    try:
        tabs = await adapter.get_all_tabs()
        print(f"✅ 连接成功！当前标签页数量: {len(tabs.get('data', []))}")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        print("💡 请确保 multi-account-browser 正在运行")
        return
    
    # 运行用户信息提取测试
    await test_wechat_account_info()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
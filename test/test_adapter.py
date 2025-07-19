#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 MultiAccountBrowserAdapter.get_or_create_tab 方法
"""
import asyncio
import sys
from pathlib import Path

current_dir = Path(__file__).parent
project_root = current_dir.parent  # 上一级目录
sys.path.insert(0, str(project_root))

print(f"当前目录: {current_dir}")
print(f"项目根目录: {project_root}")
print(f"utils目录是否存在: {(project_root / 'utils').exists()}")
from conf import BASE_DIR

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.browser_adapter import MultiAccountBrowserAdapter

async def test_get_or_create_tab():
    """测试获取或创建标签页功能"""
    
    # 初始化适配器
    adapter = MultiAccountBrowserAdapter(api_base_url="http://localhost:3000/api")
    
    # 测试参数
    
    cookie_file = Path(BASE_DIR / "cookiesFile" / "2a928562-643c-11f0-8a24-a45e60e0141b.json")
    platform = "wechat"
    initial_url = "https://channels.weixin.qq.com"
    
    print("🚀 开始测试 get_or_create_tab...")
    print(f"Cookie文件: {cookie_file}")
    print(f"平台: {platform}")
    print(f"初始URL: {initial_url}")
    print("-" * 50)
    
    try:
        # 1. 第一次调用 - 应该创建新标签页
        print("📋 第一次调用 get_or_create_tab...")
        tab_id_1 = await adapter.get_or_create_tab(
            cookie_file=cookie_file,
            platform=platform,
            initial_url=initial_url,
            tab_name_prefix="视频号_"
        )
        print(f"✅ 第一次调用成功，标签页ID: {tab_id_1}")
        
        # 2. 获取当前所有标签页状态
        print("\n📊 查看当前所有标签页...")
        all_tabs = await adapter.get_all_tabs()
        print(f"当前标签页数量: {len(all_tabs.get('data', []))}")
        for tab in all_tabs.get('data', []):
            print(f"  - ID: {tab.get('id')}, Name: {tab.get('accountName')}, Cookie: {tab.get('cookieFile')}")
        
        # 3. 第二次调用 - 应该复用现有标签页
        print("\n🔄 第二次调用 get_or_create_tab (应该复用)...")
        tab_id_2 = await adapter.get_or_create_tab(
            cookie_file=cookie_file,
            platform=platform,
            initial_url=initial_url,
            tab_name_prefix="视频号_"
        )
        print(f"✅ 第二次调用成功，标签页ID: {tab_id_2}")
        
        # 4. 验证是否为同一个标签页
        if tab_id_1 == tab_id_2:
            print("🎉 测试成功！第二次调用复用了现有标签页")
        else:
            print("⚠️ 警告：两次调用返回了不同的标签页ID")
        
        
        # 6. 获取页面URL确认
        try:
            current_url = await adapter.get_page_url(tab_id_1)
            print(f"📍 当前页面URL: {current_url}")
        except Exception as e:
            print(f"⚠️ 获取页面URL失败: {e}")
        
        print("\n" + "="*50)
        print("🎯 测试完成！")
        print(f"最终标签页ID: {tab_id_1}")
        
        # 可选：清理测试
        cleanup = input("\n是否关闭测试标签页? (y/N): ").strip().lower()
        if cleanup == 'y':
            await adapter.close_tab(tab_id_1)
            print("🗑️ 测试标签页已关闭")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

async def test_adapter_connection():
    """测试适配器连接"""
    print("🔌 测试 multi-account-browser 连接...")
    
    adapter = MultiAccountBrowserAdapter()
    
    try:
        # 简单的连接测试
        tabs = await adapter.get_all_tabs()
        print(f"✅ 连接成功！当前标签页数量: {len(tabs.get('data', []))}")
        return True
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        print("💡 请确保:")
        print("   1. multi-account-browser 正在运行")
        print("   2. 服务运行在 http://localhost:3000")
        print("   3. API端点正常工作")
        return False

async def main():
    """主测试函数"""
    print("🧪 MultiAccountBrowserAdapter 测试工具")
    print("=" * 50)
    
    # 1. 先测试连接
    if not await test_adapter_connection():
        return
    
    print("\n" + "="*50)
    
    # 2. 测试主要功能
    await test_get_or_create_tab()

if __name__ == "__main__":
    # 运行测试
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
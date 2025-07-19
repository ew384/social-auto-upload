import asyncio
from pathlib import Path
from queue import Queue
from utils.browser_adapter import MultiAccountBrowserAdapter
from utils.common import process_login_success
from conf import BASE_DIR

async def douyin_cookie_gen(id, status_queue):
    """抖音登录"""
    adapter = MultiAccountBrowserAdapter()
    tab_id = None
    
    try:
        tab_id = await adapter.create_account_tab(f"douyin_login_{id}", "douyin", "https://channels.weixin.qq.com/login.html")
        
        qr_url = await adapter.get_qr_code(tab_id, 'img[name="二维码"]')
        if not qr_url:
            status_queue.put("500")
            return
        
        status_queue.put(qr_url)
        
        if not await adapter.wait_for_url_change(tab_id):
            status_queue.put("500")
            return
        
        # 🔥 登录成功，统一处理
        await process_login_success(adapter, tab_id, id, 3, "douyin", status_queue, sleep_time=2)
        
    except Exception as e:
        print(f"❌ 抖音登录失败: {e}")
        status_queue.put("500")
    finally:
        if tab_id:
            try:
                await adapter.close_tab(tab_id)
            except:
                pass

async def get_tencent_cookie(id, status_queue):
    """视频号登录"""
    adapter = MultiAccountBrowserAdapter()
    tab_id = None
    
    try:
        tab_id = await adapter.create_account_tab(f"wechat_login_{id}", "wechat", "https://channels.weixin.qq.com")
        
        qr_url = await adapter.get_qr_code(tab_id, 'iframe img')
        if not qr_url:
            status_queue.put("500")
            return
        
        status_queue.put(qr_url)
        
        if not await adapter.wait_for_url_change(tab_id):
            status_queue.put("500")
            return
        
        # 🔥 登录成功，统一处理
        await process_login_success(adapter, tab_id, id, 2, "wechat", status_queue, sleep_time=3)
        
    except Exception as e:
        print(f"❌ 视频号登录失败: {e}")
        status_queue.put("500")
    finally:
        if tab_id:
            try:
                await adapter.close_tab(tab_id)
            except:
                pass

async def get_ks_cookie(id, status_queue):
    """快手登录"""
    adapter = MultiAccountBrowserAdapter()
    tab_id = None
    
    try:
        tab_id = await adapter.create_account_tab(f"kuaishou_login_{id}", "kuaishou", "https://cp.kuaishou.com")
        
        await adapter.execute_script(tab_id, 'document.querySelector("a[href*=\\"login\\"]").click();')
        await asyncio.sleep(1)
        await adapter.execute_script(tab_id, 'document.querySelector("[text*=\\"扫码登录\\"]").click();')
        
        qr_url = await adapter.get_qr_code(tab_id, 'img[name="qrcode"]')
        if not qr_url:
            status_queue.put("500")
            return
        
        status_queue.put(qr_url)
        
        if not await adapter.wait_for_url_change(tab_id):
            status_queue.put("500")
            return
        
        # 🔥 登录成功，统一处理
        await process_login_success(adapter, tab_id, id, 4, "kuaishou", status_queue, sleep_time=2)
        
    except Exception as e:
        print(f"❌ 快手登录失败: {e}")
        status_queue.put("500")
    finally:
        if tab_id:
            try:
                await adapter.close_tab(tab_id)
            except:
                pass

async def xiaohongshu_cookie_gen(id, status_queue):
    """小红书登录"""
    adapter = MultiAccountBrowserAdapter()
    tab_id = None
    
    try:
        tab_id = await adapter.create_account_tab(f"xiaohongshu_login_{id}", "xiaohongshu", "https://creator.xiaohongshu.com/")
        
        await adapter.execute_script(tab_id, 'document.querySelector("img.css-wemwzq").click();')
        
        qr_url = await adapter.get_qr_code(tab_id, 'img:nth-of-type(2)')
        if not qr_url:
            status_queue.put("500")
            return
        
        status_queue.put(qr_url)
        
        if not await adapter.wait_for_url_change(tab_id):
            status_queue.put("500")
            return
        
        # 🔥 登录成功，统一处理
        await process_login_success(adapter, tab_id, id, 1, "xiaohongshu", status_queue, sleep_time=2)
        
    except Exception as e:
        print(f"❌ 小红书登录失败: {e}")
        status_queue.put("500")
    finally:
        if tab_id:
            try:
                await adapter.close_tab(tab_id)
            except:
                pass
#!/usr/bin/env python3
"""
后端启动测试脚本
"""

import os
import sys
import time
import subprocess
import socket

def test_port(port):
    """测试端口是否可用"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('localhost', port))
        sock.close()
        return True
    except:
        return False

def main():
    print("🔍 后端启动诊断...")
    
    # 检查 Python 版本
    print(f"Python 版本: {sys.version}")
    
    # 检查当前目录
    print(f"当前目录: {os.getcwd()}")
    
    # 检查关键文件
    files_to_check = [
        'sau_backend.py',
        'conf.py',
        'utils',
        'myUtils',
        'uploader'
    ]
    
    for file in files_to_check:
        if os.path.exists(file):
            print(f"✅ {file} 存在")
        else:
            print(f"❌ {file} 不存在")
    
    # 检查端口
    if test_port(5409):
        print("✅ 端口 5409 可用")
    else:
        print("❌ 端口 5409 被占用")
    
    # 尝试导入关键模块
    try:
        import flask
        print(f"✅ Flask 版本: {flask.__version__}")
    except ImportError as e:
        print(f"❌ Flask 导入失败: {e}")
    
    try:
        import conf
        print("✅ 配置文件导入成功")
    except ImportError as e:
        print(f"❌ 配置文件导入失败: {e}")
    
    # 如果存在 sau_backend，尝试启动
    if os.path.exists('sau_backend.py'):
        print("🚀 尝试启动后端服务...")
        try:
            # 使用 subprocess 启动后端
            process = subprocess.Popen([sys.executable, 'sau_backend.py'], 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE,
                                     text=True)
            
            # 等待几秒
            time.sleep(3)
            
            # 检查进程状态
            if process.poll() is None:
                print("✅ 后端服务启动成功")
                
                # 检查端口是否被监听
                if not test_port(5409):
                    print("✅ 端口 5409 已被监听")
                else:
                    print("❌ 端口 5409 仍然可用，服务可能未正常启动")
                
                # 结束进程
                process.terminate()
                process.wait()
                
            else:
                print("❌ 后端服务启动失败")
                stdout, stderr = process.communicate()
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")
                
        except Exception as e:
            print(f"❌ 启动后端时发生异常: {e}")
    
    print("🔍 诊断完成")

if __name__ == "__main__":
    main()

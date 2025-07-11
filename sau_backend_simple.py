#!/usr/bin/env python3
"""
简化的后端服务 - 用于测试
"""

import os
import sys
import time
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'message': 'SAU Backend is running',
        'version': '1.0.0'
    })

@app.route('/getAccountsWithGroups', methods=['GET'])
def get_accounts_with_groups():
    return jsonify({
        'code': 200,
        'data': [],
        'message': 'Test data'
    })

@app.route('/getValidAccounts', methods=['GET'])
def get_valid_accounts():
    return jsonify({
        'code': 200,
        'data': [],
        'message': 'Test data'
    })

@app.route('/')
def index():
    return jsonify({
        'name': 'SAU Backend',
        'status': 'running',
        'endpoints': [
            '/api/health',
            '/getAccountsWithGroups',
            '/getValidAccounts'
        ]
    })

if __name__ == '__main__':
    print("🚀 启动 SAU 后端服务...")
    print(f"Python 版本: {sys.version}")
    print(f"工作目录: {os.getcwd()}")
    
    try:
        app.run(host='0.0.0.0', port=5409, debug=False)
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

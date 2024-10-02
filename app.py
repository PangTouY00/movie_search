from flask import Flask, request, jsonify, render_template, Response
import requests
import re
import json
import time
import sqlite3
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# API接口地址
API_URL = "https://www.hhlqilongzhu.cn/api/duanju_cat.php"

# 指定无代理
proxies = {
    'http': '',
    'https': '',
}

# 数据库连接
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'config', 'history.db')

def init_db():
    """初始化数据库"""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                update_day TEXT
            )
        ''')
        # 检查是否存在 update_day 列，如果不存在则添加
        cursor.execute("PRAGMA table_info(search_history)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'update_day' not in columns:
            cursor.execute('ALTER TABLE search_history ADD COLUMN update_day TEXT')
        conn.commit()

def add_or_update_history(query, update_day=None):
    """将查询添加或更新到历史记录"""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM search_history WHERE query = ?', (query,))
        existing_record = cursor.fetchone()
        if existing_record:
            return  # 如果已经存在，直接返回，不进行后续操作
        else:
            cursor.execute('INSERT INTO search_history (query, update_day) VALUES (?, ?)', (query, update_day))
        conn.commit()

def get_history():
    """获取历史记录"""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT query, timestamp, update_day FROM search_history ORDER BY timestamp DESC')
        return cursor.fetchall()

def delete_history(query):
    """删除历史记录"""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM search_history WHERE query = ?', (query,))
        conn.commit()

def check_quark_share(share_id):
    logger = {
        'info': print,
        'debug': print
    }
    
    logger['info'](f"Quark check id {share_id}")
    
    # 发送POST请求获取token
    post_data = json.dumps({
        "pwd_id": share_id,
        "passcode": ""
    })
    headers = {'Content-Type': 'application/json'}
    response = requests.post("https://drive.quark.cn/1/clouddrive/share/sharepage/token?pr=ucpro&fr=pc", data=post_data, headers=headers)
    
    logger['debug'](f"Quark token response: {response.text}")
    
    if response.status_code != 200:
        return 0  # 请求失败
    
    rsp = response.json()
    state = 0
    
    if "需要提取码" in rsp.get('message', ''):
        state = 2
    elif "ok" in rsp.get('message', ''):
        token = rsp.get('data', {}).get('stoken', '')
        token = token.replace('+', '%2B').replace('"', '%22').replace('\'', '%27').replace('/', '%2F')
        
        # 发送GET请求获取分享详情
        detail_url = f"https://drive-h.quark.cn/1/clouddrive/share/sharepage/detail?pwd_id={share_id}&stoken={token}&_fetch_share=1"
        response = requests.get(detail_url)
        
        logger['debug'](f"checkQuark detail response: {response.text}")
        
        if response.status_code != 200:
            return 0  # 请求失败
        
        rsp2 = response.json()
        if rsp2.get('data', {}).get('share', {}).get('status') == 1:
            state = 1 if not rsp2['data']['share']['partial_violation'] else 11
        elif rsp2.get('data', {}).get('share', {}).get('status') > 1:
            state = -1
    else:
        state = -1
    
    if "ok" not in rsp.get('message', ''):
        return state
    
    return state

def check_url_validity(url):
    """
    检查URL是否有效
    :param url: 资源URL
    :return: 如果URL有效返回True，否则返回False
    """
    reg = r'(?:https?:\/\/)?\bpan\.quark\.cn\/s\/([\w\-]{8,})(?!\.)'
    match = re.search(reg, url)
    if match:
        share_id = match.group(1)
        state = check_quark_share(share_id)
        return state == 1
    return False

def query_anime(msg):
    """
    查询动漫信息
    :param msg: 动漫名字
    :return: 动漫信息的JSON数据，如果请求失败返回None
    """
    params = {
        "name": msg,
    }
    response = requests.get(API_URL, params=params, proxies=proxies)
    if response.status_code != 200:
        return None
    data = response.json()
    return data

import datetime

def stream_results(name, results_div_id):
    data = query_anime(name)
    if data is None:
        return jsonify({"error": "Failed to fetch data from API"}), 500

    results = data.get('data', [])
    valid_results = []

    for item in results:
        if check_url_validity(item['url']):
            valid_results.append(item)
            
            # 提取 share_id
            reg = r'(?:https?:\/\/)?\bpan\.quark\.cn\/s\/([\w\-]{8,})(?!\.)'
            match = re.search(reg, item['url'])
            if match:
                share_id = match.group(1)
                
                # 发送POST请求获取token
                post_data = json.dumps({
                    "pwd_id": share_id,
                    "passcode": ""
                })
                headers = {'Content-Type': 'application/json'}
                response = requests.post("https://drive.quark.cn/1/clouddrive/share/sharepage/token?pr=ucpro&fr=pc", data=post_data, headers=headers)
                
                if response.status_code != 200:
                    updated_time = "Unknown"
                else:
                    rsp = response.json()
                    if "ok" in rsp.get('message', ''):
                        token = rsp.get('data', {}).get('stoken', '')
                        token = token.replace('+', '%2B').replace('"', '%22').replace('\'', '%27').replace('/', '%2F')
                        
                        # 发送GET请求获取分享详情
                        detail_url = f"https://drive-h.quark.cn/1/clouddrive/share/sharepage/detail?pwd_id={share_id}&stoken={token}&_fetch_share=1"
                        response = requests.get(detail_url)
                        
                        if response.status_code != 200:
                            updated_time = "Unknown"
                        else:
                            rsp2 = response.json()
                            updated_at = rsp2.get('data', {}).get('share', {}).get('created_at', 0)
                            if updated_at:
                                updated_time = datetime.datetime.fromtimestamp(updated_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
                            else:
                                updated_time = "Unknown"
                    else:
                        updated_time = "Unknown"
            else:
                updated_time = "Unknown"
            
            # 将更新时间作为后缀添加到搜索结果中
            result_html = f'<div class="result"><a href="{item["url"]}" target="_blank">{item["title"]}</a> (更新时间: {updated_time})</div>'
            yield f"data: {result_html}\n\n"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search():
    name = request.args.get('name', '').strip()  # 去除多余的空格
    update_day = request.args.get('update_day', None)
    if not name:
        return jsonify({"error": "Name parameter is required"}), 400

    add_or_update_history(name, update_day)  # 将查询添加或更新到历史记录
    return Response(stream_results(name, 'results'), content_type='text/event-stream')

@app.route('/history', methods=['GET'])
def history():
    history_list = get_history()
    return jsonify(history_list)

@app.route('/update_history', methods=['POST'])
def update_history():
    data = request.json
    query = data.get('query', '')
    update_day = data.get('update_day', None)

    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    add_or_update_history(query, update_day)  # 更新历史记录中的 update_day
    return jsonify({"success": True})

@app.route('/delete_history', methods=['POST'])
def delete_history_route():
    query = request.json.get('query', '')
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    delete_history(query)
    return jsonify({"success": True})

if __name__ == '__main__':
    init_db()  # 初始化数据库
    app.run(debug=True, host='0.0.0.0', port=5000)

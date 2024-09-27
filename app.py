from flask import Flask, request, jsonify, render_template, Response
import requests
import re
import json
import time
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)

# API接口地址
API_URL = "https://www.hhlqilongzhu.cn/api/duanju_cat.php"

# 数据库连接
DATABASE = 'history.db'

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
            cursor.execute('UPDATE search_history SET timestamp = CURRENT_TIMESTAMP, update_day = ? WHERE id = ?', (update_day, existing_record[0]))
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
    response = requests.get(API_URL, params=params)
    if response.status_code != 200:
        return None
    data = response.json()
    return data

def stream_results(name, results_div_id):
    data = query_anime(name)
    if data is None:
        return jsonify({"error": "Failed to fetch data from API"}), 500

    results = data.get('data', [])
    valid_results = []

    for item in results:
        if check_url_validity(item['url']):
            valid_results.append(item)
            result_html = f'<div class="result"><a href="{item["url"]}" target="_blank">{item["title"]}</a></div>'
            yield f"data: {result_html}\n\n"
            time.sleep(0.1)  # 模拟延迟，实际使用中可以去掉

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search():
    name = request.args.get('name', '')
    update_day = request.args.get('update_day', None)
    if not name:
        return jsonify({"error": "Name parameter is required"}), 400

    add_or_update_history(name, update_day)  # 将查询添加或更新到历史记录
    return Response(stream_results(name, 'results'), content_type='text/event-stream')

@app.route('/history', methods=['GET'])
def history():
    history_list = get_history()
    return jsonify(history_list)

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

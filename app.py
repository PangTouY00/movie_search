from flask import Flask, request, jsonify, render_template
import requests
import re
import json
import asyncio
from aiohttp import ClientSession

app = Flask(__name__)

# API接口地址
API_URL = "https://www.hhlqilongzhu.cn/api/duanju_cat.php"

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

async def check_url_validity_async(url):
    """
    异步检查URL是否有效
    :param url: 资源URL
    :return: 如果URL有效返回True，否则返回False
    """
    reg = r'(?:https?:\/\/)?\bpan\.quark\.cn\/s\/([\w\-]{8,})(?!\.)'
    match = re.search(reg, url)
    if match:
        share_id = match.group(1)
        state = await check_quark_share_async(share_id)
        return state == 1
    return False

async def check_quark_share_async(share_id):
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
    
    async with ClientSession() as session:
        async with session.post("https://drive.quark.cn/1/clouddrive/share/sharepage/token?pr=ucpro&fr=pc", data=post_data, headers=headers) as response:
            if response.status != 200:
                return 0  # 请求失败
            
            rsp = await response.json()
            state = 0
            
            if "需要提取码" in rsp.get('message', ''):
                state = 2
            elif "ok" in rsp.get('message', ''):
                token = rsp.get('data', {}).get('stoken', '')
                token = token.replace('+', '%2B').replace('"', '%22').replace('\'', '%27').replace('/', '%2F')
                
                detail_url = f"https://drive-h.quark.cn/1/clouddrive/share/sharepage/detail?pwd_id={share_id}&stoken={token}&_fetch_share=1"
                
                async with session.get(detail_url) as response:
                    if response.status != 200:
                        return 0  # 请求失败
                    
                    rsp2 = await response.json()
                    if rsp2.get('data', {}).get('share', {}).get('status') == 1:
                        state = 1 if not rsp2['data']['share']['partial_violation'] else 11
                    elif rsp2.get('data', {}).get('share', {}).get('status') > 1:
                        state = -1
            else:
                state = -1
            
            if "ok" not in rsp.get('message', ''):
                return state
            
            return state

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search():
    name = request.args.get('name', '')
    if not name:
        return jsonify({"error": "Name parameter is required"}), 400

    data = query_anime(name)
    if data is None:
        return jsonify({"error": "Failed to fetch data from API"}), 500

    results = data.get('data', [])
    valid_results = []

    async def check_results(results):
        tasks = [check_url_validity_async(item['url']) for item in results]
        results_validity = await asyncio.gather(*tasks)
        for item, is_valid in zip(results, results_validity):
            if is_valid:
                valid_results.append(item)

    asyncio.run(check_results(results))

    return jsonify({"results": valid_results})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

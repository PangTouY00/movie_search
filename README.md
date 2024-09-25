# 影视资源查询系统

这是一个简单的影视资源查询系统，支持多端设备（手机、电脑、平板）并使用Docker进行多架构（AMD64、ARM64、ARMv7）的镜像构建和运行。

## 项目结构

movie_search/
├── app.py
├── templates/
│ └── index.html
├── static/
│ ├── style.css
│ ├── bootstrap.min.css
│ └── loading.gif
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .github/
└── workflows/
└── docker.yml


## 安装和运行

### 本地运行

1. **创建项目目录**：
    ```bash
    mkdir movie_search
    cd movie_search
    ```

2. **创建文件**：
    - `app.py`
    - `templates/index.html`
    - `static/style.css`
    - `static/bootstrap.min.css` （或者在HTML中使用CDN链接）
    - `static/loading.gif`
    - `requirements.txt`
    - `Dockerfile`
    - `docker-compose.yml`
    - `.github/workflows/docker.yml`

3. **安装依赖**：
    ```bash
    pip install -r requirements.txt
    ```

4. **运行应用**：
    ```bash
    python app.py
    ```

5. **访问应用**：
    打开浏览器，访问 `http://127.0.0.1:5000/`，你将看到一个简洁且响应式的查询页面。输入关键词并点击搜索，或者按下Enter键，页面将显示一个加载动画，表示正在查询。查询完成后，页面将显示匹配的影视资源的标题和URL。如果有资源的URL包含“该分享已被取消，无法访问”字样，则不会显示该资源。如果查询失败，错误信息将显示在结果区域。

### 使用Docker运行

1. **构建Docker镜像**：
    ```bash
    docker build -t w1770946466/movie_search:latest .
    ```

2. **运行Docker容器**：
    ```bash
    docker run -d -p 5000:5000 -e FLASK_ENV=development w1770946466/movie_search:latest
    ```

3. **查看容器日志**：
    ```bash
    docker logs <container_id>
    ```

4. **停止和删除容器**：
    ```bash
    docker stop <container_id>
    docker rm <container_id>
    ```

5. **删除镜像**：
    ```bash
    docker rmi w1770946466/movie_search:latest
    ```



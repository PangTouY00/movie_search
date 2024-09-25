# 使用多平台支持的基础镜像
FROM python:3.8-slim

# 设置工作目录
WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 5000

# 运行应用
CMD ["python", "app.py"]

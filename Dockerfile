# 使用官方 Python 3.9 镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# 复制当前目录内容到容器内
COPY . /app

# 创建虚拟环境并激活
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# 安装依赖
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 设置环境变量（可选）
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=8090

# 设置端口
EXPOSE 8090

# 启动 Flask 应用
CMD ["flask", "run"]

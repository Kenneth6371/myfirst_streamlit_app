# 阶段1：引入Node.js环境（支持pywencai依赖）
FROM node:18-slim AS node-base
# 阶段2：基于Python镜像，合并Node.js环境
FROM python:3.9-slim

# 复制Node.js运行时到Python镜像（核心：解决pywencai的Node.js依赖）
COPY --from=node-base /usr/local/bin/node /usr/local/bin/
COPY --from=node-base /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=node-base /usr/local/include/node /usr/local/include/node
# 建立npm/npx软链接（确保可调用Node.js包管理器）
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm
RUN ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

# 安装Node.js全局依赖（pywencai可能需要的jsdom等）
RUN npm install jsdom canvas -g

# 配置Python环境
WORKDIR /app
# 复制Python依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple  # 国内源加速

# 复制应用代码
COPY . .

# 暴露Streamlit默认端口（8501，需与后续容器端口映射一致）
EXPOSE 8501

# 启动Streamlit应用（指定地址0.0.0.0，允许外部访问）
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]

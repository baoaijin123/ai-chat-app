#!/bin/bash
# ============================================
# AI Chat 网站 - Ubuntu 服务器部署指南
# ============================================

# === 1. 安装基础软件 ===
sudo apt update
sudo apt install -y python3 python3-pip python3-venv mysql-server nginx

# === 2. 配置 MySQL ===
sudo mysql -e "CREATE DATABASE IF NOT EXISTS ai_chat CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -e "CREATE USER IF NOT EXISTS 'aichat'@'localhost' IDENTIFIED BY 'YourStrongPassword123!';"
sudo mysql -e "GRANT ALL PRIVILEGES ON ai_chat.* TO 'aichat'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"

# === 3. 上传代码到服务器 ===
# 方法1: 用scp从本地上传
#   scp -r ai-chat-app/ user@你的服务器IP:/home/user/ai-chat-app
# 方法2: 用git
#   在服务器上: git clone 你的仓库地址 /home/user/ai-chat-app

# === 4. 在服务器上配置项目 ===
cd /home/user/ai-chat-app

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 编辑 config.py，修改数据库密码和智谱API Key
# 或使用环境变量：
# export SECRET_KEY='一个随机字符串'
# export DATABASE_URL='mysql+pymysql://aichat:YourStrongPassword123!@localhost/ai_chat?charset=utf8mb4'
# export ZHIPU_API_KEY='你的智谱API密钥'

# === 5. 初始化数据库 ===
flask shell -c "from app import db, create_app; app = create_app(); app.app_context().push(); db.create_all(); print('数据库初始化完成')"

# === 6. 配置 Gunicorn Systemd 服务 ===
sudo tee /etc/systemd/system/aichat.service > /dev/null <<EOF
[Unit]
Description=AI Chat Gunicorn Service
After=network.target mysql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/home/user/ai-chat-app
Environment="PATH=/home/user/ai-chat-app/venv/bin"
Environment="SECRET_KEY=改成你自己的随机密钥"
Environment="DATABASE_URL=mysql+pymysql://aichat:YourStrongPassword123!@localhost/ai_chat?charset=utf8mb4"
Environment="ZHIPU_API_KEY=你的智谱API密钥"
ExecStart=/home/user/ai-chat-app/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 "app:create_app()"

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable aichat
sudo systemctl start aichat

# === 7. 配置 Nginx 反向代理 ===
sudo tee /etc/nginx/sites-available/aichat > /dev/null <<'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /home/user/ai-chat-app/static/;
        expires 30d;
    }

    # SSE流式传输需要关闭缓冲
    location /api/chat/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding off;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/aichat /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# === 8. 开放防火墙 ===
sudo ufw allow 80/tcp
sudo ufw allow 22/tcp
sudo ufw --force enable

# === 9. 设置目录权限 ===
sudo chown -R www-data:www-data /home/user/ai-chat-app

# === 完成！ ===
echo "====================================="
echo "部署完成！"
echo "请将 config.py 中的数据库密码和API Key改为实际值"
echo "然后重启服务: sudo systemctl restart aichat"
echo "访问地址: http://你的服务器IP"
echo "====================================="

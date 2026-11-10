# -*- coding: utf-8 -*-
"""开发服务器入口。

启动：python run.py
默认地址：http://127.0.0.1:5000
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

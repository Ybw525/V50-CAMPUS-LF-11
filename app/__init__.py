# -*- coding: utf-8 -*-
"""校园失物招领信息管理系统 —— 应用工厂。

项目代号：V50-CAMPUS-LF-11
版本：v1.0（第一个版本）
"""
import os

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()


def create_app(config_object=None):
    """创建并配置 Flask 应用实例。"""
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "v50-campus-lf-11-dev-key"),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL", "sqlite:///" + os.path.join(app.instance_path, "campus.db")
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        ITEMS_PER_PAGE=10,
    )
    if config_object:
        app.config.update(config_object)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "请先登录后再进行操作。"

    from app import models  # noqa: F401  确保模型在建表前完成注册

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(models.User, int(user_id))

    from app.auth import bp as auth_bp

    app.register_blueprint(auth_bp)

    with app.app_context():
        db.create_all()

    return app

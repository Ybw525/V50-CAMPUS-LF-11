# -*- coding: utf-8 -*-
"""数据模型（本提交仅建立用户表）。

对应禅道需求：
  #1 登录与角色权限 -> User
"""
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db

# 角色常量
ROLE_STUDENT = "student"
ROLE_ADMIN = "admin"


class User(UserMixin, db.Model):
    """系统用户，学生与管理员共用一张表，用 role 区分权限。"""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    real_name = db.Column(db.String(32), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(16), nullable=False, default=ROLE_STUDENT)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    @property
    def is_admin(self):
        return self.role == ROLE_ADMIN

    def __repr__(self):
        return f"<User {self.username}>"

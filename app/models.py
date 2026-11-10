# -*- coding: utf-8 -*-
"""数据模型：用户、失物/招领信息、分类。

对应禅道需求：
  #1 登录与角色权限   -> User
  #2 失物/招领信息发布 -> Item
  #3 列表与检索       -> Item 的查询字段
  #4 详情查看         -> Item.detail
  #5 我的发布         -> Item.owner_id
"""
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db

# 角色常量
ROLE_STUDENT = "student"
ROLE_ADMIN = "admin"

# 信息类型
TYPE_LOST = "lost"      # 失物
TYPE_FOUND = "found"    # 招领

STATUS_OPEN = "open"        # 待认领 / 待归还
STATUS_DONE = "done"        # 已完结

CATEGORIES = ["证件卡类", "电子产品", "书籍资料", "钥匙", "衣物", "其他"]


class User(UserMixin, db.Model):
    """系统用户，学生与管理員共用一张表，用 role 区分权限。"""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    real_name = db.Column(db.String(32), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(16), nullable=False, default=ROLE_STUDENT)
    created_at = db.Column(db.DateTime, default=datetime.now)

    items = db.relationship("Item", back_populates="owner", lazy="dynamic")

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    @property
    def is_admin(self):
        return self.role == ROLE_ADMIN

    def __repr__(self):
        return f"<User {self.username}>"


class Item(db.Model):
    """一条失物或招领信息。"""

    __tablename__ = "items"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    item_type = db.Column(db.String(8), nullable=False)      # lost / found
    category = db.Column(db.String(16), nullable=False)
    place = db.Column(db.String(64), nullable=False)          # 丢失/拾取地点
    happened_at = db.Column(db.Date, nullable=False)          # 丢失/拾取日期
    detail = db.Column(db.Text, nullable=False)               # 详细描述
    contact = db.Column(db.String(64), nullable=False)        # 联系方式
    status = db.Column(db.String(8), nullable=False, default=STATUS_OPEN)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    owner = db.relationship("User", back_populates="items")

    def __repr__(self):
        return f"<Item {self.id} {self.title}>"

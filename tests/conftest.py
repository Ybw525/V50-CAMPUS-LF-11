# -*- coding: utf-8 -*-
"""pytest 共享夹具与辅助函数。"""
from datetime import date

import pytest

from app import create_app, db
from app.models import (ROLE_ADMIN, ROLE_STUDENT, STATUS_OPEN, TYPE_LOST,
                        Item, User)


@pytest.fixture()
def app():
    """每个测试用独立的内存数据库，互不影响。"""
    test_app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    })

    with test_app.app_context():
        db.drop_all()
        db.create_all()

        admin = User(username="admin", real_name="管理员", role=ROLE_ADMIN)
        admin.set_password("admin123")
        student = User(username="student", real_name="测试学生", role=ROLE_STUDENT)
        student.set_password("123456")
        other = User(username="other", real_name="另一学生", role=ROLE_STUDENT)
        other.set_password("123456")

        db.session.add_all([admin, student, other])
        db.session.commit()

        yield test_app

        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


def login(client, username="student", password="123456"):
    """辅助函数：以指定用户登录。"""
    return client.post(
        "/auth/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def user_id(app, username):
    """按用户名取主键。"""
    with app.app_context():
        return User.query.filter_by(username=username).first().id


def make_item(app, username="student", **kwargs):
    """辅助函数：直接往库里插一条信息，避免测试依赖表单。"""
    with app.app_context():
        uid = User.query.filter_by(username=username).first().id
        data = dict(
            title="测试失物",
            item_type=TYPE_LOST,
            category="其他",
            place="测试地点",
            happened_at=date(2026, 11, 1),
            detail="测试描述",
            contact="138****0000",
            status=STATUS_OPEN,
            owner_id=uid,
        )
        data.update(kwargs)
        item = Item(**data)
        db.session.add(item)
        db.session.commit()
        return item.id

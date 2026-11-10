# -*- coding: utf-8 -*-
"""测试用例：对应禅道需求 #1 登录与角色权限。

用例编号：TC-001 ~ TC-006
"""
from tests.conftest import login


def test_login_page_accessible(client):
    """TC-001 未登录可访问登录页。"""
    resp = client.get("/auth/login")
    assert resp.status_code == 200
    assert "这段文字页面上根本不存在用于验证构建能否拦住失败" in resp.get_data(as_text=True)


def test_register_new_user(client):
    """TC-002 注册新用户成功，并跳转登录页。"""
    resp = client.post(
        "/auth/register",
        data={
            "username": "newuser",
            "real_name": "新同学",
            "password": "abc123",
            "password2": "abc123",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "注册成功" in resp.get_data(as_text=True)


def test_register_password_mismatch(client):
    """TC-003 两次密码不一致时注册被拒绝。"""
    resp = client.post(
        "/auth/register",
        data={
            "username": "newuser2",
            "real_name": "新同学",
            "password": "abc123",
            "password2": "abc456",
        },
        follow_redirects=True,
    )
    text = resp.get_data(as_text=True)
    assert "两次输入的密码不一致" in text


def test_register_duplicate_username(client):
    """TC-004 重复用户名注册被拒绝。"""
    resp = client.post(
        "/auth/register",
        data={
            "username": "student",
            "real_name": "重名",
            "password": "abc123",
            "password2": "abc123",
        },
        follow_redirects=True,
    )
    assert "该用户名已被占用" in resp.get_data(as_text=True)


def test_login_wrong_password(client):
    """TC-005 密码错误给出统一提示，不暴露账号是否存在。"""
    resp = login(client, "student", "wrong-pass")
    assert "用户名或密码不正确" in resp.get_data(as_text=True)


def test_login_success_and_logout(client):
    """TC-006 正确密码可登录，登录后显示真实姓名；退出后回到登录页。"""
    resp = login(client, "student", "123456")
    assert "测试学生" in resp.get_data(as_text=True)

    resp = client.get("/auth/logout", follow_redirects=True)
    assert "已退出登录" in resp.get_data(as_text=True)

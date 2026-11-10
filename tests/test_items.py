# -*- coding: utf-8 -*-
"""测试用例：对应禅道需求 #2 信息发布、#3 列表检索、#4 详情、#5 我的发布。

用例编号：TC-007 ~ TC-020
"""
from tests.conftest import login, make_item


def test_index_requires_no_login(client):
    """TC-007 列表页未登录也可访问（浏览不需要登录）。"""
    resp = client.get("/")
    assert resp.status_code == 200


def test_create_requires_login(client):
    """TC-008 未登录访问发布页被重定向到登录页。"""
    resp = client.get("/items/new", follow_redirects=False)
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_create_item_success(app, client):
    """TC-009 登录后发布信息成功，详情页可见。"""
    login(client)
    resp = client.post(
        "/items/new",
        data={
            "title": "图书馆遗失水杯",
            "item_type": "lost",
            "category": "其他",
            "place": "图书馆二楼",
            "happened_at": "2026-11-01",
            "detail": "白色保温杯，杯身有贴纸",
            "contact": "13800000000",
        },
        follow_redirects=True,
    )
    text = resp.get_data(as_text=True)
    assert "发布成功" in text
    assert "图书馆遗失水杯" in text


def test_create_item_missing_fields(app, client):
    """TC-010 必填项为空时不能提交（字段校验）。"""
    login(client)
    resp = client.post(
        "/items/new",
        data={"title": "", "item_type": "", "category": "", "place": "",
              "happened_at": "", "detail": "", "contact": ""},
        follow_redirects=True,
    )
    text = resp.get_data(as_text=True)
    assert "请填写标题" in text
    assert "请选择信息类型" in text


def test_create_item_future_date_rejected(app, client):
    """TC-011 日期晚于今天时拒绝提交（边界值校验）。"""
    login(client)
    resp = client.post(
        "/items/new",
        data={
            "title": "未来失物",
            "item_type": "lost",
            "category": "其他",
            "place": "某处",
            "happened_at": "2099-01-01",
            "detail": "描述",
            "contact": "13800000000",
        },
        follow_redirects=True,
    )
    assert "日期不能晚于今天" in resp.get_data(as_text=True)


def test_search_by_keyword(app, client):
    """TC-012 关键词检索命中标题。"""
    make_item(app, "student", title="蓝色雨伞")
    make_item(app, "student", title="黑色钱包")
    resp = client.get("/?q=雨伞")
    text = resp.get_data(as_text=True)
    assert "蓝色雨伞" in text
    assert "黑色钱包" not in text


def test_search_by_category(app, client):
    """TC-013 按分类筛选。"""
    make_item(app, "student", title="校园卡", category="证件卡类")
    make_item(app, "student", title="钥匙串", category="钥匙")
    resp = client.get("/?category=钥匙")
    text = resp.get_data(as_text=True)
    assert "钥匙串" in text
    assert "校园卡" not in text


def test_search_by_type(app, client):
    """TC-014 按类型筛选失物/招领。"""
    make_item(app, "student", title="我丢的伞", item_type="lost")
    make_item(app, "student", title="我捡的卡", item_type="found")
    resp = client.get("/?type=found")
    text = resp.get_data(as_text=True)
    assert "我捡的卡" in text
    assert "我丢的伞" not in text


def test_detail_not_found(app, client):
    """TC-015 访问不存在的信息返回 404。"""
    resp = client.get("/items/99999")
    assert resp.status_code == 404


def test_detail_visible(app, client):
    """TC-016 详情页展示完整字段。"""
    item_id = make_item(app, "student", title="详情测试物品", place="实验楼")
    resp = client.get(f"/items/{item_id}")
    text = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "详情测试物品" in text
    assert "实验楼" in text


def test_mine_only_shows_own(app, client):
    """TC-017 我的发布只显示本人信息。"""
    make_item(app, "student", title="我的物品")
    make_item(app, "other", title="别人的物品")
    login(client, "student", "123456")
    resp = client.get("/my")
    text = resp.get_data(as_text=True)
    assert "我的物品" in text
    assert "别人的物品" not in text


def test_delete_own_item(app, client):
    """TC-018 可删除本人发布的信息。"""
    item_id = make_item(app, "student", title="待删除物品")
    login(client, "student", "123456")
    resp = client.post(f"/items/{item_id}/delete", follow_redirects=True)
    assert "已删除" in resp.get_data(as_text=True)


def test_delete_others_item_forbidden(app, client):
    """TC-019 不能删除他人发布的信息（权限校验，返回 403）。"""
    item_id = make_item(app, "other", title="别人的物品")
    login(client, "student", "123456")
    resp = client.post(f"/items/{item_id}/delete")
    assert resp.status_code == 403


def test_toggle_status(app, client):
    """TC-020 本人可将状态在“待认领/已完结”间切换。"""
    item_id = make_item(app, "student", title="状态切换测试")
    login(client, "student", "123456")

    resp = client.post(f"/items/{item_id}/toggle", follow_redirects=True)
    assert "状态已更新" in resp.get_data(as_text=True)

    detail = client.get(f"/items/{item_id}").get_data(as_text=True)
    assert "已完结" in detail

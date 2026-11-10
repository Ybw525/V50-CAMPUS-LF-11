# -*- coding: utf-8 -*-
"""测试用例：第二个版本 v2.0（对应禅道需求 #6~#10）。

用例编号：TC-021 ~ TC-032
"""
from tests.conftest import login, make_item


# ---------- 需求 #6 留言 / 联系方式 ----------

def test_message_requires_login(app, client):
    """TC-021 未登录用户不能留言，提交被重定向到登录页。"""
    item_id = make_item(app, "student", title="留言权限测试")
    resp = client.post(f"/items/{item_id}/message", data={"content": "在吗"})
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_add_message_success(app, client):
    """TC-022 登录后可留言，详情页能看到留言内容与作者。"""
    item_id = make_item(app, "student", title="雨伞招领")
    login(client, "other", "123456")
    resp = client.post(
        f"/items/{item_id}/message",
        data={"content": "这把伞是我的，伞柄有划痕。"},
        follow_redirects=True,
    )
    text = resp.get_data(as_text=True)
    assert "留言已发布" in text
    assert "这把伞是我的" in text
    assert "另一学生" in text


def test_add_empty_message_rejected(app, client):
    """TC-023 空留言被拒绝，不写入数据库。"""
    item_id = make_item(app, "student", title="空留言测试")
    login(client, "student", "123456")
    resp = client.post(f"/items/{item_id}/message", data={"content": "   "},
                       follow_redirects=True)
    assert "留言内容不能为空" in resp.get_data(as_text=True)


def test_delete_others_message_forbidden(app, client):
    """TC-024 不能删除他人留言（返回 403）。"""
    from app import db
    from app.models import Message
    item_id = make_item(app, "student", title="留言删除测试")
    with app.app_context():
        from app.models import User
        author = User.query.filter_by(username="other").first()
        msg = Message(item_id=item_id, author_id=author.id, content="别人的留言")
        db.session.add(msg)
        db.session.commit()
        msg_id = msg.id

    login(client, "student", "123456")
    resp = client.post(f"/messages/{msg_id}/delete")
    assert resp.status_code == 403


# ---------- 需求 #7 认领状态更新 ----------

def test_claim_requires_owner(app, client):
    """TC-025 非发布者不能登记认领结果（返回 403）。"""
    item_id = make_item(app, "other", title="他人信息")
    login(client, "student", "123456")
    resp = client.post(f"/items/{item_id}/claim", data={"claimer": "张三"})
    assert resp.status_code == 403


def test_claim_records_claimer_and_done(app, client):
    """TC-026 本人登记认领后，状态变已完结且记录认领人与时间。"""
    item_id = make_item(app, "student", title="待认领水杯")
    login(client, "student", "123456")
    resp = client.post(
        f"/items/{item_id}/claim",
        data={"claimer": "李四 2024070912", "claim_note": "已当面核对物品特征"},
        follow_redirects=True,
    )
    text = resp.get_data(as_text=True)
    assert "认领结果已登记" in text
    assert "已完结" in text
    assert "李四 2024070912" in text


def test_claim_requires_claimer(app, client):
    """TC-027 认领人为空时拒绝提交。"""
    item_id = make_item(app, "student", title="认领人必填")
    login(client, "student", "123456")
    resp = client.post(f"/items/{item_id}/claim", data={"claimer": ""},
                       follow_redirects=True)
    assert "请填写认领人" in resp.get_data(as_text=True)


# ---------- 需求 #8 管理员审核与下架 ----------

def test_audit_page_admin_only(app, client):
    """TC-028 普通学生访问审核台返回 403。"""
    login(client, "student", "123456")
    resp = client.get("/admin/audit")
    assert resp.status_code == 403


def test_pending_item_hidden_from_list(app, client):
    """TC-029 待审核信息不出现在普通用户列表中。"""
    make_item(app, "student", title="待审核信息", audit_status="pending")
    resp = client.get("/")
    assert "待审核信息" not in resp.get_data(as_text=True)


def test_audit_pass_makes_visible(app, client):
    """TC-030 管理员审核通过后，信息在列表可见。"""
    from app import db
    from app.models import Item
    item_id = make_item(app, "student", title="审核通过后可见", audit_status="pending")

    login(client, "admin", "admin123")
    resp = client.post(f"/admin/items/{item_id}/audit",
                       data={"decision": "pass"}, follow_redirects=True)
    assert "审核通过" in resp.get_data(as_text=True)

    client.get("/auth/logout", follow_redirects=True)
    assert "审核通过后可见" in client.get("/").get_data(as_text=True)


def test_offline_item_hidden(app, client):
    """TC-031 管理员下架后，信息在列表与详情均不可见。"""
    item_id = make_item(app, "student", title="将被下架的信息")
    login(client, "admin", "admin123")
    client.post(f"/admin/items/{item_id}/offline", follow_redirects=True)

    client.get("/auth/logout", follow_redirects=True)
    assert "将被下架的信息" not in client.get("/").get_data(as_text=True)
    assert client.get(f"/items/{item_id}").status_code == 404


# ---------- 需求 #9 简单统计 ----------

def test_stats_admin_only(app, client):
    """TC-032 普通学生访问统计页返回 403。"""
    login(client, "student", "123456")
    resp = client.get("/stats")
    assert resp.status_code == 403


def test_stats_numbers_match_data(app, client):
    """TC-033 统计页指标与数据库实际条数一致。"""
    make_item(app, "student", title="统计用的失物", item_type="lost")
    make_item(app, "student", title="统计用的招领", item_type="found")

    login(client, "admin", "admin123")
    resp = client.get("/stats")
    text = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "信息总数" in text
    assert "认领成功率" in text

def test_contact_hidden_when_logged_out(app, client):
    """TC-034 未登录访问详情页时联系方式不可见（需求 #6 联系方式可见性）。"""
    item_id = make_item(app, "student", title="联系方式可见性测试")
    resp = client.get(f"/items/{item_id}")
    text = resp.get_data(as_text=True)
    assert "登录后可见" in text
    assert "138****0000" not in text


def test_contact_visible_when_logged_in(app, client):
    """TC-035 登录后详情页可见联系方式。"""
    item_id = make_item(app, "student", title="联系方式展示验证")
    login(client, "other", "123456")
    resp = client.get(f"/items/{item_id}")
    text = resp.get_data(as_text=True)
    assert "138****0000" in text
    assert "登录后可见" not in text

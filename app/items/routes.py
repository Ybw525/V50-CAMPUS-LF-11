# -*- coding: utf-8 -*-
"""失物/招领信息蓝图。

对应禅道需求：
  #2 信息发布    -> create
  #3 列表与检索  -> index
  #4 详情查看    -> detail
  #5 我的发布    -> mine
"""
from datetime import date, datetime

from flask import (Blueprint, abort, flash, redirect, render_template, request,
                   url_for)
from flask_login import current_user, login_required

from app import db
from app.models import (AUDIT_LABELS, AUDIT_PASSED, AUDIT_PENDING,
                        AUDIT_REJECTED, CATEGORIES, STATUS_DONE, STATUS_OFFLINE,
                        STATUS_OPEN, TYPE_FOUND, TYPE_LOST, Item, Message)

bp = Blueprint("items", __name__)

TYPE_LABELS = {TYPE_LOST: "失物", TYPE_FOUND: "招领"}


def _to_date(text, fallback=None):
    """把 YYYY-MM-DD 字符串转为 date，解析失败时返回 fallback。"""
    if not text:
        return fallback
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%d").date()
    except ValueError:
        return fallback


@bp.route("/")
def index():
    """信息列表 + 关键词检索 + 分类/类型筛选（需求 #3）。"""
    keyword = (request.args.get("q") or "").strip()
    category = (request.args.get("category") or "").strip()
    item_type = (request.args.get("type") or "").strip()
    status = (request.args.get("status") or "").strip()
    page = request.args.get("page", 1, type=int)

    query = Item.query

    # 需求 #8：未审核通过或已下架的信息不对普通用户展示
    if not (current_user.is_authenticated and current_user.is_admin):
        query = query.filter(Item.audit_status == AUDIT_PASSED,
                             Item.status != STATUS_OFFLINE)

    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            db.or_(
                Item.title.like(like),
                Item.detail.like(like),
                Item.place.like(like),
            )
        )
    if category in CATEGORIES:
        query = query.filter(Item.category == category)
    if item_type in (TYPE_LOST, TYPE_FOUND):
        query = query.filter(Item.item_type == item_type)
    if status in (STATUS_OPEN, STATUS_DONE):
        query = query.filter(Item.status == status)

    pagination = query.order_by(Item.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )

    return render_template(
        "items/index.html",
        pagination=pagination,
        items=pagination.items,
        keyword=keyword,
        category=category,
        item_type=item_type,
        status=status,
        categories=CATEGORIES,
        type_labels=TYPE_LABELS,
        active="index",
    )


@bp.route("/items/new", methods=["GET", "POST"])
@login_required
def create():
    """发布一条失物或招领信息（需求 #2）。"""
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        item_type = (request.form.get("item_type") or "").strip()
        category = (request.form.get("category") or "").strip()
        place = (request.form.get("place") or "").strip()
        happened = _to_date(request.form.get("happened_at"))
        detail = (request.form.get("detail") or "").strip()
        contact = (request.form.get("contact") or "").strip()

        errors = []
        if not title:
            errors.append("请填写标题。")
        if item_type not in (TYPE_LOST, TYPE_FOUND):
            errors.append("请选择信息类型（失物/招领）。")
        if category not in CATEGORIES:
            errors.append("请选择物品分类。")
        if not place:
            errors.append("请填写地点。")
        if happened is None:
            errors.append("请选择日期（格式 2026-11-01）。")
        elif happened > date.today():
            errors.append("日期不能晚于今天。")
        if not detail:
            errors.append("请填写详细描述。")
        if not contact:
            errors.append("请填写联系方式。")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "items/form.html",
                categories=CATEGORIES,
                type_labels=TYPE_LABELS,
                form=request.form,
                active="create",
            )

        item = Item(
            title=title,
            item_type=item_type,
            category=category,
            place=place,
            happened_at=happened,
            detail=detail,
            contact=contact,
            owner_id=current_user.id,
            audit_status=AUDIT_PENDING,   # 需求 #8：新发布信息进入待审核
        )
        db.session.add(item)
        db.session.commit()

        flash("发布成功。", "success")
        return redirect(url_for("items.detail", item_id=item.id))

    return render_template(
        "items/form.html",
        categories=CATEGORIES,
        type_labels=TYPE_LABELS,
        form={},
        active="create",
    )


@bp.route("/items/<int:item_id>")
def detail(item_id):
    """查看单条信息详情（需求 #4）。"""
    item = db.session.get(Item, item_id)
    if item is None:
        abort(404)
    # 需求 #8：未通过审核或已下架的信息，除管理员和本人外一律 404
    is_owner = current_user.is_authenticated and current_user.id == item.owner_id
    is_admin = current_user.is_authenticated and current_user.is_admin
    if not item.is_visible and not (is_owner or is_admin):
        abort(404)
    return render_template(
        "items/detail.html",
        item=item,
        messages=item.messages.all(),
        audit_labels=AUDIT_LABELS,
        type_labels=TYPE_LABELS,
        active="index",
    )


@bp.route("/items/<int:item_id>/toggle", methods=["POST"])
@login_required
def toggle_status(item_id):
    """标记已完结 / 恢复待认领（需求 #5 的配套动作，仅本人可操作）。"""
    item = db.session.get(Item, item_id)
    if item is None:
        abort(404)
    if item.owner_id != current_user.id and not current_user.is_admin:
        abort(403)

    item.status = STATUS_DONE if item.status == STATUS_OPEN else STATUS_OPEN
    db.session.commit()
    flash("状态已更新。", "success")
    return redirect(url_for("items.detail", item_id=item.id))


@bp.route("/my")
@login_required
def mine():
    """我的发布（需求 #5）。"""
    page = request.args.get("page", 1, type=int)
    pagination = (
        Item.query.filter_by(owner_id=current_user.id)
        .order_by(Item.created_at.desc())
        .paginate(page=page, per_page=10, error_out=False)
    )
    return render_template(
        "items/mine.html",
        pagination=pagination,
        items=pagination.items,
        type_labels=TYPE_LABELS,
        active="mine",
    )


@bp.route("/items/<int:item_id>/delete", methods=["POST"])
@login_required
def delete(item_id):
    """删除本人发布的信息。"""
    item = db.session.get(Item, item_id)
    if item is None:
        abort(404)
    if item.owner_id != current_user.id and not current_user.is_admin:
        abort(403)

    db.session.delete(item)
    db.session.commit()
    flash("已删除。", "info")
    return redirect(url_for("items.mine"))


# ==================== 需求 #6 留言 / 联系方式 ====================

@bp.route("/items/<int:item_id>/message", methods=["POST"])
@login_required
def add_message(item_id):
    """在详情页留言（需求 #6）。未登录用户不可留言。"""
    item = db.session.get(Item, item_id)
    if item is None:
        abort(404)

    content = (request.form.get("content") or "").strip()
    if not content:
        flash("留言内容不能为空。", "danger")
        return redirect(url_for("items.detail", item_id=item.id))
    if len(content) > 500:
        flash("留言不能超过 500 字。", "danger")
        return redirect(url_for("items.detail", item_id=item.id))

    msg = Message(item_id=item.id, author_id=current_user.id, content=content)
    db.session.add(msg)
    db.session.commit()

    flash("留言已发布。", "success")
    return redirect(url_for("items.detail", item_id=item.id) + "#messages")


@bp.route("/messages/<int:message_id>/delete", methods=["POST"])
@login_required
def delete_message(message_id):
    """留言作者本人或管理员可删除留言。"""
    msg = db.session.get(Message, message_id)
    if msg is None:
        abort(404)
    if msg.author_id != current_user.id and not current_user.is_admin:
        abort(403)

    item_id = msg.item_id
    db.session.delete(msg)
    db.session.commit()
    flash("留言已删除。", "info")
    return redirect(url_for("items.detail", item_id=item_id) + "#messages")


# ==================== 需求 #7 认领状态更新 ====================

@bp.route("/items/<int:item_id>/claim", methods=["POST"])
@login_required
def claim_item(item_id):
    """登记认领结果：记录认领人、认领说明，并把状态置为已完结（需求 #7）。"""
    item = db.session.get(Item, item_id)
    if item is None:
        abort(404)
    # 只有发布者本人或管理员可以登记认领结果
    if item.owner_id != current_user.id and not current_user.is_admin:
        abort(403)

    claimer = (request.form.get("claimer") or "").strip()
    note = (request.form.get("claim_note") or "").strip()
    if not claimer:
        flash("请填写认领人。", "danger")
        return redirect(url_for("items.detail", item_id=item.id))

    item.status = STATUS_DONE
    item.claimer = claimer[:64]
    item.claim_note = note[:255]
    item.claimed_at = datetime.now()
    db.session.commit()

    flash("认领结果已登记，信息已标记为已完结。", "success")
    return redirect(url_for("items.detail", item_id=item.id))


# ==================== 需求 #8 管理员审核与下架 ====================

@bp.route("/admin/audit")
@login_required
def admin_audit():
    """管理员审核台：列出待审核、已下架的信息（需求 #8）。"""
    if not current_user.is_admin:
        abort(403)

    pending = (Item.query.filter_by(audit_status=AUDIT_PENDING)
               .order_by(Item.created_at.desc()).all())
    offline = (Item.query.filter_by(status=STATUS_OFFLINE)
               .order_by(Item.updated_at.desc()).all())
    return render_template(
        "items/audit.html",
        pending=pending,
        offline=offline,
        type_labels=TYPE_LABELS,
        audit_labels=AUDIT_LABELS,
        active="audit",
    )


@bp.route("/admin/items/<int:item_id>/audit", methods=["POST"])
@login_required
def audit_item(item_id):
    """审核通过或驳回（需求 #8）。"""
    if not current_user.is_admin:
        abort(403)

    item = db.session.get(Item, item_id)
    if item is None:
        abort(404)

    decision = (request.form.get("decision") or "").strip()
    note = (request.form.get("audit_note") or "").strip()

    if decision == "pass":
        item.audit_status = AUDIT_PASSED
        item.audit_note = note[:255]
        flash(f"《{item.title}》审核通过。", "success")
    elif decision == "reject":
        item.audit_status = AUDIT_REJECTED
        item.audit_note = note[:255] or "信息不符合要求。"
        flash(f"《{item.title}》已驳回。", "warning")
    else:
        flash("审核操作无效。", "danger")
        return redirect(url_for("items.admin_audit"))

    item.audited_by = current_user.real_name
    item.audited_at = datetime.now()
    db.session.commit()
    return redirect(url_for("items.admin_audit"))


@bp.route("/admin/items/<int:item_id>/offline", methods=["POST"])
@login_required
def offline_item(item_id):
    """下架 / 恢复上架（需求 #8）。"""
    if not current_user.is_admin:
        abort(403)

    item = db.session.get(Item, item_id)
    if item is None:
        abort(404)

    if item.status == STATUS_OFFLINE:
        item.status = STATUS_OPEN
        flash(f"《{item.title}》已恢复上架。", "success")
    else:
        item.status = STATUS_OFFLINE
        flash(f"《{item.title}》已下架。", "warning")
    db.session.commit()
    return redirect(url_for("items.admin_audit"))


# ==================== 需求 #9 简单统计 ====================

@bp.route("/stats")
@login_required
def stats():
    """简单统计页（需求 #9）：仅管理员可看。"""
    if not current_user.is_admin:
        abort(403)

    total = Item.query.count()
    open_count = Item.query.filter_by(status=STATUS_OPEN).count()
    done_count = Item.query.filter_by(status=STATUS_DONE).count()
    lost_count = Item.query.filter_by(item_type=TYPE_LOST).count()
    found_count = Item.query.filter_by(item_type=TYPE_FOUND).count()
    pending_count = Item.query.filter_by(audit_status=AUDIT_PENDING).count()
    offline_count = Item.query.filter_by(status=STATUS_OFFLINE).count()
    claim_success = Item.query.filter(Item.claimed_at.isnot(None)).count()

    # 分类分布
    by_category = []
    for cat in CATEGORIES:
        n = Item.query.filter_by(category=cat).count()
        by_category.append((cat, n))

    # 认领成功率
    rate = round(done_count * 100.0 / total, 1) if total else 0.0

    return render_template(
        "items/stats.html",
        total=total, open_count=open_count, done_count=done_count,
        lost_count=lost_count, found_count=found_count,
        pending_count=pending_count, offline_count=offline_count,
        claim_success=claim_success, by_category=by_category, rate=rate,
        active="stats",
    )

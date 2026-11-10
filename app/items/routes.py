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
from app.models import (CATEGORIES, STATUS_DONE, STATUS_OPEN, TYPE_FOUND,
                        TYPE_LOST, Item)

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
    return render_template(
        "items/detail.html",
        item=item,
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

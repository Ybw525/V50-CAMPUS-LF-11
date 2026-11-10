# -*- coding: utf-8 -*-
"""认证蓝图：登录、注册、退出（禅道需求 #1 登录与角色权限）。"""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app import db
from app.models import ROLE_STUDENT, User

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("items.index"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            # 统一提示，不暴露账号是否存在
            flash("用户名或密码不正确。", "danger")
            return render_template("auth/login.html", username=username, active="login")

        login_user(user)
        flash(f"欢迎回来，{user.real_name}。", "success")
        return redirect(url_for("items.index"))

    return render_template("auth/login.html", username="", active="login")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("items.index"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        real_name = (request.form.get("real_name") or "").strip()
        password = request.form.get("password") or ""
        password2 = request.form.get("password2") or ""

        errors = []
        if not username or len(username) < 3:
            errors.append("用户名至少 3 个字符。")
        if not real_name:
            errors.append("请填写真实姓名。")
        if len(password) < 6:
            errors.append("密码至少 6 位。")
        if password != password2:
            errors.append("两次输入的密码不一致。")
        if User.query.filter_by(username=username).first():
            errors.append("该用户名已被占用。")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("auth/register.html", active="register")

        user = User(username=username, real_name=real_name, role=ROLE_STUDENT)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("注册成功，请登录。", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", active="register")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("已退出登录。", "info")
    return redirect(url_for("auth.login"))

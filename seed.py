# -*- coding: utf-8 -*-
"""初始化数据库并写入演示数据（管理员 + 学生 + 若干失物招领信息）。

用法：
    python seed.py
"""
from datetime import date

from app import create_app, db
from app.models import (AUDIT_PASSED, AUDIT_PENDING, ROLE_ADMIN, ROLE_STUDENT,
                        STATUS_DONE, STATUS_OFFLINE, STATUS_OPEN, TYPE_FOUND,
                        TYPE_LOST, Item, Message, User)

app = create_app()


def main():
    with app.app_context():
        # 重建表，方便反复演示
        db.drop_all()
        db.create_all()

        admin = User(username="admin", real_name="保卫处管理员", role=ROLE_ADMIN)
        admin.set_password("admin123")

        yan = User(username="yanbowen", real_name="闫博文", role=ROLE_STUDENT)
        yan.set_password("123456")

        li = User(username="liyinuo", real_name="李以诺", role=ROLE_STUDENT)
        li.set_password("123456")

        db.session.add_all([admin, yan, li])
        db.session.commit()

        demo = [
            Item(title="图书馆三楼遗失黑色雨伞", item_type=TYPE_LOST,
                 category="其他", place="图书馆三楼自习区",
                 happened_at=date(2026, 11, 6),
                 detail="黑色长柄雨伞，伞面有浅灰色条纹，伞柄有一圈磨损，伞骨内侧贴了一张蓝色贴纸。",
                 contact="138****0611（微信同号）", status=STATUS_OPEN, owner_id=yan.id),
            Item(title="捡到校园卡一张（王××）", item_type=TYPE_FOUND,
                 category="证件卡类", place="第二食堂二楼窗口",
                 happened_at=date(2026, 11, 7),
                 detail="校园卡姓名首字为“王”，卡面有轻微划痕，已交至保卫处登记，请本人携带学生证领取。",
                 contact="第二食堂服务台 或 保卫处 1 号窗口", status=STATUS_OPEN, owner_id=admin.id),
            Item(title="遗失 AirPods 充电盒", item_type=TYPE_LOST,
                 category="电子产品", place="体育馆篮球场旁看台",
                 happened_at=date(2026, 11, 5),
                 detail="白色充电盒，盒盖内侧有一道细划痕，序列号尾号 4 位为 K2X9。",
                 contact="QQ 1234****99", status=STATUS_DONE, owner_id=li.id),
            Item(title="捡到黑色钥匙串（三把）", item_type=TYPE_FOUND,
                 category="钥匙", place="教学楼 A 座 204 教室",
                 happened_at=date(2026, 11, 8),
                 detail="黑色钥匙圈，挂三把钥匙和一个小熊挂件，已放在 A 座值班室。",
                 contact="A 座一楼值班室", status=STATUS_OPEN, owner_id=li.id),
            Item(title="遗失高等数学教材（同济版）", item_type=TYPE_LOST,
                 category="书籍资料", place="教学楼 B 座 301",
                 happened_at=date(2026, 11, 4),
                 detail="书脊用胶带补过，扉页写有姓名和班级，内页有较多荧光笔标记。",
                 contact="177****3021", status=STATUS_OPEN, owner_id=yan.id),
        ]
        db.session.add_all(demo)
        db.session.commit()

        # 需求 #6：给「图书馆三楼遗失黑色雨伞」加两条留言
        umbrella = Item.query.filter_by(title="图书馆三楼遗失黑色雨伞").first()
        if umbrella:
            db.session.add_all([
                Message(item_id=umbrella.id, author_id=li.id,
                        content="这把伞我好像在图书馆三楼见过，伞柄是不是有一圈黑色胶带？"),
                Message(item_id=umbrella.id, author_id=yan.id,
                        content="对，伞柄有一圈磨损，内侧还贴了张蓝色小贴纸。可以直接联系我。"),
            ])
            db.session.commit()

        # 需求 #8：造一条待审核信息，供管理员审核演示
        db.session.add(Item(
            title="捡到一张学生证（张××）", item_type=TYPE_FOUND,
            category="证件卡类", place="图书馆一楼大厅",
            happened_at=date(2026, 11, 9),
            detail="学生证姓名首字为“张”，专业为计算机应用技术，已交图书馆前台。",
            contact="图书馆前台", status=STATUS_OPEN, owner_id=li.id,
            audit_status=AUDIT_PENDING,
        ))
        db.session.commit()

        print("初始化完成")
        print(f"  用户 {User.query.count()} 个，信息 {Item.query.count()} 条")
        print("  管理员账号：admin / admin123")
        print("  学生账号：yanbowen / 123456，liyinuo / 123456")
        print(f"  留言 {Message.query.count()} 条，待审核 {(Item.query.filter_by(audit_status=AUDIT_PENDING)).count()} 条")


if __name__ == "__main__":
    main()

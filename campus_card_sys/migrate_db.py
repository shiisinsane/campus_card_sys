#!/usr/bin/env python3
# migrate_db.py - 数据库迁移脚本

import sqlite3
import os
from app import app
from models import db

def migrate_database():
    """迁移数据库，添加contact和select_loc字段"""

    # 数据库文件路径
    db_path = 'campus_card.db'

    if not os.path.exists(db_path):
        print("数据库文件不存在，将创建新的数据库")
        with app.app_context():
            db.create_all()
        print("✓ 新数据库创建完成")
        return

    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(campus_card)")
        columns = [column[1] for column in cursor.fetchall()]

        # 添加contact字段
        if 'contact' not in columns:
            print("正在添加contact字段...")
            cursor.execute("ALTER TABLE campus_card ADD COLUMN contact VARCHAR(20)")
            print("✓ contact字段添加成功")
        else:
            print("✓ contact字段已存在")

        # 添加select_loc字段
        if 'select_loc' not in columns:
            print("正在添加select_loc字段...")
            cursor.execute("ALTER TABLE campus_card ADD COLUMN select_loc VARCHAR(100)")
            print("✓ select_loc字段添加成功")
        else:
            print("✓ select_loc字段已存在")

        # 提交更改
        conn.commit()
        print("✓ 数据库迁移完成")

    except Exception as e:
        print(f"✗ 数据库迁移出错: {e}")
        conn.rollback()
    finally:
        conn.close()

def update_existing_records():
    """为现有记录更新select_loc字段"""

    with app.app_context():
        from models import CampusCard
        from app import extract_location_from_text

        # 获取所有没有select_loc的记录
        cards = CampusCard.query.filter(
            CampusCard.select_loc.is_(None),
            CampusCard.found_location.isnot(None)
        ).all()

        print(f"找到{len(cards)}条需要更新的记录")

        updated_count = 0
        for card in cards:
            if card.found_location and card.found_location.strip():
                try:
                    # 使用模块A分析地点
                    location_analysis = extract_location_from_text(
                        card.found_location.strip(),
                        return_best_match=True
                    )

                    if location_analysis.get('best_match') and location_analysis.get('confidence', 0) > 0.5:
                        card.select_loc = location_analysis['best_match']
                        updated_count += 1
                        print(f"更新记录 {card.id}: '{card.found_location}' -> '{card.select_loc}'")

                except Exception as e:
                    print(f"分析记录 {card.id} 失败: {e}")

        if updated_count > 0:
            db.session.commit()
            print(f"✓ 成功更新{updated_count}条记录")
        else:
            print("没有记录需要更新")

def show_table_structure():
    """显示表结构"""
    db_path = 'campus_card.db'

    if not os.path.exists(db_path):
        print("数据库文件不存在")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("\n当前campus_card表结构:")
        print("-" * 50)
        cursor.execute("PRAGMA table_info(campus_card)")
        columns = cursor.fetchall()

        for column in columns:
            _, name, type_, notnull, _, pk = column
            nullable = "NOT NULL" if notnull else "NULL"
            primary = "PRIMARY KEY" if pk else ""
            print(f"{name:15} {type_:15} {nullable:10} {primary}")

    except Exception as e:
        print(f"查询表结构出错: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    print("=" * 50)
    print("数据库迁移工具 - 添加select_loc字段")
    print("=" * 50)

    # 显示当前表结构
    show_table_structure()

    # 执行迁移
    migrate_database()

    # 更新现有记录
    print("\n开始更新现有记录...")
    update_existing_records()

    # 显示迁移后的表结构
    show_table_structure()

    print("\n迁移完成！")

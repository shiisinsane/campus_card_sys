# init_data.py
from app import app
from models import db, User, CampusCard, ForumPost, Reward
from datetime import datetime

def init_test_data():
    """初始化测试数据"""
    with app.app_context():
        # 创建数据库表
        db.create_all()
        
        # 清空现有数据
        db.session.query(User).delete()
        db.session.query(CampusCard).delete()
        db.session.query(ForumPost).delete()
        db.session.query(Reward).delete()
        
        # 创建测试用户
        test_users = [
            User(student_id='2021001', full_name='张三', password='123456', points=100),
            User(student_id='2021002', full_name='李四', password='123456', points=50),
            User(student_id='2021003', full_name='王五', password='123456', points=200),
        ]
        
        for user in test_users:
            db.session.add(user)
        
        # 创建测试校园卡
        test_cards = [
            CampusCard(
                card_number='2021004',
                student_id='2021004',
                status='found',
                found_location='图书馆一楼',
                found_time=datetime.now(),
                handler_option=1,
                contact='13800138001',
                is_matched=False,
                select_loc='图书馆'
            ),
            CampusCard(
                card_number='2021005',
                student_id='2021005',
                status='found',
                found_location='梧桐苑二楼',
                found_time=datetime.now(),
                handler_option=2,
                contact="梧桐苑",
                is_matched=False,
                select_loc='梧桐苑'
            ),
            CampusCard(
                card_number='2021006',
                student_id='2021006',
                status='found',
                found_location='图书馆三楼',
                found_time=datetime.now(),
                handler_option=1,
                contact='13800138002',
                is_matched=False,
                select_loc='图书馆'
            ),
            CampusCard(
                card_number='2021007',
                student_id='2021007',
                status='found',
                found_location='文体中心附近',
                found_time=datetime.now(),
                handler_option=2,
                contact="梧桐苑",
                is_matched=False,
                select_loc='文体中心'
            ),
            CampusCard(
                card_number='2021008',
                student_id='2021008',
                status='found',
                found_location='图书馆二楼',
                found_time=datetime.now(),
                handler_option=1,
                contact='13800138003',
                is_matched=False,
                select_loc='图书馆'
            ),
            CampusCard(
                card_number='2021009',
                student_id='2021009',
                status='found',
                found_location='教一楼',
                found_time=datetime.now(),
                handler_option=2,
                contact="中一楼",
                is_matched=False,
                select_loc='教一楼'
            ),
            CampusCard(
                card_number='2021010',
                student_id='2021010',
                status='found',
                found_location='康桥一楼',
                found_time=datetime.now(),
                handler_option=1,
                contact='13800138004',
                is_matched=False,
                select_loc='康桥苑'
            ),
            CampusCard(
                card_number='2021011',
                student_id='2021011',
                status='found',
                found_location='崇实书院正门',
                found_time=datetime.now(),
                handler_option=2,
                contact="梧桐苑",
                is_matched=False,
                select_loc='崇实书院'
            ),
            CampusCard(
                card_number='2021012',
                student_id='2021012',
                status='found',
                found_location='图书馆一楼',
                found_time=datetime.now(),
                handler_option=1,
                contact='13800138005',
                is_matched=False,
                select_loc='图书馆'
            ),
            CampusCard(
                card_number='2021013',
                student_id='2021013',
                status='found',
                found_location='西南篮球场',
                found_time=datetime.now(),
                handler_option=2,
                contact="梧桐苑",
                is_matched=False,
                select_loc='西篮球场'
            ),
            CampusCard(
                card_number='2021001',
                student_id='2021001',
                status='found',
                found_location='康桥',
                found_time=datetime.now(),
                handler_option=2,
                contact="康桥苑",
                is_matched=False,
                select_loc='康桥苑'
            )
        ]
        
        for card in test_cards:
            db.session.add(card)
        
        # 创建测试论坛帖子
        test_posts = [
            ForumPost(
                title='欢迎使用校园卡管理系统',
                content='这是一个测试帖子，欢迎大家使用我们的校园卡管理系统！',
                author_id=1,
                is_ad=False
            ),
            ForumPost(
                title='校园卡丢失怎么办？',
                content='如果你的校园卡丢失了，可以通过我们的系统查询是否有人捡到。',
                author_id=2,
                is_ad=False
            ),
            ForumPost(
                title='在图书馆丢失了校园卡',
                content='昨天在图书馆三楼自习时不小心丢失了校园卡，有人捡到吗？',
                author_id=1,
                is_ad=False
            ),
            ForumPost(
                title='食堂二楼发现校园卡',
                content='今天中午在食堂二楼吃饭时发现一张校园卡，已交给工作人员。',
                author_id=2,
                is_ad=False
            ),
            ForumPost(
                title='体育馆附近丢卡了',
                content='在体育馆打篮球后发现校园卡不见了，可能掉在篮球场附近。',
                author_id=3,
                is_ad=False
            ),
            ForumPost(
                title='一教楼下捡到校园卡',
                content='在一教楼下捡到一张校园卡，请失主联系我。',
                author_id=1,
                is_ad=False
            ),
            ForumPost(
                title='图书馆一楼有校园卡',
                content='图书馆一楼服务台有好几张校园卡，请大家去认领。',
                author_id=2,
                is_ad=False
            ),
            ForumPost(
                title='宿舍楼下丢失校园卡',
                content='在宿舍楼下丢失了校园卡，有好心人捡到请联系我。',
                author_id=3,
                is_ad=False
            ),
            ForumPost(
                title='【广告】校园书店优惠活动',
                content='校园书店正在举办优惠活动，欢迎大家前来选购！',
                author_id=3,
                is_ad=True
            ),
            ForumPost(
                title='建议增加更多校园卡找回点',
                content='希望学校能在更多地点设置校园卡找回点，比如各个食堂、宿舍楼下等，这样能更方便同学们找回丢失的校园卡。',
                author_id=1,
                is_advice=True
            ),
            ForumPost(
                title='反馈：系统使用体验很好',
                content='这个校园卡管理系统真的很实用，界面简洁，功能齐全。希望能继续保持和改进！',
                author_id=2,
                is_advice=True
            ),
        ]
        
        for post in test_posts:
            db.session.add(post)
        
        # 创建测试奖励
        test_rewards = [
            Reward(
                name='优惠券',
                description='学生福利，在校内购买商品时可使用',
                points_required=20
            ),
            Reward(
                name='精美笔记本',
                description='高质量笔记本，适合学习使用',
                points_required=50
            ),
            Reward(
                name='校园文化衫',
                description='舒适的校园文化衫，展现学校风采',
                points_required=100
            ),
            Reward(
                name='蓝牙耳机',
                description='高品质蓝牙耳机，享受音乐时光',
                points_required=200
            ),
            Reward(
                name='移动电源',
                description='大容量移动电源，随时随地充电',
                points_required=150
            ),
        ]
        
        for reward in test_rewards:
            db.session.add(reward)
        
        # 提交所有更改
        db.session.commit()
        print("测试数据初始化完成！")
        print("测试用户:")
        print("- 学号: 2021001, 姓名: 张三, 密码: 123456, 积分: 100")
        print("- 学号: 2021002, 姓名: 李四, 密码: 123456, 积分: 50")
        print("- 学号: 2021003, 姓名: 王五, 密码: 123456, 积分: 200")

if __name__ == '__main__':
    init_test_data()

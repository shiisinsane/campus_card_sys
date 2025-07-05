# models.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    full_name = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    points = db.Column(db.Integer, default=0)
    
class CampusCard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    card_number = db.Column(db.String(20), unique=True, nullable=False)
    student_id = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='normal')  # normal/found/get
    found_location = db.Column(db.String(100))
    found_time = db.Column(db.DateTime)
    handler_option = db.Column(db.Integer)  # 1:自行联系 2:放卡处
    photo_url = db.Column(db.String(200))
    contact = db.Column(db.String(20))  # 联系方式（手机号）
    is_matched = db.Column(db.Boolean, default=False)
    select_loc = db.Column(db.String(100))  # AI分析出的标准地点名称
    
class ForumPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    is_ad = db.Column(db.Boolean, default=False)  # 是否为广告
    is_advice = db.Column(db.Boolean, default=False)  # 是否为建议帖
    
class Reward(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    points_required = db.Column(db.Integer)
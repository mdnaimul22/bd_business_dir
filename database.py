from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
import datetime

class ExtendedSQLAlchemy(SQLAlchemy):
    """
    Extends standard SQLAlchemy to include helper methods 
    required by the existing application logic.
    """
    
    def get_all_categories(self):
        cats = Category.query.order_by(Category.id).all()
        return [c.to_dict() for c in cats]

    def add_category(self, name, name_english=''):
        existing = Category.query.filter_by(name=name).first()
        if existing:
            return existing.id
        new_cat = Category(name=name, name_english=name_english)
        self.session.add(new_cat)
        self.session.commit()
        return new_cat.id

    def get_all_shops(self, limit=100, offset=0):
        shops = Shop.query.order_by(Shop.id).limit(limit).offset(offset).all()
        return [s.to_dict() for s in shops]

    def get_shops_count(self):
        return Shop.query.count()

    def get_shop_by_id(self, shop_id):
        shop = Shop.query.get(shop_id)
        return shop.to_dict() if shop else None

    def get_shops_by_category(self, category_id):
        shops = Shop.query.filter_by(category_id=category_id).order_by(Shop.id).all()
        return [s.to_dict() for s in shops]

    def search_shops(self, query):
        search = f"%{query}%"
        shops = Shop.query.join(Category, isouter=True).filter(
            or_(
                Shop.name.ilike(search),
                Shop.mobile.ilike(search),
                Shop.address.ilike(search),
                Shop.products.ilike(search),
                Category.name.ilike(search)
            )
        ).order_by(Shop.name).limit(100).all()
        return [s.to_dict() for s in shops]

    def add_shop(self, data):
        new_shop = Shop(
            category_id=data.get('category_id'),
            serial_no=data.get('serial_no'),
            name=data.get('name'),
            proprietor=data.get('proprietor'),
            address=data.get('address'),
            mobile=data.get('mobile'),
            transaction_status=data.get('transaction_status'),
            whatsapp=data.get('whatsapp'),
            email_web=data.get('email_web'),
            products=data.get('products')
        )
        self.session.add(new_shop)
        self.session.commit()
        return new_shop.id

    def update_shop(self, shop_id, data):
        shop = Shop.query.get(shop_id)
        if not shop:
            return False
        
        shop.category_id = data.get('category_id')
        shop.serial_no = data.get('serial_no')
        shop.name = data.get('name')
        shop.proprietor = data.get('proprietor')
        shop.address = data.get('address')
        shop.mobile = data.get('mobile')
        shop.transaction_status = data.get('transaction_status')
        shop.whatsapp = data.get('whatsapp')
        shop.email_web = data.get('email_web')
        shop.products = data.get('products')
        shop.updated_at = datetime.datetime.now()
        
        self.session.commit()
        return True

    def delete_shop(self, shop_id):
        shop = Shop.query.get(shop_id)
        if shop:
            self.session.delete(shop)
            self.session.commit()
            return True
        return False

db = ExtendedSQLAlchemy()

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    name_english = db.Column(db.String(100))
    shops = db.relationship('Shop', backref='category', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'name_english': self.name_english
        }

class Shop(db.Model):
    __tablename__ = 'shops'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    serial_no = db.Column(db.String(50))
    name = db.Column(db.String(200))
    proprietor = db.Column(db.String(100))
    address = db.Column(db.Text)
    mobile = db.Column(db.String(100))
    transaction_status = db.Column(db.String(100))
    whatsapp = db.Column(db.String(50))
    email_web = db.Column(db.String(100))
    products = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else '',
            'category_name_english': self.category.name_english if self.category else '',
            'serial_no': self.serial_no,
            'name': self.name,
            'proprietor': self.proprietor,
            'address': self.address,
            'mobile': self.mobile,
            'transaction_status': self.transaction_status,
            'whatsapp': self.whatsapp,
            'email_web': self.email_web,
            'products': self.products,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

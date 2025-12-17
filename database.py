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

    def get_all_shops(self, limit=100000, offset=0):
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
        ).order_by(Shop.name).limit(10000).all()
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

    def import_from_json(self, json_path):
        import json
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Clear existing data
        Shop.query.delete()
        Category.query.delete()
        
        # Reset sequences (optional but good for specific IDs)
        try:
            self.session.execute(db.text("DELETE FROM sqlite_sequence WHERE name='shops' OR name='categories'"))
        except Exception:
            pass # Table might not exist yet

        # Insert categories
        for cat in data['categories']:
            new_cat = Category(
                id=cat['id'],
                name=cat['name'],
                name_english=cat.get('name_english', '')
            )
            self.session.add(new_cat)
        
        self.session.flush()

        # Insert shops
        for shop in data['shops']:
            new_shop = Shop(
                category_id=shop.get('category_id'),
                serial_no=shop.get('serial_no', ''),
                name=shop.get('name', ''),
                proprietor=shop.get('proprietor', ''),
                address=shop.get('address', ''),
                mobile=shop.get('mobile', ''),
                transaction_status=shop.get('transaction_status', ''),
                whatsapp=shop.get('whatsapp', ''),
                email_web=shop.get('email_web', ''),
                products=shop.get('products', '')
            )
            self.session.add(new_shop)
        
        self.session.commit()
        return len(data['categories']), len(data['shops'])

db = ExtendedSQLAlchemy()

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(10000), nullable=False)
    name_english = db.Column(db.String(10000))
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
    serial_no = db.Column(db.String(5000))
    name = db.Column(db.String(20000))
    proprietor = db.Column(db.String(10000))
    address = db.Column(db.Text)
    mobile = db.Column(db.String(10000))
    transaction_status = db.Column(db.String(10000))
    whatsapp = db.Column(db.String(5000))
    email_web = db.Column(db.String(10000))
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

if __name__ == '__main__':
    from app import app, db as app_db
    import os
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, 'shops_data.json')
    
    if os.path.exists(json_path):
        print("Found shops_data.json, importing...")
        with app.app_context():
            app_db.create_all() # Ensure tables exist
            cat_count, shop_count = app_db.import_from_json(json_path)
            print(f"Successfully imported {cat_count} categories and {shop_count} shops.")
    else:
        print("Error: shops_data.json not found.")
        print("Please run 'python odt_parser.py' first to generate the data.")

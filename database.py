from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
import datetime

class ExtendedSQLAlchemy(SQLAlchemy):
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
        from search_engine import normalize_text, tokenize, calculate_score
        from sqlalchemy.orm import joinedload
        from semantic_search import SemanticSearch
        
        if not query:
            return []
            
        # Pre-process query
        normalized_query = normalize_text(query)
        query_tokens = tokenize(query)
        
        if not normalized_query:
            return []
            
        semantic_search = SemanticSearch()
        semantic_results = semantic_search.search(query)
        
        semantic_scores = {r['shop_id']: r['score'] * 100 for r in semantic_results} # Scale up 0-1 to 0-100 logic
            
        # Fetch all shops with eager loaded tags to avoid N+1 query problem
        shops = Shop.query.options(
             joinedload(Shop.shop_tags).joinedload(ShopTag.tag)
        ).all()
        
        scored_shops = []
        for shop in shops:
            tags_data = [{'name': st.tag.name, 'name_bn': st.tag.name_bn} for st in shop.shop_tags]
            
            search_data = {
                'name': shop.name,
                'products': shop.products,
                'tags': tags_data
            }
            
            score = calculate_score(search_data, query_tokens, normalized_query)
            
            sem_score = semantic_scores.get(shop.id, 0)
            
            if sem_score > 0:
                if score > 0:
                    score += sem_score + 20
                else:
                    if sem_score > 5:
                        score = sem_score
                        
            if score > 0:
                scored_shops.append((score, shop))
        
        scored_shops.sort(key=lambda x: x[0], reverse=True)
        
        return [item[1].to_dict() for item in scored_shops]

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
            products=data.get('products'),
            visiting_card=data.get('visiting_card')
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
        if 'visiting_card' in data:
            shop.visiting_card = data.get('visiting_card')
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

    def get_all_tags(self):
        tags = Tag.query.order_by(Tag.name).all()
        return [t.to_dict() for t in tags]

    def get_tag_by_id(self, tag_id):
        tag = Tag.query.get(tag_id)
        return tag.to_dict() if tag else None

    def add_tag(self, name, name_bn=''):
        existing = Tag.query.filter_by(name=name).first()
        if existing:
            return existing.id
        new_tag = Tag(name=name, name_bn=name_bn)
        self.session.add(new_tag)
        self.session.commit()
        return new_tag.id

    def delete_tag(self, tag_id):
        tag = Tag.query.get(tag_id)
        if tag:
            ShopTag.query.filter_by(tag_id=tag_id).delete()
            self.session.delete(tag)
            self.session.commit()
            return True
        return False

    def get_shop_tags(self, shop_id):
        shop = Shop.query.get(shop_id)
        if shop:
            return [t.to_dict() for t in shop.tags]
        return []

    def add_shop_tag(self, shop_id, tag_id):
        existing = ShopTag.query.filter_by(shop_id=shop_id, tag_id=tag_id).first()
        if existing:
            return existing.id
        new_shop_tag = ShopTag(shop_id=shop_id, tag_id=tag_id)
        self.session.add(new_shop_tag)
        self.session.commit()
        return new_shop_tag.id

    def remove_shop_tag(self, shop_id, tag_id):
        shop_tag = ShopTag.query.filter_by(shop_id=shop_id, tag_id=tag_id).first()
        if shop_tag:
            self.session.delete(shop_tag)
            self.session.commit()
            return True
        return False

    def search_shops_by_tag(self, tag_name):
        tag = Tag.query.filter(Tag.name.ilike(f'%{tag_name}%')).first()
        if not tag:
            return []
        shops = [st.shop for st in tag.shop_tags if st.shop]
        return [s.to_dict() for s in shops]

    def import_from_json(self, json_path):
        import json
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        Shop.query.delete()
        Category.query.delete()
        
        try:
            self.session.execute(db.text("DELETE FROM sqlite_sequence WHERE name='shops' OR name='categories'"))
        except Exception:
            pass

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
    visiting_card = db.Column(db.String(5000))
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    
    # Tag relationship (many-to-many via ShopTag)
    shop_tags = db.relationship('ShopTag', backref='shop', lazy=True, cascade='all, delete-orphan')
    tags = db.relationship('Tag', secondary='shop_tags', viewonly=True, lazy='dynamic')

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
            'visiting_card': self.visiting_card,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'tags': [t.to_dict() for t in self.tags] if self.tags else []
        }


class Tag(db.Model):
    """Master tag list for shop products/services"""
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500), unique=True, nullable=False, index=True)
    name_bn = db.Column(db.String(500))  # Bengali name
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)
    
    # Relationship to shops via ShopTag
    shop_tags = db.relationship('ShopTag', backref='tag', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'name_bn': self.name_bn,
            'shop_count': len(self.shop_tags) if self.shop_tags else 0
        }


class ShopTag(db.Model):
    """Many-to-many relationship between Shop and Tag"""
    __tablename__ = 'shop_tags'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id', ondelete='CASCADE'), nullable=False, index=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)
    
    __table_args__ = (db.UniqueConstraint('shop_id', 'tag_id', name='unique_shop_tag'),)

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

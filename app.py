#!/usr/bin/env python3
"""
Flask Web Application for Shop Details
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, g, send_from_directory
from database import db, Shop, Category
from sqlalchemy import or_
from flask_babel import Babel, _
import os
from werkzeug.utils import secure_filename
import uuid

# Configuration for file uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'shop_img')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)
# Secure secret key
app.config['SECRET_KEY'] = 'dev-key-please-change'
# Database configuration
import os
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'shop_details.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Babel configuration
app.config['BABEL_DEFAULT_LOCALE'] = 'bn'
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'

def get_locale():
    # Check if language is explicitly set in session (e.g. from toggle)
    if 'lang' in session:
        return session['lang']
    # Otherwise try to match best language from request headers
    return request.accept_languages.best_match(['bn', 'en'])

babel = Babel(app, locale_selector=get_locale)

db.init_app(app)

with app.app_context():
    db.create_all()
    # Auto-migrate: Add visiting_card column if it doesn't exist
    from sqlalchemy import text
    try:
        with db.engine.connect() as conn:
            conn.execute(text("SELECT visiting_card FROM shops LIMIT 1"))
    except Exception:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE shops ADD COLUMN visiting_card VARCHAR(5000)"))
            conn.commit()
            print("Migration: Added 'visiting_card' column to shops table.")


@app.context_processor
def inject_categories():
    """Make categories available to all templates"""
    return dict(categories=db.get_all_categories())

@app.template_filter('parse_contact_info')
def parse_contact_info(value):
    """Detect if contact info is email, website, or text"""
    if not value:
        return {'type': 'text', 'value': '-'}
    
    value_lower = value.lower()
    
    # Check for email
    if '@' in value and any(x in value_lower for x in ['gmail', 'yahoo', 'hotmail', 'mail']):
        return {'type': 'email', 'value': value}
    
    # Check for website
    if '.com' in value_lower or 'http' in value_lower or 'www.' in value_lower:
        return {'type': 'web', 'value': value}
        
    return {'type': 'text', 'value': value}

@app.route('/shop_img/<filename>')
def shop_img(filename):
    """Serve visiting card images from shop_img folder"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/set_lang/<lang_code>')
def set_language(lang_code):
    if lang_code in ['en', 'bn']:
        session['lang'] = lang_code
    return redirect(request.referrer or url_for('index'))

@app.route('/')
def index():
    """Home page with search"""
    query = request.args.get('q', '')
    categories = db.get_all_categories()
    
    if query:
        shops = db.search_shops(query)
    else:
        shops = db.get_all_shops(limit=20)
    
    total_shops = db.get_shops_count()
    
    return render_template('index.html', 
                         shops=shops, 
                         categories=categories,
                         query=query,
                         total_shops=total_shops)


@app.route('/shops')
def shop_list():
    """List all shops with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    
    shops = db.get_all_shops(limit=per_page, offset=offset)
    total = db.get_shops_count()
    total_pages = (total + per_page - 1) // per_page
    
    categories = db.get_all_categories()
    
    return render_template('shop_list.html',
                         shops=shops,
                         categories=categories,
                         page=page,
                         total_pages=total_pages,
                         total=total)


@app.route('/category/<int:category_id>')
def category_shops(category_id):
    """List shops in a category"""
    shops = db.get_shops_by_category(category_id)
    categories = db.get_all_categories()
    current_category = next((c for c in categories if c['id'] == category_id), None)
    
    return render_template('shop_list.html',
                         shops=shops,
                         categories=categories,
                         current_category=current_category,
                         page=1,
                         total_pages=1,
                         total=len(shops))


@app.route('/shop/<int:shop_id>')
def shop_detail(shop_id):
    """View single shop details"""
    shop = db.get_shop_by_id(shop_id)
    if not shop:
        flash('দোকান খুঁজে পাওয়া যায়নি!', 'error')
        return redirect(url_for('index'))
    
    return render_template('shop_detail.html', shop=shop)


@app.route('/shop/add', methods=['GET', 'POST'])
def add_shop():
    """Add new shop"""
    categories = db.get_all_categories()
    
    if request.method == 'POST':
        # Handle file upload
        visiting_card_filename = None
        if 'visiting_card' in request.files:
            file = request.files['visiting_card']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                visiting_card_filename = unique_filename

        category_id = request.form.get('category_id')
        new_category_name = request.form.get('new_category_name', '').strip()
        
        # Handle new category creation
        if category_id == 'new' and new_category_name:
            category_id = db.add_category(new_category_name)
        else:
            try:
                category_id = int(category_id) if category_id else None
            except ValueError:
                category_id = None
        
        shop_data = {
            'category_id': category_id,
            'serial_no': request.form.get('serial_no', ''),
            'name': request.form.get('name', ''),
            'proprietor': request.form.get('proprietor', ''),
            'address': request.form.get('address', ''),
            'mobile': request.form.get('mobile', ''),
            'transaction_status': request.form.get('transaction_status', ''),
            'whatsapp': request.form.get('whatsapp', ''),
            'email_web': request.form.get('email_web', ''),
            'products': request.form.get('products', ''),
            'visiting_card': visiting_card_filename
        }
        
        if not shop_data['name']:
            flash('প্রতিষ্ঠানের নাম আবশ্যক!', 'error')
            return render_template('shop_form.html', categories=categories, shop=shop_data, action='add')
        
        shop_id = db.add_shop(shop_data)
        flash('দোকান সফলভাবে যোগ করা হয়েছে!', 'success')
        return redirect(url_for('shop_detail', shop_id=shop_id))
    
    return render_template('shop_form.html', categories=categories, shop={}, action='add')


@app.route('/shop/edit/<int:shop_id>', methods=['GET', 'POST'])
def edit_shop(shop_id):
    """Edit existing shop"""
    shop = db.get_shop_by_id(shop_id)
    if not shop:
        flash('দোকান খুঁজে পাওয়া যায়নি!', 'error')
        return redirect(url_for('index'))
    
    categories = db.get_all_categories()
    
    if request.method == 'POST':
        # Handle file upload
        visiting_card_filename = None
        if 'visiting_card' in request.files:
            file = request.files['visiting_card']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                visiting_card_filename = unique_filename

        category_id = request.form.get('category_id')
        new_category_name = request.form.get('new_category_name', '').strip()
        
        # Handle new category creation
        if category_id == 'new' and new_category_name:
            category_id = db.add_category(new_category_name)
        else:
            try:
                category_id = int(category_id) if category_id else None
            except ValueError:
                category_id = None
                
        shop_data = {
            'category_id': category_id,
            'serial_no': request.form.get('serial_no', ''),
            'name': request.form.get('name', ''),
            'proprietor': request.form.get('proprietor', ''),
            'address': request.form.get('address', ''),
            'mobile': request.form.get('mobile', ''),
            'transaction_status': request.form.get('transaction_status', ''),
            'whatsapp': request.form.get('whatsapp', ''),
            'email_web': request.form.get('email_web', ''),
            'products': request.form.get('products', '')
        }

        if visiting_card_filename:
            shop_data['visiting_card'] = visiting_card_filename
        
        if not shop_data['name']:
            flash('প্রতিষ্ঠানের নাম আবশ্যক!', 'error')
            return render_template('shop_form.html', categories=categories, shop=shop_data, action='edit', shop_id=shop_id)
        
        db.update_shop(shop_id, shop_data)
        flash('দোকানের তথ্য সফলভাবে আপডেট করা হয়েছে!', 'success')
        return redirect(url_for('shop_detail', shop_id=shop_id))
    
    return render_template('shop_form.html', categories=categories, shop=shop, action='edit', shop_id=shop_id)


@app.route('/shop/delete/<int:shop_id>', methods=['POST'])
def delete_shop(shop_id):
    """Delete a shop with password protection"""
    # Password protection - change this password as needed
    DELETE_PASSWORD = "admin123"
    
    submitted_password = request.form.get('delete_password', '')
    if submitted_password != DELETE_PASSWORD:
        flash('পাসওয়ার্ড ভুল! ডিলিট করা যায়নি।', 'error')
        return redirect(url_for('shop_detail', shop_id=shop_id))
    
    if db.delete_shop(shop_id):
        flash('দোকান সফলভাবে মুছে ফেলা হয়েছে!', 'success')
    else:
        flash('দোকান মুছে ফেলতে সমস্যা হয়েছে!', 'error')
    
    return redirect(url_for('index'))


@app.route('/api/search')
def api_search():
    """API endpoint for search"""
    query = request.args.get('q', '')
    shops = db.search_shops(query) if query else []
    return jsonify(shops)


@app.route('/api/shops')
def api_shops():
    """API endpoint for all shops"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    offset = (page - 1) * per_page
    
    shops = db.get_all_shops(limit=per_page, offset=offset)
    total = db.get_shops_count()
    
    return jsonify({
        'shops': shops,
        'total': total,
        'page': page,
        'per_page': per_page
    })



@app.route('/about-us')
def about():
    """About Us page"""
    return render_template('about.html')


@app.route('/our-services')
def services():
    """Services page"""
    return render_template('services.html')

@app.route('/services/<service_alias>')
def service_detail(service_alias):
    """Dynamic Service Detail Page"""
    # Simply render the specific template for the requested service
    try:
        return render_template(f'service_page/{service_alias}.html')
    except Exception:
        # Fallback if template doesn't exist
        return redirect(url_for('services'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5020)

#!/usr/bin/env python3
"""
Flask Web Application for Shop Details
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from database import ShopDatabase
import os

app = Flask(__name__)
app.secret_key = 'shop_details_secret_key_2024'

# Initialize database
db = ShopDatabase()


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
        
        if not shop_data['name']:
            flash('প্রতিষ্ঠানের নাম আবশ্যক!', 'error')
            return render_template('shop_form.html', categories=categories, shop=shop_data, action='edit', shop_id=shop_id)
        
        db.update_shop(shop_id, shop_data)
        flash('দোকানের তথ্য সফলভাবে আপডেট করা হয়েছে!', 'success')
        return redirect(url_for('shop_detail', shop_id=shop_id))
    
    return render_template('shop_form.html', categories=categories, shop=shop, action='edit', shop_id=shop_id)


@app.route('/shop/delete/<int:shop_id>', methods=['POST'])
def delete_shop(shop_id):
    """Delete a shop"""
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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5020)

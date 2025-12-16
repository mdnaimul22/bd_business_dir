#!/usr/bin/env python3
"""
Database module for Shop Details application
"""

import sqlite3
import json
import os
from datetime import datetime

class ShopDatabase:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'shop_details.db')
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Initialize database schema"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create categories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                name_english TEXT
            )
        ''')
        
        # Create shops table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER,
                serial_no TEXT,
                name TEXT,
                proprietor TEXT,
                address TEXT,
                mobile TEXT,
                transaction_status TEXT,
                whatsapp TEXT,
                email_web TEXT,
                products TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        ''')
        
        # Create tags table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')
        
        # Create shop_tags junction table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shop_tags (
                shop_id INTEGER,
                tag_id INTEGER,
                PRIMARY KEY (shop_id, tag_id),
                FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
        ''')
        
        # Create indexes for search optimization
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_shops_name ON shops(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_shops_mobile ON shops(mobile)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_shops_category ON shops(category_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name)')
        
        conn.commit()
        conn.close()
    
    def import_from_json(self, json_path):
        """Import data from JSON file"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Clear existing data
        cursor.execute('DELETE FROM shop_tags')
        cursor.execute('DELETE FROM tags')
        cursor.execute('DELETE FROM shops')
        cursor.execute('DELETE FROM categories')
        
        # Insert categories
        for cat in data['categories']:
            cursor.execute(
                'INSERT INTO categories (id, name, name_english) VALUES (?, ?, ?)',
                (cat['id'], cat['name'], cat.get('name_english', ''))
            )
        
        # Insert shops and generate tags
        for shop in data['shops']:
            cursor.execute('''
                INSERT INTO shops (category_id, serial_no, name, proprietor, address, 
                                   mobile, transaction_status, whatsapp, email_web, products)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                shop.get('category_id'),
                shop.get('serial_no', ''),
                shop.get('name', ''),
                shop.get('proprietor', ''),
                shop.get('address', ''),
                shop.get('mobile', ''),
                shop.get('transaction_status', ''),
                shop.get('whatsapp', ''),
                shop.get('email_web', ''),
                shop.get('products', '')
            ))
            shop_id = cursor.lastrowid
            
            # Generate tags from various fields
            self._generate_tags(cursor, shop_id, shop)
        
        conn.commit()
        conn.close()
        
        return len(data['categories']), len(data['shops'])
    
    def _generate_tags(self, cursor, shop_id, shop):
        """Generate searchable tags for a shop"""
        tags = set()
        
        # Add category name as tag
        if shop.get('category_name'):
            tags.add(shop['category_name'].strip().lower())
        
        # Add products as tags (split by comma)
        if shop.get('products'):
            for product in shop['products'].split(','):
                product = product.strip().lower()
                if product and len(product) > 1:
                    tags.add(product)
        
        # Add mobile numbers as tags (for mobile search)
        if shop.get('mobile'):
            # Clean and add mobile numbers
            mobile_clean = shop['mobile'].replace(' ', '').replace('-', '')
            if mobile_clean:
                tags.add(mobile_clean)
                # Also add with common format
                tags.add(shop['mobile'].strip())
        
        # Add shop name words as tags
        if shop.get('name'):
            for word in shop['name'].split():
                word = word.strip().lower()
                if word and len(word) > 1:
                    tags.add(word)
        
        # Insert tags
        for tag_name in tags:
            if not tag_name:
                continue
            # Get or create tag
            cursor.execute('SELECT id FROM tags WHERE name = ?', (tag_name,))
            result = cursor.fetchone()
            if result:
                tag_id = result[0]
            else:
                cursor.execute('INSERT INTO tags (name) VALUES (?)', (tag_name,))
                tag_id = cursor.lastrowid
            
            # Link shop to tag
            try:
                cursor.execute('INSERT INTO shop_tags (shop_id, tag_id) VALUES (?, ?)',
                             (shop_id, tag_id))
            except sqlite3.IntegrityError:
                pass  # Already linked
    
    # CRUD Operations
    
    def get_all_categories(self):
        """Get all categories"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM categories ORDER BY id')
        categories = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return categories
    
    def add_category(self, name, name_english=''):
        """Add a new category"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if exists
        cursor.execute('SELECT id FROM categories WHERE name = ?', (name,))
        existing = cursor.fetchone()
        if existing:
            conn.close()
            return existing[0]
            
        cursor.execute('INSERT INTO categories (name, name_english) VALUES (?, ?)', (name, name_english))
        cat_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return cat_id
    
    def get_all_shops(self, limit=100, offset=0):
        """Get all shops with pagination"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.*, c.name as category_name, c.name_english as category_name_english
            FROM shops s
            LEFT JOIN categories c ON s.category_id = c.id
            ORDER BY s.id
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        shops = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return shops
    
    def get_shops_count(self):
        """Get total shop count"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM shops')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_shop_by_id(self, shop_id):
        """Get a single shop by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.*, c.name as category_name, c.name_english as category_name_english
            FROM shops s
            LEFT JOIN categories c ON s.category_id = c.id
            WHERE s.id = ?
        ''', (shop_id,))
        row = cursor.fetchone()
        shop = dict(row) if row else None
        conn.close()
        return shop
    
    def get_shops_by_category(self, category_id):
        """Get all shops in a category"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.*, c.name as category_name, c.name_english as category_name_english
            FROM shops s
            LEFT JOIN categories c ON s.category_id = c.id
            WHERE s.category_id = ?
            ORDER BY s.id
        ''', (category_id,))
        shops = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return shops
    
    def search_shops(self, query):
        """Search shops by tag or keyword"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query_lower = query.strip().lower()
        query_clean = query.replace(' ', '').replace('-', '')
        
        # Search in tags
        cursor.execute('''
            SELECT DISTINCT s.*, c.name as category_name, c.name_english as category_name_english
            FROM shops s
            LEFT JOIN categories c ON s.category_id = c.id
            LEFT JOIN shop_tags st ON s.id = st.shop_id
            LEFT JOIN tags t ON st.tag_id = t.id
            WHERE t.name LIKE ? 
               OR s.name LIKE ?
               OR s.mobile LIKE ?
               OR s.products LIKE ?
               OR s.address LIKE ?
               OR c.name LIKE ?
            ORDER BY s.name
            LIMIT 100
        ''', (
            f'%{query_lower}%',
            f'%{query}%',
            f'%{query_clean}%',
            f'%{query}%',
            f'%{query}%',
            f'%{query}%'
        ))
        
        shops = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return shops
    
    def add_shop(self, shop_data):
        """Add a new shop"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO shops (category_id, serial_no, name, proprietor, address,
                              mobile, transaction_status, whatsapp, email_web, products)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            shop_data.get('category_id'),
            shop_data.get('serial_no', ''),
            shop_data.get('name', ''),
            shop_data.get('proprietor', ''),
            shop_data.get('address', ''),
            shop_data.get('mobile', ''),
            shop_data.get('transaction_status', ''),
            shop_data.get('whatsapp', ''),
            shop_data.get('email_web', ''),
            shop_data.get('products', '')
        ))
        
        shop_id = cursor.lastrowid
        
        # Get category name for tags
        if shop_data.get('category_id'):
            cursor.execute('SELECT name FROM categories WHERE id = ?', (shop_data['category_id'],))
            row = cursor.fetchone()
            if row:
                shop_data['category_name'] = row[0]
        
        # Generate tags
        self._generate_tags(cursor, shop_id, shop_data)
        
        conn.commit()
        conn.close()
        
        return shop_id
    
    def update_shop(self, shop_id, shop_data):
        """Update an existing shop"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE shops SET
                category_id = ?,
                serial_no = ?,
                name = ?,
                proprietor = ?,
                address = ?,
                mobile = ?,
                transaction_status = ?,
                whatsapp = ?,
                email_web = ?,
                products = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            shop_data.get('category_id'),
            shop_data.get('serial_no', ''),
            shop_data.get('name', ''),
            shop_data.get('proprietor', ''),
            shop_data.get('address', ''),
            shop_data.get('mobile', ''),
            shop_data.get('transaction_status', ''),
            shop_data.get('whatsapp', ''),
            shop_data.get('email_web', ''),
            shop_data.get('products', ''),
            shop_id
        ))
        
        # Delete old tags
        cursor.execute('DELETE FROM shop_tags WHERE shop_id = ?', (shop_id,))
        
        # Get category name for tags
        if shop_data.get('category_id'):
            cursor.execute('SELECT name FROM categories WHERE id = ?', (shop_data['category_id'],))
            row = cursor.fetchone()
            if row:
                shop_data['category_name'] = row[0]
        
        # Regenerate tags
        self._generate_tags(cursor, shop_id, shop_data)
        
        conn.commit()
        conn.close()
        
        return cursor.rowcount > 0
    
    def delete_shop(self, shop_id):
        """Delete a shop"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Delete tag associations
        cursor.execute('DELETE FROM shop_tags WHERE shop_id = ?', (shop_id,))
        
        # Delete shop
        cursor.execute('DELETE FROM shops WHERE id = ?', (shop_id,))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success


def main():
    """Test database operations"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, 'shops_data.json')
    
    print("Initializing database...")
    db = ShopDatabase()
    
    if os.path.exists(json_path):
        print("Importing data from JSON...")
        cat_count, shop_count = db.import_from_json(json_path)
        print(f"Imported {cat_count} categories and {shop_count} shops")
    
    print(f"\nTotal categories: {len(db.get_all_categories())}")
    print(f"Total shops: {db.get_shops_count()}")
    
    # Test search
    print("\nTest search for 'আয়রন':")
    results = db.search_shops('আয়রন')
    for shop in results[:3]:
        print(f"  - {shop['name']} | {shop['mobile']}")
    
    print("\nTest search for mobile '০১৯২২':")
    results = db.search_shops('০১৯২২')
    for shop in results[:3]:
        print(f"  - {shop['name']} | {shop['mobile']}")


if __name__ == '__main__':
    main()

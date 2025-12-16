#!/usr/bin/env python3
"""
ODT Parser - Extracts shop data from shop_details.odt content.xml
"""

import xml.etree.ElementTree as ET
import json
import re
import os
import unicodedata
from zipfile import ZipFile

# Bengali to English number mapping
BENGALI_DIGITS = '০১২৩৪৫৬৭৮৯'

def normalize_text(text):
    """Normalize unicode text"""
    if not text:
        return ""
    return unicodedata.normalize('NFC', text)

def bengali_to_english_num(text):
    """Convert Bengali numerals to English"""
    for i, d in enumerate(BENGALI_DIGITS):
        text = text.replace(d, str(i))
    return text

def normalize_mobile(mobile_text):
    """Normalize mobile number to standard format"""
    # Remove spaces and special characters except digits and hyphens
    clean = re.sub(r'[^\d০-৯\-,\s]', '', mobile_text)
    return clean.strip()

def parse_odt(odt_path):
    """Parse ODT file and extract shop data"""
    
    # Extract content.xml from ODT
    content_xml_path = os.path.join(os.path.dirname(odt_path), 'extracted_odt', 'content.xml')
    
    if not os.path.exists(content_xml_path):
        # Extract from ODT if not already extracted
        with ZipFile(odt_path, 'r') as zip_ref:
            extract_dir = os.path.join(os.path.dirname(odt_path), 'extracted_odt')
            zip_ref.extractall(extract_dir)
    
    # Parse XML
    tree = ET.parse(content_xml_path)
    root = tree.getroot()
    
    # Define namespaces used in ODT
    ns = {
        'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
        'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
        'table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
    }
    
    categories_list = []
    
    # helper to extract text from a cell
    def get_cell_text(cell):
        texts = []
        for p in cell.findall('.//text:p', ns):
            if p.text: texts.append(p.text)
            for child in p:
                if child.tail: texts.append(child.tail)
        return normalize_text(" ".join(texts).strip())

    # Step 1: Scan for Index Tables to build categories_list
    print("Scanning for categories in Index tables...")
    tables = root.findall('.//table:table', ns)
    
    for table in tables:
        rows = table.findall('.//table:table-row', ns)
        if not rows: 
            continue
            
        # Check header row for "ক্যাটেগরি"
        header_cells = rows[0].findall('.//table:table-cell', ns)
        header_text = " ".join([get_cell_text(c) for c in header_cells])
        
        if "ক্যাটেগরি" in header_text and "সিরিয়াল" in header_text:
            # This is an index table
            for row in rows[1:]: # Skip header
                cells = row.findall('.//table:table-cell', ns)
                if len(cells) >= 2:
                    # Cell 0: Serial (ID), Cell 1: Name
                    cat_id_text = bengali_to_english_num(get_cell_text(cells[0]))
                    cat_name = get_cell_text(cells[1])
                    
                    # Clean up ID
                    cat_id_match = re.search(r'\d+', cat_id_text)
                    if cat_id_match and cat_name:
                        cat_id = int(cat_id_match.group())
                        # Check if already added
                        if not any(c[0] == cat_id for c in categories_list):
                            categories_list.append((cat_id, cat_name, "")) # English name empty
                            print(f"DEBUG: Found Category {cat_id}: {cat_name}")

    if not categories_list:
        print("WARNING: No dynamic categories found. Falling back to basics or manual check needed.")
    
    categories_list.sort(key=lambda x: x[0])
    print(f"Total Categories Found: {len(categories_list)}")

    categories = {}
    for serial, name_bn, name_en in categories_list:
        categories[serial] = {
            "id": serial,
            "name": normalize_text(name_bn),
            "name_english": name_en # This will be empty for now, can be added later
        }
    
    shops = []
    current_category_id = None
    current_category_name = None
    
    # Map for easy lookup
    cat_map = {c[1]: c[0] for c in categories_list} # Name -> ID
    
    for table in tables:
        rows = table.findall('.//table:table-row', ns)
        
        for row in rows:
            cells = row.findall('.//table:table-cell', ns)
            row_text = [] # simple text list
            full_row_text = ""
            
            for cell in cells:
                cell_text = get_cell_text(cell)
                if cell_text:
                    row_text.append(cell_text)
            
            full_row_text = " ".join(row_text)
            
            # Skip empty rows
            if not full_row_text.strip():
                continue

            # Check for Category Headers (Single cell or specific text)
            # Match against our dynamic list
            matched_cat = False
            
            # Heuristic 1: Exact or fuzzy match with known category names
            # We check if the row text *contains* a collected category name
            # or if it *is* the category name
            
            cleaned_row_text = bengali_to_english_num(full_row_text)
            
            for cat_id, cat_name, _ in categories_list:
                # Check for "ID CategoryName" pattern or just "CategoryName"
                # e.g. "3 Old SS" or "Old MS"
                
                # Rigid check: if line is short and matches category name
                if len(full_row_text) < 100:
                    if cat_name in full_row_text:
                         # Verify it's not a shop row (shop rows usually have more columns or digits)
                        has_mobile = re.search(r'\d{5,}', cleaned_row_text)
                        if not has_mobile:
                            current_category_id = cat_id
                            current_category_name = cat_name
                            matched_cat = True
                            # print(f"DEBUG: Switched to Category: {cat_name}")
                            break
            
            if matched_cat:
                continue

            # Check if this row is a Shop Data Header
            # Must look like: Serial No | Name | Proprietor ...
            if len(cells) >= 5:
                header_text = row_text
                
                # Verify header keywords
                if ('সিরিয়াল' in header_text or 'নং' in header_text) and \
                   ('প্রতিষ্ঠান' in header_text or 'মোবাইল' in header_text or 'প্রোপাইটার' in header_text):
                    # Identified shop table header. 
                    # Note: We don't need to do anything special, just ensures we don't treat it as valid shop data below
                    continue

            # Process potential shop entry
            # Shop entry is valid if:
            # 1. We have enough columns (let's say 4+)
            # 2. It doesn't look like a header
            # 3. It has a Serial Number (usually) OR has a valid Mobile Number
            
            if len(cells) >= 5:
                cell_texts = []
                for cell in cells:
                    t = ""
                    for p in cell.findall('.//text:p', ns):
                        if p.text: t += p.text + " "
                        for c in p:
                            if c.text: t += c.text + " "
                            if c.tail: t += c.tail + " "
                    cell_texts.append(normalize_text(t.strip()))
                
                # Check if it's a header repetition
                if 'সিরিয়াল' in cell_texts[0] or 'প্রতিষ্ঠান' in cell_texts[1]:
                    continue
                    
                # Robustness: Check if it looks like a shop
                # Needs name (index 1) and maybe mobile (index 4) or address (index 3)
                if len(cell_texts[1]) > 0:
                    shop = {
                        "serial_no": cell_texts[0] if len(cell_texts) > 0 else "",
                        "name": cell_texts[1] if len(cell_texts) > 1 else "",
                        "proprietor": cell_texts[2] if len(cell_texts) > 2 else "",
                        "address": cell_texts[3] if len(cell_texts) > 3 else "",
                        "mobile": normalize_mobile(cell_texts[4]) if len(cell_texts) > 4 else "",
                        "transaction_status": cell_texts[5] if len(cell_texts) > 5 else "",
                        "whatsapp": cell_texts[6] if len(cell_texts) > 6 else "",
                        "email_web": cell_texts[7] if len(cell_texts) > 7 else "",
                        "products": cell_texts[8] if len(cell_texts) > 8 else "",
                        "category_id": current_category_id,
                        "category_name": current_category_name
                    }
                    shops.append(shop)

    return {
        "categories": list(categories.values()),
        "shops": shops
    }

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    odt_path = os.path.join(script_dir, 'shop_details.odt')
    
    print("Parsing ODT file...")
    data = parse_odt(odt_path)
    
    print(f"Found {len(data['categories'])} categories")
    print(f"Found {len(data['shops'])} shops")
    
    # Check category coverage
    shops_with_cat = sum(1 for s in data['shops'] if s['category_id'])
    print(f"Shops with category: {shops_with_cat} / {len(data['shops'])}")
    
    # Save to JSON
    output_path = os.path.join(script_dir, 'shops_data.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Data saved to {output_path}")

if __name__ == '__main__':
    main()

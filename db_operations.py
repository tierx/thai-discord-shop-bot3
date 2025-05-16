import json
import os
from datetime import datetime
from mongodb_config import (
    products_collection,
    countries_collection, 
    history_collection,
    configs_collection
)

# ================================
# ฟังก์ชันจัดการข้อมูลประเทศ
# ================================

def load_countries():
    """โหลดข้อมูลประเทศจาก MongoDB"""
    country_data = countries_collection.find_one({})
    if country_data:
        return country_data.get("countries", []), country_data.get("country_names", {}), country_data.get("country_emojis", {}), country_data.get("country_codes", {})
    return [], {}, {}, {}

def save_countries(countries, country_names, country_emojis, country_codes):
    """บันทึกข้อมูลประเทศลง MongoDB"""
    country_data = {
        "countries": countries,
        "country_names": country_names,
        "country_emojis": country_emojis,
        "country_codes": country_codes
    }
    
    # ตรวจสอบว่ามีข้อมูลอยู่แล้วหรือไม่
    existing_data = countries_collection.find_one({})
    if existing_data:
        countries_collection.replace_one({"_id": existing_data["_id"]}, country_data)
    else:
        countries_collection.insert_one(country_data)

def add_country(code, name, emoji=""):
    """เพิ่มประเทศใหม่
    
    Args:
        code (str): รหัสประเทศ (เช่น 'korea', 'china')
        name (str): ชื่อประเทศเป็นภาษาไทย (เช่น 'เกาหลี', 'จีน')
        emoji (str, optional): อีโมจิประเทศ
        
    Returns:
        bool or tuple: True ถ้าสำเร็จ, หรือ (False, error_message) ถ้าล้มเหลวพร้อมข้อความผิดพลาด
    """
    # โหลดข้อมูลประเทศปัจจุบัน
    countries, country_names, country_emojis, country_codes = load_countries()
    
    # ตรวจสอบว่ามีประเทศนี้แล้วหรือไม่
    if code in countries or code in country_codes.values():
        return (False, f"มีประเทศรหัส {code} อยู่แล้ว")
    
    # เพิ่มประเทศใหม่
    countries.append(code)
    country_names[code] = name
    if emoji:
        country_emojis[code] = emoji
    
    # บันทึกข้อมูล
    save_countries(countries, country_names, country_emojis, country_codes)
    return True

def edit_country(code, new_name=None, new_emoji=None):
    """แก้ไขข้อมูลประเทศ
    
    Args:
        code (str): รหัสประเทศที่ต้องการแก้ไข
        new_name (str, optional): ชื่อใหม่สำหรับประเทศ
        new_emoji (str, optional): อีโมจิใหม่สำหรับประเทศ
        
    Returns:
        bool: True ถ้าสำเร็จ, False ถ้าไม่พบประเทศ
    """
    # โหลดข้อมูลประเทศปัจจุบัน
    countries, country_names, country_emojis, country_codes = load_countries()
    
    # ตรวจสอบว่ามีประเทศนี้หรือไม่
    if code not in countries and code not in country_names:
        return False
    
    # แก้ไขข้อมูล
    if new_name:
        country_names[code] = new_name
    if new_emoji:
        country_emojis[code] = new_emoji
    
    # บันทึกข้อมูล
    save_countries(countries, country_names, country_emojis, country_codes)
    return True

def remove_country(code):
    """ลบประเทศและสินค้าทั้งหมดในประเทศนั้น
    
    Args:
        code (str): รหัสประเทศที่ต้องการลบ
        
    Returns:
        bool or tuple: True ถ้าสำเร็จ, หรือ (False, error_message) ถ้าล้มเหลวพร้อมข้อความผิดพลาด
    """
    # โหลดข้อมูลประเทศปัจจุบัน
    countries, country_names, country_emojis, country_codes = load_countries()
    
    # ตรวจสอบว่ามีประเทศนี้หรือไม่
    if code not in countries and code not in country_names:
        return (False, f"ไม่พบประเทศรหัส {code}")
    
    # ลบประเทศออกจากรายการ
    if code in countries:
        countries.remove(code)
    if code in country_names:
        del country_names[code]
    if code in country_emojis:
        del country_emojis[code]
    
    # ลบรหัสประเทศเก่า (ถ้ามี)
    for k, v in list(country_codes.items()):
        if v == code:
            del country_codes[k]
    
    # บันทึกข้อมูลประเทศ
    save_countries(countries, country_names, country_emojis, country_codes)
    
    # ลบสินค้าทั้งหมดในประเทศนี้
    products_collection.delete_many({"country": code})
    
    return True

# ================================
# ฟังก์ชันจัดการข้อมูลสินค้า
# ================================

def load_products(country=None, category=None):
    """โหลดข้อมูลสินค้าจาก MongoDB ตามประเทศและหมวดหมู่
    
    Args:
        country (str, optional): รหัสประเทศ (1, 2, 3, 4, 5) หรือรหัสเก่า (thailand, japan, usa). Default: None.
        category (str, optional): รหัสหมวดหมู่ (money, weapon, item, etc). Default: None.
        
    Returns:
        list: รายการสินค้าที่ตรงกับเงื่อนไข
    """
    query = {}
    
    # กรองตามประเทศ (ถ้าระบุ)
    if country:
        query["country"] = country
    
    # กรองตามหมวดหมู่ (ถ้าระบุ)
    if category:
        query["category"] = category
    
    # ดึงข้อมูลจาก MongoDB
    products = list(products_collection.find(query))
    
    # แปลง _id เป็น str เพื่อให้สามารถแปลงเป็น JSON ได้
    for product in products:
        if "_id" in product:
            product["_id"] = str(product["_id"])
    
    return products

def save_product(product):
    """บันทึกสินค้าเดียวลง MongoDB
    
    Args:
        product: ข้อมูลสินค้าที่ต้องการบันทึก ต้องมีฟิลด์ name, price, emoji, country และ category
        
    Returns:
        bool: True ถ้าสำเร็จ
    """
    # ตรวจสอบว่าสินค้ามีข้อมูลครบถ้วน
    required_fields = ["name", "price", "emoji", "country", "category"]
    for field in required_fields:
        if field not in product:
            return False
    
    # ตรวจสอบว่ามีสินค้านี้อยู่แล้วหรือไม่
    existing_product = products_collection.find_one({
        "name": product["name"],
        "country": product["country"],
        "category": product["category"]
    })
    
    if existing_product:
        # อัปเดตสินค้าที่มีอยู่แล้ว
        product_id = existing_product["_id"]
        products_collection.replace_one({"_id": product_id}, product)
    else:
        # เพิ่มสินค้าใหม่
        products_collection.insert_one(product)
    
    return True

def batch_add_products(products_data):
    """เพิ่มสินค้าหลายรายการในครั้งเดียว
    
    Args:
        products_data: รายการข้อมูลสินค้าที่ต้องการเพิ่ม แต่ละรายการต้องมีฟิลด์ name, price, emoji, country และ category
        
    Returns:
        int: จำนวนสินค้าที่เพิ่มสำเร็จ
    """
    success_count = 0
    
    for product in products_data:
        if save_product(product):
            success_count += 1
    
    return success_count

def remove_product(name, category=None, country=None):
    """ลบสินค้า
    
    Args:
        name (str): ชื่อสินค้าที่ต้องการลบ
        category (str, optional): หมวดหมู่ของสินค้า (ถ้าระบุจะลบเฉพาะในหมวดนี้)
        country (str, optional): ประเทศของสินค้า (ถ้าระบุจะลบเฉพาะในประเทศนี้)
        
    Returns:
        bool: True ถ้าสำเร็จ, False ถ้าไม่พบสินค้า
    """
    query = {"name": name}
    
    # เพิ่มเงื่อนไขการค้นหา
    if category:
        query["category"] = category
    if country:
        query["country"] = country
    
    # ลบสินค้า
    result = products_collection.delete_many(query)
    
    return result.deleted_count > 0

def update_product(name, country, new_emoji=None, new_name=None, new_price=None, new_category=None, new_country=None):
    """อัปเดตข้อมูลสินค้า
    
    Args:
        name (str): ชื่อสินค้าที่ต้องการแก้ไข
        country (str): ประเทศของสินค้า
        new_emoji (str, optional): อีโมจิใหม่
        new_name (str, optional): ชื่อใหม่
        new_price (float, optional): ราคาใหม่
        new_category (str, optional): หมวดหมู่ใหม่
        new_country (str, optional): ประเทศใหม่
        
    Returns:
        bool: True ถ้าสำเร็จ, False ถ้าไม่พบสินค้า
    """
    # ค้นหาสินค้า
    product = products_collection.find_one({"name": name, "country": country})
    
    if not product:
        return False
    
    # สร้างข้อมูลที่จะอัปเดต
    updates = {}
    if new_emoji:
        updates["emoji"] = new_emoji
    if new_name:
        updates["name"] = new_name
    if new_price is not None:
        updates["price"] = new_price
    if new_category:
        updates["category"] = new_category
    if new_country:
        updates["country"] = new_country
    
    # ถ้าไม่มีข้อมูลที่จะอัปเดต
    if not updates:
        return True
    
    # อัปเดตสินค้า
    products_collection.update_one({"_id": product["_id"]}, {"$set": updates})
    
    return True

def clear_category_products(category, country=None):
    """ลบสินค้าทั้งหมดในหมวดหมู่
    
    Args:
        category (str): หมวดหมู่ที่ต้องการลบ
        country (str, optional): ประเทศที่ต้องการลบ (ถ้าไม่ระบุจะลบในทุกประเทศ)
        
    Returns:
        int: จำนวนสินค้าที่ลบได้
    """
    query = {"category": category}
    
    # เพิ่มเงื่อนไขประเทศ (ถ้าระบุ)
    if country:
        query["country"] = country
    
    # ลบสินค้า
    result = products_collection.delete_many(query)
    
    return result.deleted_count

def delete_all_products():
    """ลบสินค้าทั้งหมดจากทุกหมวดหมู่ในทุกประเทศ
    
    Returns:
        int: จำนวนสินค้าทั้งหมดที่ถูกลบ
    """
    result = products_collection.delete_many({})
    return result.deleted_count

def add_no_product_placeholders():
    """เพิ่มสินค้า placeholder 'ไม่มีสินค้า' ในหมวดหมู่ที่ว่างเปล่า
    
    Returns:
        int: จำนวนสินค้า placeholder ที่เพิ่ม
    """
    from shopbot import COUNTRIES, CATEGORIES
    
    placeholder_count = 0
    
    # ตรวจสอบแต่ละประเทศและหมวดหมู่
    for country in COUNTRIES:
        for category in CATEGORIES:
            # ตรวจสอบว่ามีสินค้าในหมวดหมู่นี้หรือไม่
            product_count = products_collection.count_documents({
                "country": country,
                "category": category
            })
            
            # ถ้าไม่มีสินค้า ให้เพิ่ม placeholder
            if product_count == 0:
                placeholder = {
                    "name": "ไม่มีสินค้า",
                    "price": 0,
                    "emoji": "❌",
                    "country": country,
                    "category": category
                }
                products_collection.insert_one(placeholder)
                placeholder_count += 1
    
    return placeholder_count

# ================================
# ฟังก์ชันจัดการประวัติการซื้อ
# ================================

def log_purchase(user, items, total_price):
    """บันทึกประวัติการซื้อใน MongoDB
    
    Args:
        user: ข้อมูลผู้ใช้ที่ซื้อสินค้า
        items: รายการสินค้าที่ซื้อ
        total_price: ราคารวม
        
    Returns:
        str: ID ของรายการที่บันทึก
    """
    # สร้างข้อมูลประวัติการซื้อ
    purchase_data = {
        "user_id": str(user.id),
        "user_name": str(user),
        "items": items,
        "total_price": total_price,
        "timestamp": datetime.now().isoformat()
    }
    
    # บันทึกลง MongoDB
    result = history_collection.insert_one(purchase_data)
    
    return str(result.inserted_id)

def get_purchase_history(limit=5):
    """ดึงประวัติการซื้อล่าสุด
    
    Args:
        limit (int): จำนวนรายการที่ต้องการดึง
        
    Returns:
        list: รายการประวัติการซื้อล่าสุด
    """
    # ดึงข้อมูลล่าสุดตามจำนวนที่ระบุ
    history = list(history_collection.find().sort("timestamp", -1).limit(limit))
    
    # แปลง _id เป็น str เพื่อให้สามารถแปลงเป็น JSON ได้
    for record in history:
        if "_id" in record:
            record["_id"] = str(record["_id"])
    
    return history

# ================================
# ฟังก์ชันจัดการการตั้งค่า
# ================================

def load_qrcode_url():
    """โหลด URL QR code จาก MongoDB
    
    Returns:
        str: URL ของ QR code
    """
    config = configs_collection.find_one({"config_type": "qrcode"})
    return config.get("url", "https://promptpay.io/1234567890") if config else "https://promptpay.io/1234567890"

def save_qrcode_url(url):
    """บันทึก URL QR code ลง MongoDB
    
    Args:
        url (str): URL ของ QR code
        
    Returns:
        bool: True ถ้าสำเร็จ
    """
    # ตรวจสอบว่ามีการตั้งค่าอยู่แล้วหรือไม่
    config = configs_collection.find_one({"config_type": "qrcode"})
    
    if config:
        # อัปเดตการตั้งค่าที่มีอยู่
        configs_collection.update_one(
            {"_id": config["_id"]},
            {"$set": {"url": url}}
        )
    else:
        # สร้างการตั้งค่าใหม่
        configs_collection.insert_one({
            "config_type": "qrcode",
            "url": url
        })
    
    return True

def load_thank_you_message():
    """โหลดข้อความขอบคุณจาก MongoDB
    
    Returns:
        str: ข้อความขอบคุณ
    """
    config = configs_collection.find_one({"config_type": "thank_you"})
    default_message = "✅ ขอบคุณสำหรับการสั่งซื้อ! สินค้าจะถูกส่งถึงคุณเร็วๆ นี้"
    return config.get("message", default_message) if config else default_message

def save_thank_you_message(message):
    """บันทึกข้อความขอบคุณลง MongoDB
    
    Args:
        message (str): ข้อความขอบคุณ
        
    Returns:
        bool: True ถ้าสำเร็จ
    """
    # ตรวจสอบว่ามีการตั้งค่าอยู่แล้วหรือไม่
    config = configs_collection.find_one({"config_type": "thank_you"})
    
    if config:
        # อัปเดตการตั้งค่าที่มีอยู่
        configs_collection.update_one(
            {"_id": config["_id"]},
            {"$set": {"message": message}}
        )
    else:
        # สร้างการตั้งค่าใหม่
        configs_collection.insert_one({
            "config_type": "thank_you",
            "message": message
        })
    
    return True
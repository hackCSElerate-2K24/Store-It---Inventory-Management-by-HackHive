import sqlite3
from flask import redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE = 'inventory.db'

def get_db():
    conn = sqlite3.connect(DATABASE, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('PRAGMA journal_mode=WAL;')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS items (
        itemID INTEGER PRIMARY KEY AUTOINCREMENT,
        itemBarcode TEXT NOT NULL UNIQUE,
        itemName TEXT NOT NULL,
        itemCategory TEXT NOT NULL,
        itemCost DOUBLE NOT NULL,
        itemStock INTEGER NOT NULL,
        userID INTEGER,  -- Add this line to associate items with a user
        FOREIGN KEY (userID) REFERENCES users(userID)  -- Link to users table
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        userID INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL,
        phone_num TEXT NOT NULL,  -- Updated to TEXT for phone number
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'user'
    )
    ''')

    conn.commit()
    conn.close()


def add_item(itembarcode, itemname, itemcategory, itemcost, itemstock):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM items WHERE itemBarcode = ?', (itembarcode,))
        existing_item = cursor.fetchone()

        if existing_item:
            flash(f"Item with barcode {itembarcode} already exists.", "danger")
            return redirect(url_for('add_item_view'))
        cursor.execute('''
        INSERT INTO items(itemBarcode, itemName, itemCategory, itemCost, itemStock)
        VALUES (?, ?, ?, ?, ?)''', (itembarcode, itemname, itemcategory, itemcost, itemstock))

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_items():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT items.*, users.username, users.email, users.phone_num
    FROM items
    LEFT JOIN users ON items.userID = users.userID
    ''')

    items = cursor.fetchall()
    conn.close()

    items_dict = []
    for item in items:
        items_dict.append({
            'itemID': item[0],
            'itemBarcode': item[1],
            'itemName': item[2],
            'itemCategory': item[3],
            'itemCost': item[4],
            'itemStock': item[5],
            'userID': item[6],
            'username': item[7],
            'userEmail': item[8],
            'userPhone': item[9]
        })
    return items_dict


def get_item_by_barcode(barcode):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM items WHERE itemBarcode = ?', (barcode,))
    item = cursor.fetchone()
    conn.close()
    return item


def update_item(barcode, item_name, item_category, item_cost, item_stock):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE items 
    SET itemName = ?, itemCategory = ?, itemCost = ?, itemStock = ?
    WHERE itemBarcode = ?
    ''', (item_name, item_category, item_cost, item_stock, barcode))

    conn.commit()
    conn.close()


def add_user(username, email, phone_num, password):
    conn = get_db()
    cursor = conn.cursor()
    password_hash = generate_password_hash(password)
    cursor.execute(''' 
    INSERT INTO users(username, email, phone_num, password_hash, role) 
    VALUES (?, ?, ?, ?, ?) 
    ''', (username, email, phone_num, password_hash, 'user'))

    conn.commit()
    conn.close()


def get_user_by_username(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    return user


def verify_user_password(user, password):
    return check_password_hash(user['password_hash'], password)

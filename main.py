from flask import Flask, render_template, request, redirect, url_for, Response, session, flash, jsonify
import cv2
import time
from pyzbar.pyzbar import decode
from db import get_db, get_item_by_barcode, add_item, get_items, init_db, get_user_by_username, verify_user_password, \
    add_user, update_item
app = Flask(__name__)
from google.generativeai import genai
app.secret_key = 'a_sneaky_key_hahaha!'
init_db()
DATABASE = 'inventory.db'

video_capture = cv2.VideoCapture(0)

last_barcode_time = time.time()
barcode_data = None


### -- GENERATING BARCODE SCAN -- ###
def process_frame(frame):
    global last_barcode_time, barcode_data
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    detected_barcodes = decode(gray_frame)

    if detected_barcodes:
        for barcode in detected_barcodes:
            new_barcode_data = barcode.data.decode('utf-8')
            print(f"Detected barcode: {new_barcode_data}")
            if new_barcode_data != barcode_data or time.time() - last_barcode_time > 1:
                barcode_data = new_barcode_data
                last_barcode_time = time.time()
    return barcode_data, frame


@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            success, frame = video_capture.read()
            if not success:
                print("Failed to read from video capture")
                break
            barcode_data, frame = process_frame(frame)
            time.sleep(0.1)
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n\r\n')

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/barcode_feed')
def barcode_feed():
    def generate():
        global barcode_data
        while True:
            time.sleep(0.1)
            if barcode_data:
                yield f"data:{barcode_data}\n\n"

    return Response(generate(), mimetype="text/event-stream")


### -- IMPLEMENTING BASIC PAGE ROUTES -- ###
@app.route('/')
def home():
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user_by_username(username)
        if user and verify_user_password(user, password):
            session['logged_in'] = True
            session['user_id'] = user['userID']
            session['username'] = user['username']
            session['role'] = user['role']
            flash("Login successful", "success")

            print(f"Session set for user: {session['username']} with role: {session['role']}")

            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash("Invalid username or password", "danger")
            return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/user_dashboard')
def user_dashboard():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM items")
    items = cursor.fetchall()
    conn.close()
    return render_template('user_dashboard.html', items=items)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone_num = request.form['phone_num']  # Collecting phone number
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash("Passwords do not match", "danger")
            return redirect(url_for('signup'))

        user = get_user_by_username(username)
        if user:
            flash("Username already exists", "danger")
            return redirect(url_for('signup'))

        add_user(username, email, phone_num, password)
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))


@app.route('/scanner')
def scanner():
    items = get_items()
    return render_template('scanner.html', barcode_data=barcode_data)


### -- CRUD APPLICATIONS -- ###
@app.route('/add_item', methods=['GET', 'POST'])
def add_item_view():
    if request.method == 'POST':
        barcode = request.form['barcode']
        item_name = request.form['item_name']
        item_category = request.form['item_category']
        item_cost = request.form['item_cost']
        stock = int(request.form['stock'])

        add_item(barcode, item_name, item_category, item_cost, stock)
        flash("Item added successfully!", "success")
        return redirect(url_for('user_dashboard'))
    return render_template('add_item.html', barcode_data=barcode_data)


@app.route('/edit_item/<barcode>', methods=['GET', 'POST'])
def edit_item(barcode):
    item = get_item_by_barcode(barcode)

    if request.method == 'POST':
        item_name = request.form['item_name']
        item_category = request.form['item_category']
        item_cost = request.form['item_cost']
        stock = int(request.form['stock'])

        update_item(barcode, item_name, item_category, item_cost, stock)
        flash("Item updated successfully!", "success")
        return redirect(url_for('user_dashboard'))
    return render_template('edit_item.html', item=item)


@app.route('/delete_item/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM items WHERE itemID = ?", (item_id,))
    conn.commit()
    conn.close()
    flash(f"Item with ID {item_id} has been deleted.", "success")
    return redirect(url_for('user_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)

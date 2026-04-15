import os
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    send_file,
    session,
    flash,
)
from datetime import datetime, timedelta
import sqlite3
import csv
from functools import wraps

import os

app = Flask(__name__)
app.secret_key = "danzona_pharmacy_secret_key_2024"

# Use /tmp for database on Render, local file otherwise
if os.environ.get("RENDER"):
    DB_NAME = "/tmp/pharmacy_pos.db"
else:
    DB_NAME = "pharmacy_pos.db"


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT,
            role TEXT DEFAULT 'staff',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT UNIQUE,
            name TEXT NOT NULL,
            category TEXT,
            batch_number TEXT,
            expiry_date TEXT,
            quantity INTEGER DEFAULT 0,
            unit_price REAL NOT NULL,
            pkt_price REAL DEFAULT 0,
            sachet_price REAL DEFAULT 0,
            bag_price REAL DEFAULT 0,
            ampule_price REAL DEFAULT 0,
            vial_price REAL DEFAULT 0,
            cost_price REAL DEFAULT 0,
            min_stock INTEGER DEFAULT 10,
            supplier TEXT,
            wholesale_price REAL DEFAULT 0,
            ctn_price REAL DEFAULT 0,
            units_per_ctn INTEGER DEFAULT 1,
            location TEXT,
            manufacturer TEXT,
            sku TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            address TEXT,
            loyalty_points INTEGER DEFAULT 0,
            account_balance REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            customer_id INTEGER,
            subtotal REAL,
            discount REAL DEFAULT 0,
            discount_type TEXT DEFAULT 'fixed',
            tax REAL DEFAULT 0,
            total REAL NOT NULL,
            payment_method TEXT,
            amount_paid REAL,
            change_given REAL,
            status TEXT DEFAULT 'completed',
            is_suspended INTEGER DEFAULT 0,
            is_batch INTEGER DEFAULT 0,
            work_order_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER,
            product_id INTEGER,
            product_name TEXT,
            quantity INTEGER,
            unit_price REAL,
            total REAL,
            FOREIGN KEY (sale_id) REFERENCES sales(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            receiver_id INTEGER,
            subject TEXT,
            message TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            field_name TEXT NOT NULL,
            field_type TEXT DEFAULT 'text',
            field_label TEXT NOT NULL,
            is_required INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS work_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE NOT NULL,
            customer_id INTEGER,
            description TEXT,
            status TEXT DEFAULT 'pending',
            total REAL DEFAULT 0,
            created_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    """)

    # Insert default admin user
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (username, password, full_name, role) VALUES (?, ?, ?, ?)",
            ("admin", "admin123", "Administrator", "admin"),
        )

    # Insert default categories
    default_categories = [
        "Medications",
        "Supplements",
        "Baby Care",
        "Personal Care",
        "Medical Supplies",
        "First Aid",
    ]
    for cat in default_categories:
        cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (cat,))

    # Insert default settings
    cursor.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('tax_rate', '5')"
    )
    cursor.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('business_name', 'DANZONA PHARMACY NIG. LTD PLC')"
    )
    cursor.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('business_address', 'AKWANGA, NIGERIA')"
    )

    conn.commit()
    conn.close()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


# Routes
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password),
        )
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    month_start = datetime.now().strftime("%Y-%m-01")

    cursor.execute(
        "SELECT COALESCE(SUM(total), 0) as total, COUNT(*) as count FROM sales WHERE created_at LIKE ? AND is_suspended = 0",
        (f"{today}%",),
    )
    today_sales = cursor.fetchone()

    cursor.execute(
        "SELECT COALESCE(SUM(total), 0) as total FROM sales WHERE created_at LIKE ? AND is_suspended = 0",
        (f"{yesterday}%",),
    )
    yesterday_sales = cursor.fetchone()

    cursor.execute(
        "SELECT COALESCE(SUM(total), 0) as total FROM sales WHERE created_at >= ? AND is_suspended = 0",
        (month_start,),
    )
    month_sales = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) as count FROM products WHERE quantity > 0")
    products_count = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) as count FROM products WHERE quantity <= min_stock")
    low_stock = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) as count FROM customers")
    customers_count = cursor.fetchone()

    cursor.execute("""
        SELECT s.id, s.total, s.payment_method, s.created_at, COALESCE(c.name, 'Walk-in') as customer
        FROM sales s 
        LEFT JOIN customers c ON s.customer_id = c.id 
        WHERE s.is_suspended = 0
        ORDER BY s.id DESC LIMIT 10
    """)
    recent_sales = cursor.fetchall()

    cursor.execute(
        """
        SELECT product_name, SUM(quantity) as total_qty, SUM(total) as total_sales
        FROM sale_items 
        WHERE sale_id IN (SELECT id FROM sales WHERE created_at LIKE ? AND is_suspended = 0)
        GROUP BY product_name 
        ORDER BY total_sales DESC LIMIT 5
    """,
        (f"{today}%",),
    )
    top_products = cursor.fetchall()

    cursor.execute(
        "SELECT COUNT(*) as count FROM messages WHERE receiver_id = ? AND is_read = 0",
        (session["user_id"],),
    )
    unread_messages = cursor.fetchone()

    # Today's receipts count
    cursor.execute(
        "SELECT COUNT(*) as count FROM sales WHERE created_at LIKE ? AND is_suspended = 0",
        (f"{today}%",),
    )
    today_receipts = cursor.fetchone()

    conn.close()

    return render_template(
        "dashboard.html",
        today_sales=today_sales,
        yesterday_sales=yesterday_sales,
        month_sales=month_sales,
        products_count=products_count,
        low_stock=low_stock,
        customers_count=customers_count,
        recent_sales=recent_sales,
        top_products=top_products,
        unread_messages=unread_messages,
        today_receipts=today_receipts,
    )


@app.route("/pos")
@login_required
def pos():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, phone, email, address, account_balance FROM customers ORDER BY name"
    )
    customers = cursor.fetchall()
    cursor.execute("SELECT name FROM categories ORDER BY name")
    categories = cursor.fetchall()
    conn.close()
    return render_template("pos.html", customers=customers, categories=categories)


@app.route("/inventory")
@login_required
def inventory():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products ORDER BY name")
    products = cursor.fetchall()
    cursor.execute("SELECT name FROM categories ORDER BY name")
    categories = cursor.fetchall()
    conn.close()
    return render_template("inventory.html", products=products, categories=categories)


@app.route("/customers")
@login_required
def customers():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers ORDER BY name")
    customers = cursor.fetchall()
    conn.close()
    return render_template("customers.html", customers=customers)


@app.route("/reports")
@login_required
def reports():
    conn = get_db()
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")
    month_start = datetime.now().strftime("%Y-%m-01")

    cursor.execute(
        """
        SELECT DATE(created_at) as date, SUM(total) as total, COUNT(*) as count 
        FROM sales 
        WHERE created_at >= ? AND is_suspended = 0
        GROUP BY DATE(created_at) 
        ORDER BY date DESC
    """,
        (month_start,),
    )
    daily_sales = cursor.fetchall()

    cursor.execute(
        """
        SELECT product_name, SUM(quantity) as qty, SUM(total) as sales
        FROM sale_items
        WHERE sale_id IN (SELECT id FROM sales WHERE created_at >= ? AND is_suspended = 0)
        GROUP BY product_name
        ORDER BY sales DESC
        LIMIT 20
    """,
        (month_start,),
    )
    product_sales = cursor.fetchall()

    cursor.execute(
        """
        SELECT COALESCE(c.name, 'Walk-in') as customer, SUM(s.total) as total, COUNT(*) as visits
        FROM sales s
        LEFT JOIN customers c ON s.customer_id = c.id
        WHERE s.created_at >= ? AND s.is_suspended = 0
        GROUP BY customer
        ORDER BY total DESC
        LIMIT 10
    """,
        (month_start,),
    )
    customer_sales = cursor.fetchall()

    cursor.execute(
        "SELECT SUM(amount) as total FROM expenses WHERE created_at >= ?",
        (month_start,),
    )
    expenses = cursor.fetchone()

    conn.close()
    return render_template(
        "reports.html",
        daily_sales=daily_sales,
        product_sales=product_sales,
        customer_sales=customer_sales,
        expenses=expenses,
    )


@app.route("/sales")
@login_required
def sales():
    conn = get_db()
    cursor = conn.cursor()

    # All sales including suspended
    cursor.execute("""
        SELECT s.id, s.created_at, s.total, s.payment_method, s.status, s.is_suspended, s.is_batch,
               COALESCE(c.name, 'Walk-in') as customer, u.full_name as cashier
        FROM sales s 
        LEFT JOIN customers c ON s.customer_id = c.id
        LEFT JOIN users u ON s.user_id = u.id
        ORDER BY s.id DESC
    """)
    all_sales = cursor.fetchall()

    # Suspended sales
    cursor.execute("""
        SELECT s.id, s.created_at, s.total, s.payment_method,
               COALESCE(c.name, 'Walk-in') as customer
        FROM sales s 
        LEFT JOIN customers c ON s.customer_id = c.id
        WHERE s.is_suspended = 1
        ORDER BY s.id DESC
    """)
    suspended_sales = cursor.fetchall()

    # Today's all receipts
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute(
        """
        SELECT s.id, s.created_at, s.total, s.payment_method, s.status,
               COALESCE(c.name, 'Walk-in') as customer
        FROM sales s 
        LEFT JOIN customers c ON s.customer_id = c.id
        WHERE s.created_at LIKE ? AND s.is_suspended = 0
        ORDER BY s.id DESC
    """,
        (f"{today}%",),
    )
    today_receipts = cursor.fetchall()

    # Work orders
    cursor.execute("""
        SELECT w.*, c.name as customer_name, u.full_name as created_by_name
        FROM work_orders w
        LEFT JOIN customers c ON w.customer_id = c.id
        LEFT JOIN users u ON w.created_by = u.id
        ORDER BY w.id DESC
    """)
    work_orders = cursor.fetchall()

    # Custom fields
    cursor.execute("SELECT * FROM custom_fields ORDER BY id")
    custom_fields = cursor.fetchall()

    conn.close()
    return render_template(
        "sales.html",
        all_sales=all_sales,
        suspended_sales=suspended_sales,
        today_receipts=today_receipts,
        work_orders=work_orders,
        custom_fields=custom_fields,
    )


@app.route("/messages", methods=["GET", "POST"])
@login_required
def messages():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        data = request.form
        cursor.execute(
            """
            INSERT INTO messages (sender_id, receiver_id, subject, message)
            VALUES (?, ?, ?, ?)
        """,
            (
                session["user_id"],
                data.get("receiver_id"),
                data.get("subject"),
                data.get("message"),
            ),
        )
        conn.commit()
        flash("Message sent successfully", "success")

    cursor.execute(
        "SELECT id, full_name, username FROM users WHERE id != ?", (session["user_id"],)
    )
    users = cursor.fetchall()

    cursor.execute(
        """
        SELECT m.*, u.full_name as sender_name
        FROM messages m
        LEFT JOIN users u ON m.sender_id = u.id
        WHERE m.receiver_id = ?
        ORDER BY m.created_at DESC
    """,
        (session["user_id"],),
    )
    inbox = cursor.fetchall()

    cursor.execute(
        """
        SELECT m.*, u.full_name as receiver_name
        FROM messages m
        LEFT JOIN users u ON m.receiver_id = u.id
        WHERE m.sender_id = ?
        ORDER BY m.created_at DESC
    """,
        (session["user_id"],),
    )
    sent = cursor.fetchall()

    conn.close()
    return render_template("messages.html", users=users, inbox=inbox, sent=sent)


# API Routes
@app.route("/api/products")
def api_products():
    conn = get_db()
    cursor = conn.cursor()
    search = request.args.get("search", "")
    category = request.args.get("category", "")
    letter = request.args.get("letter", "")

    query = "SELECT * FROM products WHERE quantity > 0"
    params = []

    if search:
        query += " AND (barcode LIKE ? OR name LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    if category:
        query += " AND category = ?"
        params.append(category)
    if letter:
        query += " AND UPPER(name) LIKE ?"
        params.append(f"{letter}%")

    query += " ORDER BY name"
    cursor.execute(query, params)
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(products)


@app.route("/api/inventory")
def api_inventory():
    conn = get_db()
    cursor = conn.cursor()
    search = request.args.get("search", "")

    if search:
        cursor.execute(
            """
            SELECT * FROM products 
            WHERE barcode LIKE ? OR name LIKE ? OR category LIKE ?
            ORDER BY name
        """,
            (f"%{search}%", f"%{search}%", f"%{search}%"),
        )
    else:
        cursor.execute("SELECT * FROM products ORDER BY name")

    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(products)


@app.route("/api/customers")
def api_customers():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers ORDER BY name")
    customers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(customers)


@app.route("/api/sales")
def api_sales():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, COALESCE(c.name, 'Walk-in') as customer
        FROM sales s 
        LEFT JOIN customers c ON s.customer_id = c.id 
        ORDER BY s.id DESC
    """)
    sales = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(sales)


@app.route("/api/low-stock")
def api_low_stock():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM products WHERE quantity <= min_stock ORDER BY quantity"
    )
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(products)


# Product Management
@app.route("/product", methods=["GET", "POST"])
@app.route("/product/<int:product_id>", methods=["GET", "POST"])
@login_required
def manage_product(product_id=None):
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        data = request.form

        if product_id:
            cursor.execute(
                """
                UPDATE products SET barcode=?, name=?, category=?, batch_number=?, expiry_date=?,
                                   quantity=?, unit_price=?, pkt_price=?, sachet_price=?, bag_price=?, ampule_price=?, vial_price=?,
                                   cost_price=?, min_stock=?, supplier=?,
                                   wholesale_price=?, ctn_price=?, units_per_ctn=?, location=?, manufacturer=?, sku=?
                WHERE id=?
            """,
                (
                    data.get("barcode"),
                    data.get("name"),
                    data.get("category"),
                    data.get("batch_number"),
                    data.get("expiry_date"),
                    int(data.get("quantity", 0)),
                    float(data.get("unit_price", 0)),
                    float(data.get("pkt_price", 0)),
                    float(data.get("sachet_price", 0)),
                    float(data.get("bag_price", 0)),
                    float(data.get("ampule_price", 0)),
                    float(data.get("vial_price", 0)),
                    float(data.get("cost_price", 0)),
                    int(data.get("min_stock", 10)),
                    data.get("supplier"),
                    float(data.get("wholesale_price", 0)),
                    float(data.get("ctn_price", 0)),
                    int(data.get("units_per_ctn", 1)),
                    data.get("location"),
                    data.get("manufacturer"),
                    data.get("sku"),
                    product_id,
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO products (barcode, name, category, batch_number, expiry_date, 
                                   quantity, unit_price, pkt_price, sachet_price, bag_price, ampule_price, vial_price,
                                   cost_price, min_stock, supplier,
                                   wholesale_price, ctn_price, units_per_ctn, location, manufacturer, sku)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    data.get("barcode"),
                    data.get("name"),
                    data.get("category"),
                    data.get("batch_number"),
                    data.get("expiry_date"),
                    int(data.get("quantity", 0)),
                    float(data.get("unit_price", 0)),
                    float(data.get("pkt_price", 0)),
                    float(data.get("sachet_price", 0)),
                    float(data.get("bag_price", 0)),
                    float(data.get("ampule_price", 0)),
                    float(data.get("vial_price", 0)),
                    float(data.get("cost_price", 0)),
                    int(data.get("min_stock", 10)),
                    data.get("supplier"),
                    float(data.get("wholesale_price", 0)),
                    float(data.get("ctn_price", 0)),
                    int(data.get("units_per_ctn", 1)),
                    data.get("location"),
                    data.get("manufacturer"),
                    data.get("sku"),
                ),
            )
        conn.commit()
        flash("Product saved successfully", "success")
        conn.close()
        return redirect(url_for("inventory"))

    product = None
    if product_id:
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()

    cursor.execute("SELECT name FROM categories ORDER BY name")
    categories = cursor.fetchall()
    conn.close()
    return render_template("product.html", product=product, categories=categories)


@app.route("/product/delete/<int:product_id>")
@login_required
def delete_product(product_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    flash("Product deleted", "success")
    return redirect(url_for("inventory"))


@app.route("/receive-stock", methods=["POST"])
@login_required
def receive_stock():
    data = request.json
    product_id = data.get("product_id")
    quantity = data.get("quantity", 0)
    cost_price = data.get("cost_price", 0)

    conn = get_db()
    cursor = conn.cursor()

    if cost_price > 0:
        cursor.execute(
            "UPDATE products SET quantity = quantity + ?, cost_price = ? WHERE id = ?",
            (quantity, cost_price, product_id),
        )
    else:
        cursor.execute(
            "UPDATE products SET quantity = quantity + ? WHERE id = ?",
            (quantity, product_id),
        )

    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Stock received successfully"})


# Customer Management
@app.route("/customer", methods=["POST"])
@app.route("/customer/<int:customer_id>", methods=["GET", "POST"])
@login_required
def manage_customer(customer_id=None):
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        data = request.form
        if customer_id:
            cursor.execute(
                """
                UPDATE customers SET name=?, phone=?, email=?, address=? WHERE id=?
            """,
                (
                    data.get("name"),
                    data.get("phone"),
                    data.get("email"),
                    data.get("address"),
                    customer_id,
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO customers (name, phone, email, address) VALUES (?, ?, ?, ?)
            """,
                (
                    data.get("name"),
                    data.get("phone"),
                    data.get("email"),
                    data.get("address"),
                ),
            )
        conn.commit()
        flash("Customer saved successfully", "success")
        conn.close()
        return redirect(url_for("customers"))

    customer = None
    if customer_id:
        cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
        customer = cursor.fetchone()
    conn.close()
    return render_template("customer_form.html", customer=customer)


@app.route("/customer/delete/<int:customer_id>")
@login_required
def delete_customer(customer_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
    conn.commit()
    conn.close()
    flash("Customer deleted", "success")
    return redirect(url_for("customers"))


# Process Sale
@app.route("/process-sale", methods=["POST"])
@login_required
def process_sale():
    data = request.json
    cart = data.get("cart", [])
    customer_name = data.get("customer")
    discount = float(data.get("discount", 0))
    discount_type = data.get("discount_type", "fixed")
    payment_method = data.get("payment_method", "Cash")
    amount_paid = float(data.get("amount_paid", 0))
    is_suspended = data.get("is_suspended", False)
    is_batch = data.get("is_batch", False)
    work_order_id = data.get("work_order_id", None)

    if not cart:
        return jsonify({"success": False, "message": "Cart is empty"})

    subtotal = sum(item["total"] for item in cart)

    if discount_type == "percent":
        discount_amount = subtotal * (discount / 100)
    else:
        discount_amount = discount

    tax = subtotal * 0.05
    total = subtotal - discount_amount + tax

    if not is_suspended and amount_paid < total:
        return jsonify({"success": False, "message": "Insufficient payment"})

    change = amount_paid - total

    conn = get_db()
    cursor = conn.cursor()

    customer_id = None
    if customer_name:
        cursor.execute("SELECT id FROM customers WHERE name = ?", (customer_name,))
        result = cursor.fetchone()
        if result:
            customer_id = result["id"]

    cursor.execute(
        """
        INSERT INTO sales (user_id, customer_id, subtotal, discount, discount_type, tax, total, 
                          payment_method, amount_paid, change_given, is_suspended, is_batch, work_order_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            session["user_id"],
            customer_id,
            subtotal,
            discount_amount,
            discount_type,
            tax,
            total,
            payment_method,
            amount_paid,
            change,
            1 if is_suspended else 0,
            1 if is_batch else 0,
            work_order_id,
        ),
    )

    sale_id = cursor.lastrowid

    if not is_suspended:
        for item in cart:
            cursor.execute(
                """
                INSERT INTO sale_items (sale_id, product_id, product_name, quantity, unit_price, total)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    sale_id,
                    item["id"],
                    item["name"],
                    item["quantity"],
                    item["price"],
                    item["total"],
                ),
            )

            cursor.execute(
                "UPDATE products SET quantity = quantity - ? WHERE id = ?",
                (item["quantity"], item["id"]),
            )

    conn.commit()

    receipt_data = {
        "id": sale_id,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "customer": customer_name or "Walk-in",
        "items": [
            {
                "product_name": item["name"],
                "quantity": item["quantity"],
                "unit_price": item["price"],
                "total": item["total"],
            }
            for item in cart
        ],
        "subtotal": subtotal,
        "discount": discount_amount,
        "tax": tax,
        "total": total,
        "method": payment_method,
        "paid": amount_paid,
        "change": change,
        "status": "Suspended" if is_suspended else "Completed",
    }

    conn.close()
    return jsonify(
        {"success": True, "sale_id": sale_id, "change": change, "receipt": receipt_data}
    )


@app.route("/resume-sale/<int:sale_id>", methods=["POST"])
@login_required
def resume_sale(sale_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM sale_items WHERE sale_id = ?", (sale_id,))
    items = cursor.fetchall()

    cursor.execute("SELECT * FROM sales WHERE id = ?", (sale_id,))
    sale = cursor.fetchone()

    amount_paid = float(request.json.get("amount_paid", 0))

    if amount_paid < sale["total"]:
        return jsonify({"success": False, "message": "Insufficient payment"})

    change = amount_paid - sale["total"]

    for item in items:
        cursor.execute(
            "UPDATE products SET quantity = quantity - ? WHERE id = ?",
            (item["quantity"], item["product_id"]),
        )

    cursor.execute(
        """
        UPDATE sales SET is_suspended = 0, amount_paid = ?, change_given = ?, status = 'completed'
        WHERE id = ?
    """,
        (amount_paid, change, sale_id),
    )

    conn.commit()
    conn.close()
    return jsonify({"success": True, "change": change})


@app.route("/lookup-receipt", methods=["POST"])
@login_required
def lookup_receipt():
    receipt_number = request.form.get("receipt_number")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sales WHERE id = ?", (receipt_number,))
    sale = cursor.fetchone()

    if not sale:
        flash("Receipt not found", "danger")
        return redirect(url_for("sales"))

    cursor.execute(
        "SELECT product_name, quantity, unit_price, total FROM sale_items WHERE sale_id = ?",
        (receipt_number,),
    )
    items = cursor.fetchall()

    cursor.execute("SELECT name FROM customers WHERE id = ?", (sale["customer_id"],))
    customer = cursor.fetchone()

    cursor.execute("SELECT value FROM settings WHERE key = 'business_name'")
    business_name = cursor.fetchone()

    receipt = {
        "id": receipt_number,
        "date": sale["created_at"],
        "customer": customer["name"] if customer else "Walk-in",
        "items": [dict(item) for item in items],
        "subtotal": sale["subtotal"],
        "discount": sale["discount"],
        "tax": sale["tax"],
        "total": sale["total"],
        "method": sale["payment_method"],
        "paid": sale["amount_paid"],
        "change": sale["change_given"],
        "status": sale["status"],
        "business_name": business_name["value"]
        if business_name
        else "DANZONA PHARMACY",
    }
    conn.close()
    return render_template("receipt.html", receipt=receipt)


@app.route("/receipt/<int:sale_id>")
@login_required
def view_receipt(sale_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sales WHERE id = ?", (sale_id,))
    sale = cursor.fetchone()
    cursor.execute(
        "SELECT product_name, quantity, unit_price, total FROM sale_items WHERE sale_id = ?",
        (sale_id,),
    )
    items = cursor.fetchall()

    cursor.execute("SELECT name FROM customers WHERE id = ?", (sale["customer_id"],))
    customer = cursor.fetchone()

    cursor.execute("SELECT value FROM settings WHERE key = 'business_name'")
    business_name = cursor.fetchone()

    receipt = {
        "id": sale_id,
        "date": sale["created_at"],
        "customer": customer["name"] if customer else "Walk-in",
        "items": [dict(item) for item in items],
        "subtotal": sale["subtotal"],
        "discount": sale["discount"],
        "tax": sale["tax"],
        "total": sale["total"],
        "method": sale["payment_method"],
        "paid": sale["amount_paid"],
        "change": sale["change_given"],
        "status": sale["status"],
        "business_name": business_name["value"]
        if business_name
        else "DANZONA PHARMACY",
    }
    conn.close()
    return render_template("receipt.html", receipt=receipt)


@app.route("/last-receipt")
@login_required
def last_receipt():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM sales WHERE is_suspended = 0 ORDER BY id DESC LIMIT 1"
    )
    last = cursor.fetchone()
    conn.close()

    if last:
        return redirect(url_for("view_receipt", sale_id=last["id"]))
    flash("No receipts found", "warning")
    return redirect(url_for("sales"))


@app.route("/sale/delete/<int:sale_id>")
@login_required
def cancel_sale(sale_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT is_suspended FROM sales WHERE id = ?", (sale_id,))
    sale = cursor.fetchone()

    if sale and sale["is_suspended"] == 0:
        cursor.execute(
            "SELECT product_id, quantity FROM sale_items WHERE sale_id = ?", (sale_id,)
        )
        items = cursor.fetchall()
        for item in items:
            cursor.execute(
                "UPDATE products SET quantity = quantity + ? WHERE id = ?",
                (item["quantity"], item["product_id"]),
            )

    cursor.execute("UPDATE sales SET status = 'cancelled' WHERE id = ?", (sale_id,))
    conn.commit()
    conn.close()
    flash("Sale cancelled", "success")
    return redirect(url_for("sales"))


@app.route("/suspended-sale/delete/<int:sale_id>")
@login_required
def delete_suspended_sale(sale_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sale_items WHERE sale_id = ?", (sale_id,))
    cursor.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
    conn.commit()
    conn.close()
    flash("Suspended sale deleted", "success")
    return redirect(url_for("sales"))


@app.route("/export-sales")
@login_required
def export_sales():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, s.created_at, COALESCE(c.name, 'Walk-in') as customer, 
               s.subtotal, s.discount, s.tax, s.total, s.payment_method, s.status
        FROM sales s LEFT JOIN customers c ON s.customer_id = c.id
        WHERE s.is_suspended = 0
        ORDER BY s.id DESC
    """)

    filename = f"sales_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "ID",
                "Date",
                "Customer",
                "Subtotal",
                "Discount",
                "Tax",
                "Total",
                "Method",
                "Status",
            ]
        )
        for row in cursor.fetchall():
            writer.writerow(
                [
                    row["id"],
                    row["created_at"],
                    row["customer"],
                    row["subtotal"],
                    row["discount"],
                    row["tax"],
                    row["total"],
                    row["payment_method"],
                    row["status"],
                ]
            )

    conn.close()
    return send_file(filename, as_attachment=True)


@app.route("/import-sales", methods=["GET", "POST"])
@login_required
def import_sales():
    if request.method == "POST":
        file = request.files["file"]
        if file:
            filename = f"import_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
            file.save(filename)

            conn = get_db()
            cursor = conn.cursor()

            with open(filename, "r") as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                for row in reader:
                    try:
                        cursor.execute(
                            """
                            INSERT INTO sales (user_id, customer_id, subtotal, discount, tax, total, 
                                              payment_method, amount_paid, change_given, is_batch)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                        """,
                            (
                                session["user_id"],
                                None,
                                float(row[3]),
                                0,
                                float(row[5]),
                                float(row[6]),
                                row[7],
                                float(row[6]),
                                0,
                            ),
                        )
                    except:
                        pass

            conn.commit()
            conn.close()
            os.remove(filename)
            flash("Sales imported successfully", "success")
            return redirect(url_for("sales"))

    return render_template("import_sales.html")


@app.route("/account-payment", methods=["GET", "POST"])
@login_required
def account_payment():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        customer_id = request.form.get("customer_id")
        amount = float(request.form.get("amount"))
        description = request.form.get("description")

        cursor.execute(
            "UPDATE customers SET account_balance = account_balance - ? WHERE id = ?",
            (amount, customer_id),
        )
        cursor.execute(
            "INSERT INTO expenses (description, amount, category, created_by) VALUES (?, ?, ?, ?)",
            (
                f"Payment from customer #{customer_id}: {description}",
                amount,
                "Customer Payment",
                session["user_id"],
            ),
        )
        conn.commit()
        flash("Payment recorded successfully", "success")
        return redirect(url_for("sales"))

    cursor.execute("SELECT * FROM customers WHERE account_balance > 0 ORDER BY name")
    debtors = cursor.fetchall()
    conn.close()
    return render_template("account_payment.html", debtors=debtors)


@app.route("/work-order", methods=["GET", "POST"])
@login_required
def work_order():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        customer_id = request.form.get("customer_id")
        description = request.form.get("description")
        order_number = f"WO-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        cursor.execute(
            """
            INSERT INTO work_orders (order_number, customer_id, description, created_by)
            VALUES (?, ?, ?, ?)
        """,
            (order_number, customer_id, description, session["user_id"]),
        )
        conn.commit()
        flash("Work order created", "success")
        return redirect(url_for("sales"))

    cursor.execute("SELECT id, name FROM customers ORDER BY name")
    customers = cursor.fetchall()
    conn.close()
    return render_template("work_order.html", customers=customers)


@app.route("/work-order/complete/<int:order_id>")
@login_required
def complete_work_order(order_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE work_orders WHERE id = ? SET status = 'completed'", (order_id,)
    )
    conn.commit()
    conn.close()
    flash("Work order completed", "success")
    return redirect(url_for("sales"))


@app.route("/custom-fields", methods=["GET", "POST"])
@login_required
def custom_fields():
    if session.get("role") != "admin":
        flash("Access denied", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        field_name = request.form.get("field_name")
        field_type = request.form.get("field_type")
        field_label = request.form.get("field_label")
        is_required = 1 if request.form.get("is_required") else 0

        cursor.execute(
            """
            INSERT INTO custom_fields (field_name, field_type, field_label, is_required)
            VALUES (?, ?, ?, ?)
        """,
            (field_name, field_type, field_label, is_required),
        )
        conn.commit()
        flash("Custom field added", "success")

    cursor.execute("SELECT * FROM custom_fields ORDER BY id")
    fields = cursor.fetchall()
    conn.close()
    return render_template("custom_fields.html", fields=fields)


@app.route("/custom-field/delete/<int:field_id>")
@login_required
def delete_custom_field(field_id):
    if session.get("role") != "admin":
        flash("Access denied", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM custom_fields WHERE id = ?", (field_id,))
    conn.commit()
    conn.close()
    flash("Custom field deleted", "success")
    return redirect(url_for("custom_fields"))


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if session.get("role") != "admin":
        flash("Access denied", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        data = request.form
        for key, value in data.items():
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
        conn.commit()
        flash("Settings saved", "success")

    cursor.execute("SELECT * FROM settings")
    settings = {row["key"]: row["value"] for row in cursor.fetchall()}
    conn.close()
    return render_template("settings.html", settings=settings)


@app.route("/customer-display")
@login_required
def customer_display():
    return render_template("customer_display.html")


# Initialize database and create default admin on startup
init_db()
conn = get_db()
cursor = conn.cursor()
cursor.execute("SELECT * FROM users WHERE username = 'admin'")
if not cursor.fetchone():
    cursor.execute(
        "INSERT INTO users (username, password, full_name, role) VALUES (?, ?, ?, ?)",
        ("admin", "admin123", "Administrator", "admin"),
    )
    conn.commit()
conn.close()


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)

import tkinter as tk
from tkinter import messagebox, ttk, filedialog, simpledialog
import mysql.connector
from PIL import Image, ImageTk
import os
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import random
import time
import threading

# Color scheme
COLORS = {
    "primary": "#1a237e",     # Deep indigo
    "secondary": "#7986cb",   # Lighter indigo
    "accent": "#ff4081",      # Pink accent
    "success": "#00c853",     # Green
    "warning": "#ffd600",     # Yellow
    "danger": "#d50000",      # Red
    "light": "#f5f5f5",       # Light grey
    "dark": "#212121"         # Dark grey
}

# Global variables
current_user = None
current_role = None
inventory_threshold = 10  # Default threshold for low inventory alerts
notifications = []

# Database Connection
def connect_db():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="garment_inventory"
        )
    except mysql.connector.Error as err:
        messagebox.showerror("Database Connection Error", f"Failed to connect to database: {err}")
        return None

# Create Tables
def create_tables():
    db = connect_db()
    if not db:
        return
        
    cursor = db.cursor()

    tables = [
        """CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            role ENUM('admin', 'staff') NOT NULL,
            email VARCHAR(255),
            last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            profile_pic LONGBLOB
        )""",
        """CREATE TABLE IF NOT EXISTS garments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            garment_name VARCHAR(255) NOT NULL,
            category VARCHAR(100) NOT NULL,
            size VARCHAR(10) NOT NULL,
            color VARCHAR(50) NOT NULL,
            quantity INT NOT NULL,
            price FLOAT NOT NULL,
            cost_price FLOAT NOT NULL,
            supplier_id INT,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS suppliers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            supplier_name VARCHAR(255) NOT NULL,
            contact_person VARCHAR(255),
            phone VARCHAR(20),
            email VARCHAR(255),
            address TEXT,
            rating INT DEFAULT 0,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            garment_id INT,
            quantity INT NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status ENUM('pending', 'shipped', 'delivered', 'cancelled') DEFAULT 'pending',
            customer_name VARCHAR(255),
            customer_contact VARCHAR(255),
            FOREIGN KEY (garment_id) REFERENCES garments(id)
        )""",
        """CREATE TABLE IF NOT EXISTS sales (
            id INT AUTO_INCREMENT PRIMARY KEY,
            garment_id INT,
            quantity INT NOT NULL,
            sale_price FLOAT NOT NULL,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            profit FLOAT,
            user_id INT,
            FOREIGN KEY (garment_id) REFERENCES garments(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )""",
        """CREATE TABLE IF NOT EXISTS activity_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            activity TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )""",
        """CREATE TABLE IF NOT EXISTS settings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            setting_name VARCHAR(255) UNIQUE NOT NULL,
            setting_value VARCHAR(255) NOT NULL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )"""
    ]

    for table in tables:
        cursor.execute(table)

    # Insert default settings
    try:
        cursor.execute("INSERT INTO settings (setting_name, setting_value) VALUES (%s, %s)", 
                      ("inventory_threshold", str(inventory_threshold)))
        cursor.execute("INSERT INTO settings (setting_name, setting_value) VALUES (%s, %s)", 
                      ("company_name", "Garment Inventory System"))
        db.commit()
    except mysql.connector.IntegrityError:
        # Settings already exist
        pass

    db.commit()
    db.close()

# Load settings from the database
def load_settings():
    global inventory_threshold
    db = connect_db()
    if not db:
        return
        
    cursor = db.cursor()
    cursor.execute("SELECT setting_name, setting_value FROM settings")
    for name, value in cursor.fetchall():
        if name == "inventory_threshold":
            inventory_threshold = int(value)
    db.close()

# Authentication and User Management
def register_user():
    def submit_registration():
        username = reg_username.get()
        pwd = reg_password.get()
        role = reg_role.get()
        email = reg_email.get()
        
        if not username or not pwd or not role or not email:
            show_notification(register_window, "All fields are required", "warning")
            return
        
        if not terms_var.get():
            show_notification(register_window, "You must accept Terms & Conditions", "warning")
            return
            
        db = connect_db()
        if not db:
            return
            
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password, role, email) VALUES (%s, %s, %s, %s)", 
                          (username, pwd, role, email))
            db.commit()
            
            # Log activity
            user_id = cursor.lastrowid
            cursor.execute("INSERT INTO activity_log (user_id, activity) VALUES (%s, %s)",
                           (user_id, f"User {username} registered as {role}"))
            db.commit()
            
            show_notification(register_window, "User registered successfully!", "success")
            
            # Create success animation
            success_animation(register_window)
            
            register_window.after(2000, register_window.destroy)
        except mysql.connector.IntegrityError:
            show_notification(register_window, "Username already exists", "danger")
        finally:
            db.close()

    # Registration Window Setup
    register_window = tk.Toplevel()
    register_window.title("Register New User")
    register_window.geometry("600x600")
    register_window.configure(bg=COLORS["light"])
        
    # Title
    title_frame = tk.Frame(register_window, bg=COLORS["primary"], padx=10, pady=10)
    title_frame.pack(fill=tk.X)
    
    title_label = tk.Label(title_frame, text="Register New User", font=("Arial", 16, "bold"), 
                         bg=COLORS["primary"], fg=COLORS["light"])
    title_label.pack()
    
    # Form
    form_frame = tk.Frame(register_window, bg=COLORS["light"], padx=20, pady=20)
    form_frame.pack(fill=tk.BOTH, expand=True)
    
    # Username
    tk.Label(form_frame, text="Username:", bg=COLORS["light"], font=("Arial", 12)).grid(row=0, column=0, sticky="w", pady=10)
    reg_username = tk.Entry(form_frame, font=("Arial", 12), width=30)
    reg_username.grid(row=0, column=1, pady=10)
    
    # Password
    tk.Label(form_frame, text="Password:", bg=COLORS["light"], font=("Arial", 12)).grid(row=1, column=0, sticky="w", pady=10)
    reg_password = tk.Entry(form_frame, show="*", font=("Arial", 12), width=30)
    reg_password.grid(row=1, column=1, pady=10)
    
    # Role
    tk.Label(form_frame, text="Role:", bg=COLORS["light"], font=("Arial", 12)).grid(row=2, column=0, sticky="w", pady=10)
    reg_role = ttk.Combobox(form_frame, values=["admin", "staff"], font=("Arial", 12), width=28, state="readonly")
    reg_role.current(1)  # Default to staff
    reg_role.grid(row=2, column=1, pady=10)
    
    # Email
    tk.Label(form_frame, text="Email:", bg=COLORS["light"], font=("Arial", 12)).grid(row=3, column=0, sticky="w", pady=10)
    reg_email = tk.Entry(form_frame, font=("Arial", 12), width=30)
    reg_email.grid(row=3, column=1, pady=10)
    
    # Terms and conditions
    terms_frame = tk.Frame(form_frame, bg=COLORS["light"])
    terms_frame.grid(row=7, column=0, columnspan=2, pady=10)
    
    terms_var = tk.BooleanVar()
    terms_check = tk.Checkbutton(terms_frame, text="I agree to the Terms and Conditions", 
                                variable=terms_var, font=("Montserrat", 12),
                                bg=COLORS["light"], activebackground=COLORS["light"],
                                fg=COLORS["dark"])
    terms_check.pack(side=tk.LEFT)
    
    terms_link = tk.Label(terms_frame, text="View Terms", font=("Montserrat", 12, "underline"),
                         fg=COLORS["accent"], bg=COLORS["light"], cursor="hand2")
    terms_link.pack(side=tk.LEFT, padx=10)
    terms_link.bind("<Button-1>", lambda e: show_terms_and_conditions())
    
    # Submit Button
    submit_btn = tk.Button(form_frame, text="Register", font=("Arial", 12, "bold"), 
                          bg=COLORS["primary"], fg=COLORS["light"], padx=20, pady=5,
                          command=submit_registration)
    submit_btn.grid(row=5, column=0, columnspan=2, pady=20)
    
    # Notification area
    notification_frame = tk.Frame(register_window, bg=COLORS["light"], padx=20, pady=10)
    notification_frame.pack(fill=tk.X, side=tk.BOTTOM)

# Show terms and conditions
def show_terms_and_conditions():
    terms_window = tk.Toplevel()
    terms_window.title("Terms and Conditions")
    terms_window.geometry("600x500")
    terms_window.configure(bg=COLORS["light"])
    
    title = tk.Label(terms_window, text="Terms and Conditions", font=("Montserrat", 18, "bold"),
                    bg=COLORS["light"], fg=COLORS["primary"])
    title.pack(pady=20)
    
    # Create scrollable text area
    terms_frame = tk.Frame(terms_window, bg=COLORS["light"])
    terms_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
    
    scrollbar = tk.Scrollbar(terms_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    terms_text = tk.Text(terms_frame, font=("Montserrat", 12), bg="white", fg=COLORS["dark"],
                        yscrollcommand=scrollbar.set, wrap=tk.WORD)
    terms_text.pack(fill=tk.BOTH, expand=True)
    
    scrollbar.config(command=terms_text.yview)
    
    # Sample terms text
    terms = """1. ACCEPTANCE OF TERMS
    By accessing and using this Garment Inventory Management System, you accept and agree to be bound by the terms and conditions of this agreement.
    
2. USER ACCOUNTS
    Users are responsible for maintaining the confidentiality of their account information and password.
    Users are responsible for all activities that occur under their account.
    
3. PRIVACY POLICY
    All personal information collected will be used solely for the purposes of managing inventory and user authentication.
    
4. DATA INTEGRITY
    Users must ensure all data entered is accurate and complete.
    
5. SECURITY
    Users must not attempt to breach system security or access unauthorized data.
    
6. TERMINATION
    The company reserves the right to terminate user accounts for violations of these terms.
    
7. DISCLAIMER OF WARRANTIES
    This system is provided "as is" without warranty of any kind.
    
8. LIMITATION OF LIABILITY
    The company shall not be liable for any damages arising from the use of this system.
    
9. GOVERNING LAW
    These terms shall be governed by the laws of the jurisdiction in which the company operates.
    
10. CHANGES TO TERMS
    The company reserves the right to modify these terms at any time without notice."""
    
    terms_text.insert(tk.END, terms)
    terms_text.config(state=tk.DISABLED)  # Make read-only
    
    # Close button
    close_btn = tk.Button(terms_window, text="Close", font=("Montserrat", 12),
                         bg=COLORS["primary"], fg="white", command=terms_window.destroy,
                         relief=tk.FLAT, padx=30, pady=5)
    close_btn.pack(pady=20)

# Login page
def show_login():
    def login_user():
        username = username_entry.get()
        pwd = password_entry.get()
        
        if not username or not pwd:
            show_notification(login_window, "Username and password are required", "warning")
            return
            
        db = connect_db()
        if not db:
            return
            
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, pwd))
        user = cursor.fetchone()
        
        if user:
            # Update last login
            cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s", (user['id'],))
            
            # Log activity
            cursor.execute("INSERT INTO activity_log (user_id, activity) VALUES (%s, %s)",
                          (user['id'], "User logged in"))
            db.commit()
            
            global current_user, current_role
            current_user = user
            current_role = user['role']
            
            show_notification(login_window, "Login successful! Redirecting...", "success")
            
            # Play success animation
            success_animation(login_window)
            
            login_window.after(1500, lambda: [login_window.destroy(), home_page(username, current_role)])
        else:
            show_notification(login_window, "Invalid username or password", "danger")
            # Shake animation for failed login
            shake_animation(login_frame)
            
        db.close()
    
    # Setup login window
    login_window = tk.Tk()
    login_window.title("Garment Inventory System - Login")
    login_window.geometry("2056x1028")
    login_window.configure(bg=COLORS["light"])
    
    # Create a header
    header_frame = tk.Frame(login_window, bg=COLORS["primary"], padx=10, pady=10)
    header_frame.pack(fill=tk.X)
    
    title_label = tk.Label(header_frame, text="Garment Inventory System", font=("Arial", 18, "bold"), 
                         bg=COLORS["primary"], fg=COLORS["light"])
    title_label.pack()
    
    # Login Form
    login_frame = tk.Frame(login_window, bg=COLORS["light"], padx=30, pady=30)
    login_frame.pack(padx=20, pady=20)
    
    # Logo or Icon (placeholder)
    try:
        # Try to load a logo if it exists
        logo = Image.open("logo.png")
        logo = logo.resize((100, 100), Image.LANCZOS)
        logo_img = ImageTk.PhotoImage(logo)
        logo_label = tk.Label(login_frame, image=logo_img, bg=COLORS["light"])
        logo_label.image = logo_img  # Keep a reference
        logo_label.pack(pady=10)
    except:
        # If logo doesn't exist, just show a placeholder
        placeholder = tk.Label(login_frame, text="👕", font=("Arial", 50), bg=COLORS["light"], fg=COLORS["primary"])
        placeholder.pack(pady=10)
    
    # Username
    username_label = tk.Label(login_frame, text="Username:", font=("Arial", 12), bg=COLORS["light"])
    username_label.pack(anchor="w", pady=(20, 5))
    
    username_entry = tk.Entry(login_frame, font=("Arial", 12), width=30)
    username_entry.pack(pady=(0, 15))
    
    # Password
    password_label = tk.Label(login_frame, text="Password:", font=("Arial", 12), bg=COLORS["light"])
    password_label.pack(anchor="w", pady=(0, 5))
    
    password_entry = tk.Entry(login_frame, show="*", font=("Arial", 12), width=30)
    password_entry.pack(pady=(0, 20))
    
    # Login Button
    login_button = tk.Button(login_frame, text="Login", font=("Arial", 12, "bold"), 
                           bg=COLORS["primary"], fg=COLORS["light"], padx=20, pady=5,
                           command=login_user)
    login_button.pack(pady=10)
    
    # Register Link
    register_link = tk.Label(login_frame, text="Register New User", font=("Arial", 10, "underline"), 
                           fg=COLORS["accent"], bg=COLORS["light"], cursor="hand2")
    register_link.pack(pady=20)
    register_link.bind("<Button-1>", lambda e: register_user())
    
    # Notification area
    notification_frame = tk.Frame(login_window, bg=COLORS["light"], padx=20, pady=10)
    notification_frame.pack(fill=tk.X, side=tk.BOTTOM)
    
    # Check if database exists and create tables if needed
    create_tables()
    load_settings()
    
    login_window.mainloop()

def view_suppliers(parent):
    clear_frame(parent)
    create_title_bar(parent, "Suppliers Management")

    # Create search and filter bar
    search_frame = tk.Frame(parent, bg=COLORS["light"], pady=10)
    search_frame.pack(fill=tk.X, padx=20)

    # Search input
    search_container = tk.Frame(search_frame, bg="white", highlightbackground=COLORS["secondary"],
                              highlightthickness=1, padx=10)
    search_container.pack(side=tk.LEFT)

    search_icon = tk.Label(search_container, text="🔍", bg="white")
    search_icon.pack(side=tk.LEFT)

    search_entry = tk.Entry(search_container, font=("Montserrat", 12), bd=0, bg="white", width=25)
    search_entry.pack(side=tk.LEFT, ipady=8, padx=5)
    search_entry.insert(0, "Search suppliers...")

    # Clear on focus
    def on_entry_click(event):
        if search_entry.get() == "Search suppliers...":
            search_entry.delete(0, tk.END)
            search_entry.config(fg=COLORS["dark"])

    # Reset if empty on focus out
    def on_focus_out(event):
        if search_entry.get() == "":
            search_entry.insert(0, "Search suppliers...")
            search_entry.config(fg=COLORS["secondary"])

    search_entry.bind("<FocusIn>", on_entry_click)
    search_entry.bind("<FocusOut>", on_focus_out)
    search_entry.config(fg=COLORS["secondary"])

    # Add new supplier button
    add_btn = tk.Button(search_frame, text="Add New Supplier", font=("Montserrat", 12, "bold"),
                      bg=COLORS["primary"], fg="white", padx=15, pady=5,
                      command=lambda: add_new_supplier(parent, None))
    add_btn.pack(side=tk.RIGHT)

    # Create suppliers table
    table_frame = tk.Frame(parent, bg=COLORS["light"], padx=20, pady=20)
    table_frame.pack(fill=tk.BOTH, expand=True)

    # Scrollbars
    table_scroll_y = tk.Scrollbar(table_frame)
    table_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

    table_scroll_x = tk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
    table_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

    # Treeview for suppliers table
    columns = ("ID", "Name", "Contact Person", "Phone", "Email", "Address", "Rating")

    style = ttk.Style()
    style.configure("Treeview", font=("Montserrat", 12), rowheight=30)
    style.configure("Treeview.Heading", font=("Montserrat", 12, "bold"))

    suppliers_table = ttk.Treeview(table_frame, columns=columns, show="headings",
                                  yscrollcommand=table_scroll_y.set,
                                  xscrollcommand=table_scroll_x.set)

    table_scroll_y.config(command=suppliers_table.yview)
    table_scroll_x.config(command=suppliers_table.xview)

    # Define column headings and widths
    suppliers_table.heading("ID", text="ID")
    suppliers_table.column("ID", width=50, anchor="center")

    suppliers_table.heading("Name", text="Name")
    suppliers_table.column("Name", width=150, anchor="w")

    suppliers_table.heading("Contact Person", text="Contact Person")
    suppliers_table.column("Contact Person", width=150, anchor="w")

    suppliers_table.heading("Phone", text="Phone")
    suppliers_table.column("Phone", width=120, anchor="w")

    suppliers_table.heading("Email", text="Email")
    suppliers_table.column("Email", width=150, anchor="w")

    suppliers_table.heading("Address", text="Address")
    suppliers_table.column("Address", width=200, anchor="w")

    suppliers_table.heading("Rating", text="Rating")
    suppliers_table.column("Rating", width=80, anchor="center")

    suppliers_table.pack(fill=tk.BOTH, expand=True)

    # Load suppliers data
    db = connect_db()
    if db:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM suppliers")
        records = cursor.fetchall()
        db.close()

        # Populate table with data
        for record in records:
            suppliers_table.insert("", tk.END, values=record)

def show_dashboard(parent):
    clear_frame(parent)
    create_title_bar(parent, "Dashboard")

    # Create cards for key metrics
    cards_frame = tk.Frame(parent, bg=COLORS["light"])
    cards_frame.pack(fill=tk.X, padx=20, pady=10)

    # Total Products
    total_products = get_total_products()
    card1 = create_card(cards_frame, "Total Products", total_products, "📦", COLORS["primary"])
    card1.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

    # Total Sales
    total_sales = get_total_sales()
    card2 = create_card(cards_frame, "Total Sales", f"Rs{total_sales:.2f}", "💰", COLORS["success"])
    card2.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

    # Low Stock Items
    low_stock = get_low_stock_items()
    card3 = create_card(cards_frame, "Low Stock Items", low_stock, "⚠️", COLORS["warning"])
    card3.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")

    # Total Orders
    total_orders = get_total_orders()
    card4 = create_card(cards_frame, "Total Orders", total_orders, "🛒", COLORS["accent"])
    card4.grid(row=0, column=3, padx=10, pady=10, sticky="nsew")

    # Configure grid
    for i in range(4):
        cards_frame.columnconfigure(i, weight=1)

    # Add charts section
    charts_frame = tk.Frame(parent, bg=COLORS["light"])
    charts_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

    # Left chart - Inventory by category
    left_chart_frame = tk.Frame(charts_frame, bg="white", padx=15, pady=15,
                               highlightbackground=COLORS["secondary"], highlightthickness=1)
    left_chart_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

    tk.Label(left_chart_frame, text="Inventory by Category", font=("Montserrat", 14, "bold"),
            bg="white", fg=COLORS["dark"]).pack(anchor="w", pady=(0, 10))

    # Get categories data
    db = connect_db()
    if db:
        cursor = db.cursor()
        cursor.execute("SELECT category, SUM(quantity) FROM garments GROUP BY category")
        categories = cursor.fetchall()
        db.close()

        # Create figure
        fig, ax = plt.subplots(figsize=(6, 4))

        # If we have data, create a pie chart
        if categories:
            labels = [c[0] for c in categories]
            sizes = [c[1] for c in categories]

            # Custom colors
            colors = ['#1a237e', '#283593', '#303f9f', '#3949ab', '#3f51b5', '#5c6bc0', '#7986cb']

            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors[:len(labels)])
            ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
        else:
            ax.text(0.5, 0.5, "No data available", ha='center', va='center', fontsize=12)
            ax.axis('off')

        # Embed the chart
        chart_widget = FigureCanvasTkAgg(fig, left_chart_frame)
        chart_widget.draw()
        chart_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)

def view_sales_reports(parent):
    clear_frame(parent)
    create_title_bar(parent, "Sales Reports")

    # Create sales table
    table_frame = tk.Frame(parent, bg=COLORS["light"], padx=20, pady=20)
    table_frame.pack(fill=tk.BOTH, expand=True)

    # Scrollbars
    table_scroll_y = tk.Scrollbar(table_frame)
    table_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

    table_scroll_x = tk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
    table_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

    # Treeview for sales table
    columns = ("ID", "Garment", "Quantity", "Sale Price", "Profit", "Sale Date", "User")

    style = ttk.Style()
    style.configure("Treeview", font=("Montserrat", 12), rowheight=30)
    style.configure("Treeview.Heading", font=("Montserrat", 12, "bold"))

    sales_table = ttk.Treeview(table_frame, columns=columns, show="headings",
                              yscrollcommand=table_scroll_y.set,
                              xscrollcommand=table_scroll_x.set)

    table_scroll_y.config(command=sales_table.yview)
    table_scroll_x.config(command=sales_table.xview)

    # Define column headings and widths
    sales_table.heading("ID", text="ID")
    sales_table.column("ID", width=50, anchor="center")

    sales_table.heading("Garment", text="Garment")
    sales_table.column("Garment", width=150, anchor="w")

    sales_table.heading("Quantity", text="Quantity")
    sales_table.column("Quantity", width=100, anchor="center")

    sales_table.heading("Sale Price", text="Sale Price")
    sales_table.column("Sale Price", width=120, anchor="e")

    sales_table.heading("Profit", text="Profit")
    sales_table.column("Profit", width=120, anchor="e")

    sales_table.heading("Sale Date", text="Sale Date")
    sales_table.column("Sale Date", width=150, anchor="w")

    sales_table.heading("User", text="User")
    sales_table.column("User", width=150, anchor="w")

    sales_table.pack(fill=tk.BOTH, expand=True)

    # Load sales data
    db = connect_db()
    if db:
        cursor = db.cursor()
        cursor.execute("""
            SELECT s.id, g.garment_name, s.quantity, s.sale_price, s.profit, s.sale_date, u.username
            FROM sales s
            JOIN garments g ON s.garment_id = g.id
            JOIN users u ON s.user_id = u.id
        """)
        records = cursor.fetchall()
        db.close()

        # Populate table with data
        for record in records:
            sales_table.insert("", tk.END, values=record)

def manage_users(parent):
    clear_frame(parent)
    create_title_bar(parent, "User Management")

    # Create users table
    table_frame = tk.Frame(parent, bg=COLORS["light"], padx=20, pady=20)
    table_frame.pack(fill=tk.BOTH, expand=True)

    # Scrollbars
    table_scroll_y = tk.Scrollbar(table_frame)
    table_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

    table_scroll_x = tk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
    table_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

    # Treeview for users table
    columns = ("ID", "Username", "Role", "Email", "Last Login")

    style = ttk.Style()
    style.configure("Treeview", font=("Montserrat", 12), rowheight=30)
    style.configure("Treeview.Heading", font=("Montserrat", 12, "bold"))

    users_table = ttk.Treeview(table_frame, columns=columns, show="headings",
                              yscrollcommand=table_scroll_y.set,
                              xscrollcommand=table_scroll_x.set)

    table_scroll_y.config(command=users_table.yview)
    table_scroll_x.config(command=users_table.xview)

    # Define column headings and widths
    users_table.heading("ID", text="ID")
    users_table.column("ID", width=50, anchor="center")

    users_table.heading("Username", text="Username")
    users_table.column("Username", width=150, anchor="w")

    users_table.heading("Role", text="Role")
    users_table.column("Role", width=100, anchor="w")

    users_table.heading("Email", text="Email")
    users_table.column("Email", width=200, anchor="w")

    users_table.heading("Last Login", text="Last Login")
    users_table.column("Last Login", width=150, anchor="w")

    users_table.pack(fill=tk.BOTH, expand=True)

    # Load users data
    db = connect_db()
    if db:
        cursor = db.cursor()
        cursor.execute("SELECT id, username, role, email, last_login FROM users")
        records = cursor.fetchall()
        db.close()

        # Populate table with data
        for record in records:
            users_table.insert("", tk.END, values=record)

def manage_settings(parent):
    clear_frame(parent)
    create_title_bar(parent, "Settings")

    # Create settings form
    form_frame = tk.Frame(parent, bg=COLORS["light"], padx=20, pady=20)
    form_frame.pack(fill=tk.BOTH, expand=True)

    # Inventory Threshold
    tk.Label(form_frame, text="Inventory Threshold:", font=("Montserrat", 12),
            bg=COLORS["light"], fg=COLORS["dark"]).grid(row=0, column=0, sticky="w", pady=10)
    threshold_entry = tk.Entry(form_frame, font=("Montserrat", 12), width=10)
    threshold_entry.grid(row=0, column=1, sticky="w", pady=10)
    threshold_entry.insert(0, str(inventory_threshold))

    # Save button
    def save_settings():
        new_threshold = int(threshold_entry.get())
        global inventory_threshold
        inventory_threshold = new_threshold

        db = connect_db()
        if db:
            cursor = db.cursor()
            cursor.execute("UPDATE settings SET setting_value = %s WHERE setting_name = 'inventory_threshold'",
                           (new_threshold,))
            db.commit()
            db.close()
            show_notification(parent, "Settings saved successfully!", "success")

    save_btn = tk.Button(form_frame, text="Save", font=("Montserrat", 12, "bold"),
                        bg=COLORS["primary"], fg="white", padx=20, pady=5,
                        command=save_settings)
    save_btn.grid(row=1, column=0, columnspan=2, pady=20)

                                            

# UI Effects and Animations
def shake_animation(widget, offset=10, repeats=5):
    def shake(count, direction):
        if count > 0:
            widget.place(x=widget._original_x + offset * direction, y=widget._original_y)
            widget.after(50, lambda: shake(count - 1, -direction))
        else:
            widget.place(x=widget._original_x, y=widget._original_y)
    
    widget._original_x = widget.winfo_x()
    widget._original_y = widget.winfo_y()
    shake(repeats, 1)

def loading_animation(parent):
    # Create a semi-transparent overlay
    overlay = tk.Frame(parent, bg="#000000", bd=0, highlightthickness=0)
    overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
    overlay.attributes("-alpha", 0.7)
    
    # Create a loading frame
    loading_frame = tk.Frame(overlay, bg=COLORS["light"], padx=40, pady=40,
                            highlightbackground=COLORS["primary"], highlightthickness=2)
    loading_frame.place(relx=0.5, rely=0.5, anchor="center")
    
    # Loading text
    loading_label = tk.Label(loading_frame, text="Logging in...", font=("Montserrat", 18, "bold"),
                            bg=COLORS["light"], fg=COLORS["primary"])
    loading_label.pack(pady=20)
    
    # Progress bar
    style = ttk.Style()
    style.theme_use('clam')
    style.configure("color.Horizontal.TProgressbar", background=COLORS["accent"])
    
    progress = ttk.Progressbar(loading_frame, style="color.Horizontal.TProgressbar", 
                              length=300, mode='determinate')
    progress.pack(pady=10)
    
    # Simulate progress
    def update_progress(val=0):
        if val <= 100:
            progress['value'] = val
            parent.after(20, lambda: update_progress(val + 2))
        else:
            overlay.destroy()
    
    update_progress()

def success_animation(parent):
    # Create a success icon in the center of the screen
    success_frame = tk.Frame(parent, bg=COLORS["success"], width=100, height=100,
                            highlightthickness=0, bd=0)
    success_frame.place(relx=0.5, rely=0.5, anchor="center")
    success_frame.configure(borderwidth=0, highlightthickness=0)
    
    # Check mark
    check = tk.Label(success_frame, text="✓", font=("Arial", 50), bg=COLORS["success"], fg="white")
    check.place(relx=0.5, rely=0.5, anchor="center")
    
    # Animate success icon
    def grow_and_fade():
        for i in range(10):
            size = 100 + (i * 10)
            success_frame.configure(width=size, height=size)
            parent.update()
            time.sleep(0.05)
        
        # Fade out
        for i in range(10, 0, -1):
            alpha = i / 10
            success_frame.attributes("-alpha", alpha)
            parent.update()
            time.sleep(0.05)
        
        success_frame.destroy()
    
    threading.Thread(target=grow_and_fade).start()

def show_notification(parent, message, type="info"):
    # Define colors based on type
    bg_colors = {
        "info": COLORS["secondary"],
        "success": COLORS["success"],
        "warning": COLORS["warning"],
        "danger": COLORS["danger"]
    }
    
    # Store notification for alerts page
    global notifications
    notifications.append({
        "message": message,
        "type": type,
        "timestamp": datetime.now()
    })
    
    # Create notification frame
    notif = tk.Frame(parent, bg=bg_colors.get(type, COLORS["secondary"]), padx=20, pady=10)
    notif.place(relx=0.5, rely=0.1, anchor="n")
    
    # Notification text
    msg = tk.Label(notif, text=message, font=("Montserrat", 12), bg=bg_colors.get(type, COLORS["secondary"]),
                  fg="white" if type != "warning" else "black")
    msg.pack(side=tk.LEFT, padx=10)
    
    # Close button
    close = tk.Label(notif, text="×", font=("Arial", 16), bg=bg_colors.get(type, COLORS["secondary"]),
                    fg="white" if type != "warning" else "black", cursor="hand2")
    close.pack(side=tk.RIGHT)
    close.bind("<Button-1>", lambda e: notif.destroy())
    
    # Auto-close after 3 seconds
    parent.after(3000, notif.destroy)

# Main Application Pages
def home_page(username, role):
    home = tk.Tk()
    home.geometry("2056x1028")
    home.title("Garment Inventory Management")
    home.configure(bg=COLORS["light"])
    
    # Load settings
    load_settings()
    
    # Check for low inventory items and add notifications
    check_low_inventory()
    
    # Main container with two panels
    main_container = tk.Frame(home, bg=COLORS["light"])
    main_container.pack(fill=tk.BOTH, expand=True)
    
    # Left sidebar (navigation)
    sidebar = tk.Frame(main_container, bg=COLORS["primary"], width=250)
    sidebar.pack(side=tk.LEFT, fill=tk.Y)
    sidebar.pack_propagate(False)  # Keep width fixed
    
    # App logo/title
    logo_frame = tk.Frame(sidebar, bg=COLORS["primary"], height=150)
    logo_frame.pack(fill=tk.X)
    logo_frame.pack_propagate(False)
    
    logo_text = tk.Label(logo_frame, text="G-Inventory", font=("Montserrat", 24, "bold"),
                        bg=COLORS["primary"], fg="white")
    logo_text.place(relx=0.5, rely=0.5, anchor="center")
    
    # User info
    user_frame = tk.Frame(sidebar, bg=COLORS["primary"], height=100)
    user_frame.pack(fill=tk.X)
    
    user_icon = tk.Label(user_frame, text="👤", font=("Arial", 24),
                       bg=COLORS["primary"], fg="white")
    user_icon.pack(pady=(10, 0))
    
    user_name = tk.Label(user_frame, text=(current_user["username"].capitalize() if current_user else "Guest"),
                     font=("Montserrat", 14, "bold"),
                     bg=COLORS["primary"], fg="white")
    user_name.pack()
    
    user_role = tk.Label(user_frame, text=f"Role: {current_role.capitalize()}",
                        font=("Montserrat", 12),
                        bg=COLORS["primary"], fg=COLORS["secondary"])
    user_role.pack(pady=(0, 10))
    
    # Create navigation buttons with icons
    nav_buttons = [
        {"text": "Dashboard", "icon": "📊", "command": lambda: show_dashboard(content_frame)},
        {"text": "Inventory", "icon": "📦", "command": lambda: display_inventory(content_frame)},
        {"text": "Orders", "icon": "🛒", "command": lambda: view_orders(content_frame)},
        {"text": "Suppliers", "icon": "🏭", "command": lambda: view_suppliers(content_frame)},
        {"text": "Sales Reports", "icon": "📈", "command": lambda: view_sales_reports(content_frame)},
        {"text": "User Management", "icon": "👥", "command": lambda: manage_users(content_frame)},
        {"text": "Settings", "icon": "⚙️", "command": lambda: manage_settings(content_frame)},
        {"text": "Logout", "icon": "🚪", "command": home.destroy}
    ]
    
    # Create navigation menu
    nav_frame = tk.Frame(sidebar, bg=COLORS["primary"])
    nav_frame.pack(fill=tk.BOTH, expand=True, pady=20)
    
    for button in nav_buttons:
        btn_frame = tk.Frame(nav_frame, bg=COLORS["primary"])
        btn_frame.pack(fill=tk.X, pady=5)
        
        icon_label = tk.Label(btn_frame, text=button["icon"], font=("Arial", 16),
                             bg=COLORS["primary"], fg="white", width=2)
        icon_label.pack(side=tk.LEFT, padx=20)
        
        btn = tk.Button(btn_frame, text=button["text"], command=button["command"],
                       font=("Montserrat", 12), bg=COLORS["primary"], fg="white",
                       activebackground=COLORS["secondary"], activeforeground="white",
                       bd=0, relief=tk.FLAT, anchor="w", padx=10, cursor="hand2")
        btn.pack(fill=tk.X, padx=5, ipady=8)
    
    # Main content area
    content_frame = tk.Frame(main_container, bg=COLORS["light"])
    content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
    
    # Show dashboard by default
    show_dashboard(content_frame)
    
    home.mainloop()

# Clear frame function
def clear_frame(frame):
    for widget in frame.winfo_children():
        widget.destroy()

# Create title bar
def create_title_bar(parent, title):
    title_frame = tk.Frame(parent, bg=COLORS["light"], height=80)
    title_frame.pack(fill=tk.X, padx=20, pady=(20, 10))
    
    # Title with underline
    title_label = tk.Label(title_frame, text=title, font=("Montserrat", 24, "bold"),
                          bg=COLORS["light"], fg=COLORS["primary"])
    title_label.pack(side=tk.LEFT)
    
    # Current date and time
    date_label = tk.Label(title_frame, text=datetime.now().strftime("%d %b %Y, %I:%M %p"),
                         font=("Montserrat", 12),
                         bg=COLORS["light"], fg=COLORS["dark"])
    date_label.pack(side=tk.RIGHT, padx=20)
    
    # Divider
    divider = tk.Frame(parent, height=2, bg=COLORS["secondary"])
    divider.pack(fill=tk.X, padx=20, pady=(0, 20))

# Check low inventory
def check_low_inventory():
    """Check for inventory items below threshold and add to notifications"""
    db = connect_db()
    if not db:
        return
        
    cursor = db.cursor()
    cursor.execute(f"SELECT id, garment_name, quantity FROM garments WHERE quantity < {inventory_threshold}")
    low_items = cursor.fetchall()
    db.close()
    
    global notifications
    for item in low_items:
        item_id, name, qty = item
        notifications.append({
            "message": f"Low inventory alert: {name} (only {qty} left)",
            "type": "warning",
            "timestamp": datetime.now()
        })

# View orders
def view_orders(parent):
    clear_frame(parent)
    create_title_bar(parent, "View Orders")

    # Get stats from database
    db = connect_db()
    if not db:
        return
    
    cursor = db.cursor()

    # Get total order count
    cursor.execute("SELECT COUNT(*) FROM orders")
    total_orders = cursor.fetchone()[0]

    # Get total orders
    cursor.execute("SELECT SUM(quantity) FROM orders")
    total_number = cursor.fetchone()[0]

    # Display orders in a table
    orders_frame = tk.Frame(parent, bg=COLORS["light"])
    orders_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

    # Treeview for orders
    columns = ("Order ID", "Garment", "Quantity", "Status", "Customer", "Order Date")
    orders_table = ttk.Treeview(orders_frame, columns=columns, show="headings")
    
    for col in columns:
        orders_table.heading(col, text=col)
    
    # Fetch orders from database
    cursor.execute("""
        SELECT o.id, g.garment_name, o.quantity, o.status, o.customer_name, o.order_date 
        FROM orders o
        JOIN garments g ON o.garment_id = g.id
    """)
    orders = cursor.fetchall()
    
    for order in orders:
        orders_table.insert("", tk.END, values=order)
    
    orders_table.pack(fill=tk.BOTH, expand=True)
    
    db.close()

def create_card(parent, title, value, icon, color, command=None):
    card = tk.Frame(parent, bg="white", padx=20, pady=15,
                   highlightbackground=color, highlightthickness=1)
    if command:
        card.bind("<Button-1>", lambda e: command())
        card.configure(cursor="hand2")
    
    # Icon
    icon_label = tk.Label(card, text=icon, font=("Arial", 28),
                         bg="white", fg=color)
    icon_label.pack(anchor="w")
    
    # Value in large font
    value_label = tk.Label(card, text=value, font=("Montserrat", 24, "bold"),
                          bg="white", fg=COLORS["dark"])
    value_label.pack(anchor="w")
    
    # Title
    title_label = tk.Label(card, text=title, font=("Montserrat", 12),
                          bg="white", fg=COLORS["dark"])
    title_label.pack(anchor="w")
    
    return card


# Show dashboard
def show_dashboard(parent):
    clear_frame(parent)
    create_title_bar(parent, "Dashboard")
    
    # Get stats from database
    db = connect_db()
    if not db:
        return
        
    cursor = db.cursor()
    
    # Get total inventory count
    cursor.execute("SELECT COUNT(*) FROM garments")
    total_items = cursor.fetchone()[0]
    
    # Get total inventory value
    cursor.execute("SELECT SUM(quantity * price) FROM garments")
    result = cursor.fetchone()[0]
    total_value = f"Rs{result:.2f}" if result else "Rs0.00"
    
    # Get low stock items
    cursor.execute(f"SELECT COUNT(*) FROM garments WHERE quantity < {inventory_threshold}")
    low_stock = cursor.fetchone()[0]
    
    # Get orders count
    cursor.execute("SELECT COUNT(*) FROM orders")
    total_orders = cursor.fetchone()[0]
    
    db.close()
    
    # Create cards in a grid layout
    cards_frame = tk.Frame(parent, bg=COLORS["light"])
    cards_frame.pack(fill=tk.X, padx=20, pady=10)
    
    card1 = create_card(cards_frame, "Total Products", total_items, "📦", COLORS["primary"],
                       lambda: display_inventory(parent))
    card1.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
    
    card2 = create_card(cards_frame, "Inventory Value", total_value, "💰", COLORS["success"])
    card2.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
    
    card3 = create_card(cards_frame, "Low Stock Items", low_stock, "⚠️", COLORS["warning"])
    card3.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
    
    card4 = create_card(cards_frame, "Total Orders", total_orders, "🛒", COLORS["accent"],
                       lambda: view_orders(parent))
    card4.grid(row=0, column=3, padx=10, pady=10, sticky="nsew")
    
    # Configure grid
    for i in range(4):
        cards_frame.columnconfigure(i, weight=1)
    
    # Add charts section
    charts_frame = tk.Frame(parent, bg=COLORS["light"])
    charts_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
    
    # Left chart - Inventory by category
    left_chart_frame = tk.Frame(charts_frame, bg="white", padx=15, pady=15,
                               highlightbackground=COLORS["secondary"], highlightthickness=1)
    left_chart_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
    
    tk.Label(left_chart_frame, text="Inventory by Category", font=("Montserrat", 14, "bold"),
            bg="white", fg=COLORS["dark"]).pack(anchor="w", pady=(0, 10))
    
    # Get categories data
    db = connect_db()
    if db:
        cursor = db.cursor()
        cursor.execute("SELECT category, SUM(quantity) FROM garments GROUP BY category")
        categories = cursor.fetchall()
        db.close()
        
        # Create figure
        fig, ax = plt.subplots(figsize=(6, 4))
        
        # If we have data, create a pie chart
        if categories:
            labels = [c[0] for c in categories]
            sizes = [c[1] for c in categories]
            
            # Custom colors
            colors = ['#1a237e', '#283593', '#303f9f', '#3949ab', '#3f51b5', '#5c6bc0', '#7986cb']
            
            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors[:len(labels)])
            ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
        else:
            ax.text(0.5, 0.5, "No data available", ha='center', va='center', fontsize=12)
            ax.axis('off')
        
        # Embed the chart
        chart_widget = FigureCanvasTkAgg(fig, left_chart_frame)
        chart_widget.draw()
        chart_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    # Right chart - Monthly sales
    right_chart_frame = tk.Frame(charts_frame, bg="white", padx=15, pady=15,
                                highlightbackground=COLORS["secondary"], highlightthickness=1)
    right_chart_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
    
    tk.Label(right_chart_frame, text="Monthly Sales Trend", font=("Montserrat", 14, "bold"),
            bg="white", fg=COLORS["dark"]).pack(anchor="w", pady=(0, 10))
    
    # Sample sales data (or get from database if available)
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
    sales = [random.randint(5000, 15000) for _ in range(6)]
    
    # Create figure
    fig2, ax2 = plt.subplots(figsize=(6, 4))
    
    # Create line chart
    ax2.plot(months, sales, marker='o', linestyle='-', color=COLORS["primary"], linewidth=2)
    ax2.set_ylabel('Sales (Rs)')
    ax2.grid(True, linestyle='--', alpha=0.7)
    
    # Embed the chart
    chart_widget2 = FigureCanvasTkAgg(fig2, right_chart_frame)
    chart_widget2.draw()
    chart_widget2.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    # Configure grid
    charts_frame.columnconfigure(0, weight=1)
    charts_frame.columnconfigure(1, weight=1)
    charts_frame.rowconfigure(0, weight=1)
    
    # Recent activities section
    activities_frame = tk.Frame(parent, bg="white", padx=15, pady=15,
                              highlightbackground=COLORS["secondary"], highlightthickness=1)
    activities_frame.pack(fill=tk.X, padx=20, pady=10)
    
    tk.Label(activities_frame, text="Recent Activities", font=("Montserrat", 14, "bold"),
            bg="white", fg=COLORS["dark"]).pack(anchor="w", pady=(0, 10))
    
    # Get recent activities from log
    db = connect_db()
    if db:
        cursor = db.cursor()
        cursor.execute("""
            SELECT u.username, a.activity, a.timestamp 
            FROM activity_log a 
            JOIN users u ON a.user_id = u.id 
            ORDER BY a.timestamp DESC LIMIT 5
        """)
        activities = cursor.fetchall()
        db.close()
        
        if activities:
            for activity in activities:
                username, action, timestamp = activity
                time_str = timestamp.strftime("%d %b, %I:%M %p")
                
                activity_item = tk.Frame(activities_frame, bg="white", pady=5)
                activity_item.pack(fill=tk.X)
                
                tk.Label(activity_item, text=f"👤 {username}", font=("Montserrat", 12, "bold"),
                        bg="white", fg=COLORS["primary"], width=15, anchor="w").pack(side=tk.LEFT)
                
                tk.Label(activity_item, text=action, font=("Montserrat", 12),
                        bg="white", fg=COLORS["dark"]).pack(side=tk.LEFT, padx=10)
                
                tk.Label(activity_item, text=time_str, font=("Montserrat", 10),
                        bg="white", fg=COLORS["secondary"]).pack(side=tk.RIGHT)
                
                # Add separator except for last item
                if activity != activities[-1]:
                    tk.Frame(activities_frame, height=1, bg=COLORS["light"]).pack(fill=tk.X, pady=5)
        else:
            tk.Label(activities_frame, text="No recent activities", font=("Montserrat", 12),
                    bg="white", fg=COLORS["dark"]).pack(pady=10)

# Display inventory
def display_inventory(parent):
    clear_frame(parent)
    create_title_bar(parent, "Inventory Management")
    
    # Create search and filter bar
    search_frame = tk.Frame(parent, bg=COLORS["light"], pady=10)
    search_frame.pack(fill=tk.X, padx=20)
    
    # Search input
    search_container = tk.Frame(search_frame, bg="white", highlightbackground=COLORS["secondary"],
                              highlightthickness=1, padx=10)
    search_container.pack(side=tk.LEFT)
    
    search_icon = tk.Label(search_container, text="🔍", bg="white")
    search_icon.pack(side=tk.LEFT)
    
    search_entry = tk.Entry(search_container, font=("Montserrat", 12), bd=0, bg="white", width=25)
    search_entry.pack(side=tk.LEFT, ipady=8, padx=5)
    search_entry.insert(0, "Search products...")
    
    # Clear on focus
    def on_entry_click(event):
        if search_entry.get() == "Search products...":
            search_entry.delete(0, tk.END)
            search_entry.config(fg=COLORS["dark"])
    
    # Reset if empty on focus out
    def on_focus_out(event):
        if search_entry.get() == "":
            search_entry.insert(0, "Search products...")
            search_entry.config(fg=COLORS["secondary"])
    
    search_entry.bind("<FocusIn>", on_entry_click)
    search_entry.bind("<FocusOut>", on_focus_out)
    search_entry.config(fg=COLORS["secondary"])
    
    # Category filter
    tk.Label(search_frame, text="Category:", font=("Montserrat", 12),
            bg=COLORS["light"], fg=COLORS["dark"]).pack(side=tk.LEFT, padx=(20, 5))
    
    category_filter = ttk.Combobox(search_frame, values=["All", "T-Shirts", "Pants", "Dresses", "Jackets"],
                                  font=("Montserrat", 12), width=15, state="readonly")
    category_filter.current(0)
    category_filter.pack(side=tk.LEFT)
    
    # Size filter
    tk.Label(search_frame, text="Size:", font=("Montserrat", 12),
            bg=COLORS["light"], fg=COLORS["dark"]).pack(side=tk.LEFT, padx=(20, 5))
    
    size_filter = ttk.Combobox(search_frame, values=["All", "S", "M", "L", "XL", "XXL"],
                              font=("Montserrat", 12), width=10, state="readonly")
    size_filter.current(0)
    size_filter.pack(side=tk.LEFT)
    
    # Add new garment button (only for admin)
    if current_role == 'admin':
        add_btn = tk.Button(search_frame, text="Add New Product", font=("Montserrat", 12, "bold"),
                          bg=COLORS["primary"], fg="white", padx=15, pady=5,
                          command=lambda: add_garment_form(parent))
        add_btn.pack(side=tk.RIGHT)
    
    # Create inventory table
    table_frame = tk.Frame(parent, bg=COLORS["light"], padx=20, pady=20)
    table_frame.pack(fill=tk.BOTH, expand=True)
    
    # Scrollbars
    table_scroll_y = tk.Scrollbar(table_frame)
    table_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
    
    table_scroll_x = tk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
    table_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
    
    # Treeview for inventory table
    columns = ("ID", "Name", "Category", "Size", "Color", "Quantity", "Price", "Value", "Supplier")
    
    style = ttk.Style()
    style.configure("Treeview", font=("Montserrat", 12), rowheight=30)
    style.configure("Treeview.Heading", font=("Montserrat", 12, "bold"))
    
    inventory_table = ttk.Treeview(table_frame, columns=columns, show="headings",
                                  yscrollcommand=table_scroll_y.set,
                                  xscrollcommand=table_scroll_x.set)
    
    table_scroll_y.config(command=inventory_table.yview)
    table_scroll_x.config(command=inventory_table.xview)
    
    # Define column headings and widths
    inventory_table.heading("ID", text="ID")
    inventory_table.column("ID", width=50, anchor="center")
    
    inventory_table.heading("Name", text="Product Name")
    inventory_table.column("Name", width=200, anchor="w")
    
    inventory_table.heading("Category", text="Category")
    inventory_table.column("Category", width=120, anchor="w")
    
    inventory_table.heading("Size", text="Size")
    inventory_table.column("Size", width=80, anchor="center")
    
    inventory_table.heading("Color", text="Color")
    inventory_table.column("Color", width=100, anchor="w")
    
    inventory_table.heading("Quantity", text="Quantity")
    inventory_table.column("Quantity", width=100, anchor="center")
    
    inventory_table.heading("Price", text="Price")
    inventory_table.column("Price", width=100, anchor="e")
    
    inventory_table.heading("Value", text="Total Value")
    inventory_table.column("Value", width=120, anchor="e")
    
    inventory_table.heading("Supplier", text="Supplier")
    inventory_table.column("Supplier", width=150, anchor="w")
    
    inventory_table.pack(fill=tk.BOTH, expand=True)
    
    # Load inventory data
    db = connect_db()
    if db:
        cursor = db.cursor()
        cursor.execute("""
            SELECT g.id, g.garment_name, g.category, g.size, g.color, g.quantity, 
                   g.price, g.quantity * g.price as value, s.supplier_name
            FROM garments g
            LEFT JOIN suppliers s ON g.supplier_id = s.id
            ORDER BY g.id
        """)
        records = cursor.fetchall()
        db.close()
        
        # Populate table with data
        for i, record in enumerate(records):
            # Format price and value
            record_list = list(record)
            record_list[6] = f"Rs{record[6]:.2f}"
            record_list[7] = f"Rs{record[7]:.2f}"
            
            # Highlight low inventory items in red
            if record[5] < inventory_threshold:
                inventory_table.insert("", tk.END, values=record_list, tags=("low_stock",))
            else:
                inventory_table.insert("", tk.END, values=record_list, tags=("normal",))
            
            # Alternate row colors
            if i % 2 == 0:
                inventory_table.tag_configure("normal", background="white")
                inventory_table.tag_configure("low_stock", background="#ffe6e6", foreground="#d32f2f")
            else:
                inventory_table.tag_configure("normal", background="#f5f5f5")
                inventory_table.tag_configure("low_stock", background="#ffcccc", foreground="#d32f2f")
    
    # Add context menu
    def show_context_menu(event):
        try:
            item = inventory_table.identify_row(event.y)
            if item:
                # Get selected item ID
                selected_id = inventory_table.item(item, "values")[0]
                
                # Create context menu
                context = tk.Menu(parent, tearoff=0)
                context.add_command(label="View Details", 
                                   command=lambda: view_item_details(parent, selected_id))
                
                if current_role == 'admin':
                    context.add_command(label="Edit Item", 
                                       command=lambda: edit_item(parent, selected_id))
                    context.add_command(label="Delete Item", 
                                       command=lambda: delete_item(parent, selected_id))
                
                context.add_separator()
                context.add_command(label="Add to Order", 
                                   command=lambda: add_to_order(parent, selected_id))
                
                context.post(event.x_root, event.y_root)
        except:
            pass
    
    inventory_table.bind("<Button-3>", show_context_menu)
    
    # Add double-click event for viewing details
    inventory_table.bind("<Double-1>", lambda event: view_item_details(
        parent, inventory_table.item(inventory_table.selection()[0], "values")[0] if inventory_table.selection() else None))
    
    # Pagination controls
    pagination_frame = tk.Frame(parent, bg=COLORS["light"], pady=10)
    pagination_frame.pack(fill=tk.X, padx=20)
    
    tk.Label(pagination_frame, text=f"Total items: {len(records) if 'records' in locals() else 0}",
            font=("Montserrat", 12), bg=COLORS["light"], fg=COLORS["dark"]).pack(side=tk.LEFT)
    
    # Page navigation
    pages_frame = tk.Frame(pagination_frame, bg=COLORS["light"])
    pages_frame.pack(side=tk.RIGHT)
    
    prev_btn = tk.Button(pages_frame, text="Previous", font=("Montserrat", 10),
                        bg=COLORS["light"], fg=COLORS["primary"])
    prev_btn.pack(side=tk.LEFT, padx=5)
    
    # Page buttons (1, 2, 3, etc.)
    for i in range(1, min(4, (len(records) // 10) + 2) if 'records' in locals() else 2):
        page_btn = tk.Button(pages_frame, text=str(i), font=("Montserrat", 10),
                           bg=COLORS["primary"] if i == 1 else COLORS["light"],
                           fg="white" if i == 1 else COLORS["primary"],
                           width=3)
        page_btn.pack(side=tk.LEFT, padx=2)
    
    next_btn = tk.Button(pages_frame, text="Next", font=("Montserrat", 10),
                        bg=COLORS["light"], fg=COLORS["primary"])
    next_btn.pack(side=tk.LEFT, padx=5)

# Add garment form
def add_garment_form(parent):
    """Form for adding a new garment"""
    # Create a popup window
    popup = tk.Toplevel()
    popup.title("Add New Product")
    popup.geometry("600x700")
    popup.configure(bg=COLORS["light"])
    
    tk.Label(popup, text="Add New Product", font=("Montserrat", 18, "bold"),
            bg=COLORS["light"], fg=COLORS["primary"]).pack(pady=20)
    
    # Create form frame
    form = tk.Frame(popup, bg=COLORS["light"], padx=20)
    form.pack(fill=tk.BOTH, expand=True)
    
    # Product name
    tk.Label(form, text="Product Name", font=("Montserrat", 12),
            bg=COLORS["light"], fg=COLORS["dark"]).grid(row=0, column=0, sticky="w", pady=10)
    product_name = tk.Entry(form, font=("Montserrat", 12), width=40)
    product_name.grid(row=0, column=1, sticky="w", pady=10)
    
    # Category
    tk.Label(form, text="Category", font=("Montserrat", 12),
            bg=COLORS["light"], fg=COLORS["dark"]).grid(row=1, column=0, sticky="w", pady=10)
    category = ttk.Combobox(form, values=["T-Shirts", "Pants", "Dresses", "Jackets", "Accessories"],
                           font=("Montserrat", 12), width=20, state="readonly")
    category.grid(row=1, column=1, sticky="w", pady=10)
    category.current(0)
    
    # Size
    tk.Label(form, text="Size", font=("Montserrat", 12),
            bg=COLORS["light"], fg=COLORS["dark"]).grid(row=2, column=0, sticky="w", pady=10)
    size = ttk.Combobox(form, values=["S", "M", "L", "XL", "XXL"],
                       font=("Montserrat", 12), width=10, state="readonly")
    size.grid(row=2, column=1, sticky="w", pady=10)
    size.current(0)
    
    # Color
    tk.Label(form, text="Color", font=("Montserrat", 12),
            bg=COLORS["light"], fg=COLORS["dark"]).grid(row=3, column=0, sticky="w", pady=10)
    color = tk.Entry(form, font=("Montserrat", 12), width=20)
    color.grid(row=3, column=1, sticky="w", pady=10)
    
    # Quantity
    tk.Label(form, text="Quantity", font=("Montserrat", 12),
            bg=COLORS["light"], fg=COLORS["dark"]).grid(row=4, column=0, sticky="w", pady=10)
    quantity = tk.Spinbox(form, from_=0, to=1000, font=("Montserrat", 12), width=10)
    quantity.grid(row=4, column=1, sticky="w", pady=10)
    
    # Price
    tk.Label(form, text="Price (Rs)", font=("Montserrat", 12),
            bg=COLORS["light"], fg=COLORS["dark"]).grid(row=5, column=0, sticky="w", pady=10)
    price = tk.Entry(form, font=("Montserrat", 12), width=15)
    price.grid(row=5, column=1, sticky="w", pady=10)
    
    # Cost Price
    tk.Label(form, text="Cost Price (Rs)", font=("Montserrat", 12),
            bg=COLORS["light"], fg=COLORS["dark"]).grid(row=6, column=0, sticky="w", pady=10)
    cost_price = tk.Entry(form, font=("Montserrat", 12), width=15)
    cost_price.grid(row=6, column=1, sticky="w", pady=10)
    
    # Supplier
    tk.Label(form, text="Supplier", font=("Montserrat", 12),
            bg=COLORS["light"], fg=COLORS["dark"]).grid(row=7, column=0, sticky="w", pady=10)
    
    # Get suppliers from database
    db = connect_db()
    suppliers = []
    supplier_ids = {}
    
    if db:
        cursor = db.cursor()
        cursor.execute("SELECT id, supplier_name FROM suppliers")
        for sid, name in cursor.fetchall():
            suppliers.append(name)
            supplier_ids[name] = sid
        db.close()
    
    supplier = ttk.Combobox(form, values=suppliers,
                           font=("Montserrat", 12), width=25, state="readonly")
    supplier.grid(row=7, column=1, sticky="w", pady=10)
    if suppliers:
        supplier.current(0)
    
    # Add a new supplier button
    add_supplier_btn = tk.Button(form, text="+", font=("Arial", 14, "bold"),
                               bg=COLORS["primary"], fg="white", width=2,
                               command=lambda: add_new_supplier(popup, supplier))
    add_supplier_btn.grid(row=7, column=2, padx=5)
    
    # Description
    tk.Label(form, text="Description", font=("Montserrat", 12),
            bg=COLORS["light"], fg=COLORS["dark"]).grid(row=8, column=0, sticky="w", pady=10)
    description = tk.Text(form, font=("Montserrat", 12), width=40, height=5)
    description.grid(row=8, column=1, columnspan=2, sticky="w", pady=10)
    
    # Image upload placeholder
    tk.Label(form, text="Product Image", font=("Montserrat", 12),
            bg=COLORS["light"], fg=COLORS["dark"]).grid(row=9, column=0, sticky="w", pady=10)
    
    image_frame = tk.Frame(form, bg=COLORS["light"], width=150, height=150,
                          highlightbackground=COLORS["secondary"], highlightthickness=1)
    image_frame.grid(row=9, column=1, sticky="w", pady=10)
    image_frame.grid_propagate(False)
    
    upload_btn = tk.Button(image_frame, text="Upload Image", font=("Montserrat", 10),
                          bg=COLORS["secondary"], fg="white")
    upload_btn.place(relx=0.5, rely=0.5, anchor="center")
    
    # Button frame
    btn_frame = tk.Frame(popup, bg=COLORS["light"], pady=20)
    btn_frame.pack(fill=tk.X)
    
    # Save button function
    def save_product():
        # Validate inputs
        if not product_name.get() or not price.get() or not cost_price.get():
            show_notification(popup, "Please fill in all required fields", "warning")
            return
        
        try:
            price_val = float(price.get())
            cost_val = float(cost_price.get())
            qty_val = int(quantity.get())
        except ValueError:
            show_notification(popup, "Invalid number format", "danger")
            return
        
        # Get supplier id
        supplier_id = supplier_ids.get(supplier.get()) if supplier.get() in supplier_ids else None
        
        # Save to database
        db = connect_db()
        if db:
            cursor = db.cursor()
            try:
                cursor.execute("""
                    INSERT INTO garments 
                    (garment_name, category, size, color, quantity, price, cost_price, supplier_id) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    product_name.get(),
                    category.get(),
                    size.get(),
                    color.get(),
                    qty_val,
                    price_val,
                    cost_val,
                    supplier_id
                ))
                
                # Log activity
                cursor.execute("INSERT INTO activity_log (user_id, activity) VALUES (%s, %s)",
                              (current_user["id"], f"Added new product: {product_name.get()}"))
                
                db.commit()
                show_notification(popup, "Product added successfully!", "success")
                popup.after(1500, popup.destroy)
                
                # Refresh inventory display
                display_inventory(parent)
            except Exception as e:
                show_notification(popup, f"Error: {str(e)}", "danger")
            finally:
                db.close()
    
    # Save button
    save_btn = tk.Button(btn_frame, text="Save Product", command=save_product,
                        font=("Montserrat", 14, "bold"), 
                        bg=COLORS["primary"], fg="white", padx=30, pady=10)
    save_btn.pack(side=tk.RIGHT, padx=20)
    
    # Cancel button
    cancel_btn = tk.Button(btn_frame, text="Cancel", command=popup.destroy,
                          font=("Montserrat", 14), 
                          bg=COLORS["light"], fg=COLORS["primary"], padx=20, pady=10)
    cancel_btn.pack(side=tk.RIGHT)

# Add new supplier
def add_new_supplier(parent, supplier_combo):
    """Form to add a new supplier"""
    supplier_popup = tk.Toplevel(parent)
    supplier_popup.title("Add New Supplier")
    supplier_popup.geometry("500x400")
    supplier_popup.configure(bg=COLORS["light"])
    
    tk.Label(supplier_popup, text="Add New Supplier", font=("Montserrat", 16, "bold"),
            bg=COLORS["light"], fg=COLORS["primary"]).pack(pady=20)
    
    form = tk.Frame(supplier_popup, bg=COLORS["light"], padx=20)
    form.pack(fill=tk.BOTH, expand=True)
    
    # Supplier name
    tk.Label(form, text="Supplier Name", font=("Montserrat", 12),
            bg=COLORS["light"], fg=COLORS["dark"]).grid(row=0, column=0, sticky="w", pady=10)
    supplier_name = tk.Entry(form, font=("Montserrat", 12), width=30)
    supplier_name.grid(row=0, column=1, sticky="w", pady=10)
    
    # Contact person
    tk.Label(form, text="Contact Person", font=("Montserrat", 12),
            bg=COLORS["light"], fg=COLORS["dark"]).grid(row=1, column=0, sticky="w", pady=10)
    contact_person = tk.Entry(form, font=("Montserrat", 12), width=30)
    contact_person.grid(row=1, column=1, sticky="w", pady=10)
    
    # Phone
    tk.Label(form, text="Phone", font=("Montserrat", 12),
            bg=COLORS["light"], fg=COLORS["dark"]).grid(row=2, column=0, sticky="w", pady=10)
    phone = tk.Entry(form, font=("Montserrat", 12), width=20)
    phone.grid(row=2, column=1, sticky="w", pady=10)
    
    # Email
    tk.Label(form, text="Email", font=("Montserrat", 12),
            bg=COLORS["light"], fg=COLORS["dark"]).grid(row=3, column=0, sticky="w", pady=10)
    email = tk.Entry(form, font=("Montserrat", 12), width=30)
    email.grid(row=3, column=1, sticky="w", pady=10)
    
    # Address
    tk.Label(form, text="Address", font=("Montserrat", 12),
            bg=COLORS["light"], fg=COLORS["dark"]).grid(row=4, column=0, sticky="w", pady=10)
    address = tk.Text(form, font=("Montserrat", 12), width=30, height=3)
    address.grid(row=4, column=1, sticky="w", pady=10)
    
    # Button frame
    btn_frame = tk.Frame(supplier_popup, bg=COLORS["light"], pady=20)
    btn_frame.pack(fill=tk.X)
    
    # Save button function
    def save_supplier():
        if not supplier_name.get():
            show_notification(supplier_popup, "Please enter supplier name", "warning")
            return
        
        db = connect_db()
        if db:
            cursor = db.cursor()
            try:
                cursor.execute("""
                    INSERT INTO suppliers 
                    (supplier_name, contact_person, phone, email, address) 
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    supplier_name.get(),
                    contact_person.get(),
                    phone.get(),
                    email.get(),
                    address.get("1.0", tk.END)
                ))
                
                # Get the new supplier ID
                supplier_id = cursor.lastrowid
                
                # Log activity
                cursor.execute("INSERT INTO activity_log (user_id, activity) VALUES (%s, %s)",
                              (current_user["id"], f"Added new supplier: {supplier_name.get()}"))
                
                db.commit()
                show_notification(supplier_popup, "Supplier added successfully!", "success")
                
                # Update the supplier dropdown in parent form
                new_supplier_name = supplier_name.get()
                
                # Refresh supplier dropdown
                suppliers = list(supplier_combo['values'])
                suppliers.append(new_supplier_name)
                supplier_combo['values'] = suppliers
                supplier_combo.set(new_supplier_name)
                
                # Add to supplier_ids dictionary in parent scope
                # We need to get the parent's supplier_ids dictionary
                for widget in parent.winfo_children():
                    if isinstance(widget, tk.Frame):
                        for child in widget.winfo_children():
                            if isinstance(child, tk.Frame):
                                if hasattr(child, 'winfo_children'):
                                    for grandchild in child.winfo_children():
                                        if isinstance(grandchild, ttk.Combobox) and grandchild == supplier_combo:
                                            # Found the combo box, now update supplier_ids in this scope
                                            parent.supplier_ids[new_supplier_name] = supplier_id
                
                supplier_popup.after(1500, supplier_popup.destroy)
                
            except Exception as e:
                show_notification(supplier_popup, f"Error: {str(e)}", "danger")
            finally:
                db.close()
    
    # Save button
    save_btn = tk.Button(btn_frame, text="Save Supplier", command=save_supplier,
                        font=("Montserrat", 14, "bold"), 
                        bg=COLORS["primary"], fg="white", padx=30, pady=10)
    save_btn.pack(side=tk.RIGHT, padx=20)
    
    # Cancel button
    cancel_btn = tk.Button(btn_frame, text="Cancel", command=supplier_popup.destroy,
                          font=("Montserrat", 14), 
                          bg=COLORS["light"], fg=COLORS["primary"], padx=20, pady=10)
    cancel_btn.pack(side=tk.RIGHT)

# Main entry point
if __name__ == "__main__":
    create_tables()
    show_login()
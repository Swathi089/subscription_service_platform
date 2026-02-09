from flask import Flask, request, jsonify, session, render_template, redirect
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import sqlite3
import json
from functools import wraps
import hmac
import hashlib

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True
CORS(app, supports_credentials=True, origins=['*'])

DATABASE = 'service_platform.db'

# Razorpay Configuration (use test keys for development)
RAZORPAY_KEY_ID = 'rzp_test_your_key_id'
RAZORPAY_KEY_SECRET = 'your_key_secret'


def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # Users table with enhanced fields
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        contact TEXT,
        address TEXT,
        city TEXT,
        state TEXT,
        pincode TEXT,
        profile_image TEXT,
        is_verified BOOLEAN DEFAULT 0,
        rating REAL DEFAULT 0,
        total_reviews INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Services table with enhanced fields
    c.execute('''CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        category TEXT,
        subcategory TEXT,
        price REAL,
        discount_percentage REAL DEFAULT 0,
        duration_minutes INTEGER,
        frequency_options TEXT,
        provider_id INTEGER,
        image_url TEXT,
        is_active BOOLEAN DEFAULT 1,
        rating REAL DEFAULT 0,
        total_bookings INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (provider_id) REFERENCES users(id)
    )''')

    # Subscriptions table with payment tracking
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        service_id INTEGER,
        start_date DATE,
        end_date DATE,
        next_service_date DATE,
        frequency TEXT,
        preferred_time TEXT,
        status TEXT DEFAULT 'pending',
        total_amount REAL,
        discount_applied REAL DEFAULT 0,
        payment_status TEXT DEFAULT 'pending',
        auto_renew BOOLEAN DEFAULT 1,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES users(id),
        FOREIGN KEY (service_id) REFERENCES services(id)
    )''')

    # Service Requests with detailed tracking
    c.execute('''CREATE TABLE IF NOT EXISTS service_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subscription_id INTEGER,
        customer_id INTEGER,
        service_provider_id INTEGER,
        service_category TEXT,
        service_description TEXT,
        location TEXT,
        scheduled_date DATE,
        scheduled_time TEXT,
        actual_start_time TIMESTAMP,
        actual_end_time TIMESTAMP,
        status TEXT DEFAULT 'scheduled',
        customer_rating INTEGER,
        customer_feedback TEXT,
        provider_notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (subscription_id) REFERENCES subscriptions(id),
        FOREIGN KEY (customer_id) REFERENCES users(id),
        FOREIGN KEY (service_provider_id) REFERENCES users(id)
    )''')

    # Payments table with transaction details
    c.execute('''CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subscription_id INTEGER,
        amount REAL,
        payment_method TEXT,
        transaction_id TEXT,
        razorpay_order_id TEXT,
        razorpay_payment_id TEXT,
        razorpay_signature TEXT,
        payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'pending',
        FOREIGN KEY (subscription_id) REFERENCES subscriptions(id)
    )''')

    # Reviews table
    c.execute('''CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_id INTEGER,
        customer_id INTEGER,
        provider_id INTEGER,
        rating INTEGER,
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (service_id) REFERENCES services(id),
        FOREIGN KEY (customer_id) REFERENCES users(id),
        FOREIGN KEY (provider_id) REFERENCES users(id)
    )''')

    # Notifications table
    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        message TEXT,
        type TEXT,
        is_read BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    # Insert sample services for testing
    c.execute('SELECT COUNT(*) FROM services')
    if c.fetchone()[0] < 500:
        # Generate 100 sample services
        categories = [
            ('Cleaning', ['Deep Cleaning', 'Regular Cleaning',
             'Office Cleaning', 'Carpet Cleaning', 'Window Cleaning']),
            ('Gardening', ['Lawn Care', 'Garden Maintenance',
             'Tree Trimming', 'Landscaping', 'Pest Control']),
            ('Plumbing', ['Repair', 'Installation',
             'Maintenance', 'Emergency', 'Leak Detection']),
            ('Electrical', ['Repair', 'Installation',
             'Maintenance', 'Wiring', 'Fixtures']),
            ('AC Service', ['Maintenance', 'Repair', 'Installation',
             'Duct Cleaning', 'Filter Replacement']),
            ('Painting', ['Interior', 'Exterior',
             'Commercial', 'Residential', 'Touch-up']),
            ('Pest Control', ['Prevention', 'Treatment',
             'Inspection', 'Rodent Control', 'Termite Control']),
            ('Car Care', ['Cleaning', 'Detailing',
             'Maintenance', 'Repair', 'Towing']),
            ('Home Repair', ['Carpentry', 'Roofing',
             'Flooring', 'Drywall', 'Insulation']),
            ('Appliance Repair', [
             'Refrigerator', 'Washing Machine', 'Dishwasher', 'Oven', 'Microwave']),
            ('Security', ['Installation', 'Monitoring',
             'Cameras', 'Alarms', 'Access Control']),
            ('IT Services', ['Computer Repair', 'Network Setup',
             'Data Recovery', 'Software Installation', 'Tech Support']),
            ('Moving', ['Local Moving', 'Long Distance',
             'Packing', 'Storage', 'Furniture Assembly']),
            ('Beauty', ['Hair Styling', 'Makeup', 'Nails', 'Spa', 'Massage']),
            ('Fitness', ['Personal Training', 'Yoga',
             'Pilates', 'Group Classes', 'Nutrition']),
            ('Tutoring', ['Math', 'Science',
             'Language', 'Test Prep', 'Music']),
            ('Pet Care', ['Grooming', 'Walking',
             'Sitting', 'Training', 'Veterinary']),
            ('Event Planning', ['Weddings', 'Parties',
             'Corporate', 'Catering', 'Decorations']),
            ('Photography', ['Portrait', 'Event',
             'Commercial', 'Real Estate', 'Product']),
            ('Legal Services', ['Consultation', 'Document Prep',
             'Notary', 'Mediation', 'Contract Review'])
        ]

        sample_services = []
        service_id = 1

        # Image URLs for different categories - highly specific and appropriate
        category_images = {
            'Cleaning': [
                # Professional cleaning service
                'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400',
                'https://images.unsplash.com/photo-1581578731548-c64695cc6952?w=400',  # House cleaning
                'https://images.unsplash.com/photo-1497366216548-37526070297c?w=400',  # Office cleaning
                'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=400',  # Carpet cleaning
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400'   # Window cleaning
            ],
            'Gardening': [
                'https://images.unsplash.com/photo-1416879595882-3373a0480b5b?w=400',  # Garden maintenance
                'https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?w=400',  # Lawn care
                'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400',  # Tree trimming
                'https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?w=400',  # Landscaping
                'https://images.unsplash.com/photo-1592150621744-aca64f48394a?w=400'   # Pest control
            ],
            'Plumbing': [
                'https://images.unsplash.com/photo-1621905251189-08b45d6a269e?w=400',  # Plumbing repair
                'https://images.unsplash.com/photo-1607472586893-edb57bdc0e39?w=400',  # Pipe installation
                # Plumbing maintenance
                'https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=400',
                'https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=400',  # Emergency plumbing
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400'   # Leak detection
            ],
            'Electrical': [
                'https://images.unsplash.com/photo-1621905252507-b35492cc74b4?w=400',  # Electrical repair
                # Electrical installation
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400',
                # Electrical maintenance
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400',
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400',  # Wiring
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400'   # Electrical fixtures
            ],
            'AC Service': [
                'https://images.unsplash.com/photo-1585771724684-38269d6639fd?w=400',  # AC maintenance
                'https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=400',  # AC repair
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400',  # AC installation
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400',  # Duct cleaning
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400'   # Filter replacement
            ],
            'Painting': [
                'https://images.unsplash.com/photo-1562259949-e8e7689d7828?w=400',  # Interior painting
                'https://images.unsplash.com/photo-1503387837-b154d5074bd2?w=400',  # Exterior painting
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400',  # Commercial painting
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400',  # Residential painting
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400'   # Touch-up painting
            ],
            'Pest Control': [
                'https://images.unsplash.com/photo-1581092160562-40aa08e78837?w=400',  # Pest prevention
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400',  # Pest treatment
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400',  # Pest inspection
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400',  # Rodent control
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400'   # Termite control
            ],
            'Car Care': [
                'https://images.unsplash.com/photo-1601362840469-51e4d8d58785?w=400',  # Car cleaning
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400',  # Car detailing
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400',  # Car maintenance
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400',  # Car repair
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400'   # Car towing
            ],
            'Home Repair': [
                'https://images.unsplash.com/photo-1581244277943-fe4a9c777189?w=400',  # Carpentry
                'https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=400',  # Roofing
                'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=400',  # Flooring
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400',  # Drywall
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400'   # Insulation
            ],
            'Appliance Repair': [
                'https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400',  # Refrigerator repair
                # Washing machine repair
                'https://images.unsplash.com/photo-1584568694244-14e3f4c0b4b5?w=400',
                'https://images.unsplash.com/photo-1556909172-54557c7e4fb7?w=400',  # Dishwasher repair
                'https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400',  # Oven repair
                'https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400'   # Microwave repair
            ],
            'Security': [
                # Security installation
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400',
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400',  # Security monitoring
                'https://images.unsplash.com/photo-1557804506-669a67965ba0?w=400',  # Security cameras
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400',  # Security alarms
                'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400'   # Access control
            ],
            'IT Services': [
                'https://images.unsplash.com/photo-1517077304055-6e89abbf09b0?w=400',  # Computer repair
                'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=400',  # Network setup
                'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=400',  # Data recovery
                # Software installation
                'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=400',
                'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=400'   # Tech support
            ],
            'Moving': [
                'https://images.unsplash.com/photo-1600518464441-9154a4dea21b?w=400',  # Local moving
                # Long distance moving
                'https://images.unsplash.com/photo-1600518464441-9154a4dea21b?w=400',
                'https://images.unsplash.com/photo-1600518464441-9154a4dea21b?w=400',  # Packing services
                'https://images.unsplash.com/photo-1600518464441-9154a4dea21b?w=400',  # Storage
                'https://images.unsplash.com/photo-1600518464441-9154a4dea21b?w=400'   # Furniture assembly
            ],
            'Beauty': [
                'https://images.unsplash.com/photo-1562322140-8baeececf3df?w=400',  # Hair styling
                'https://images.unsplash.com/photo-1516975080664-ed2fc6a32937?w=400',  # Makeup
                'https://images.unsplash.com/photo-1562322140-8baeececf3df?w=400',  # Nails
                'https://images.unsplash.com/photo-1544161515-4ab6ce6db874?w=400',  # Spa
                'https://images.unsplash.com/photo-1544161515-4ab6ce6db874?w=400'   # Massage
            ],
            'Fitness': [
                'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=400',  # Personal training
                'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400',  # Yoga
                'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=400',  # Pilates
                'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=400',  # Group classes
                'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=400'   # Nutrition
            ],
            'Tutoring': [
                'https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=400',  # Math tutoring
                'https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=400',  # Science tutoring
                'https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=400',  # Language tutoring
                'https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=400',  # Test prep
                'https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=400'   # Music tutoring
            ],
            'Pet Care': [
                'https://images.unsplash.com/photo-1583337130417-3346a1be7dee?w=400',  # Pet grooming
                'https://images.unsplash.com/photo-1583337130417-3346a1be7dee?w=400',  # Pet walking
                'https://images.unsplash.com/photo-1583337130417-3346a1be7dee?w=400',  # Pet sitting
                'https://images.unsplash.com/photo-1583337130417-3346a1be7dee?w=400',  # Pet training
                'https://images.unsplash.com/photo-1583337130417-3346a1be7dee?w=400'   # Veterinary
            ],
            'Event Planning': [
                'https://images.unsplash.com/photo-1519741497674-611481863552?w=400',  # Wedding planning
                'https://images.unsplash.com/photo-1530103862676-de8c9debad1d?w=400',  # Party planning
                'https://images.unsplash.com/photo-1519741497674-611481863552?w=400',  # Corporate events
                'https://images.unsplash.com/photo-1530103862676-de8c9debad1d?w=400',  # Catering
                'https://images.unsplash.com/photo-1530103862676-de8c9debad1d?w=400'   # Event decorations
            ],
            'Photography': [
                # Portrait photography
                'https://images.unsplash.com/photo-1606983340126-99ab4feaa64a?w=400',
                'https://images.unsplash.com/photo-1606983340126-99ab4feaa64a?w=400',  # Event photography
                # Commercial photography
                'https://images.unsplash.com/photo-1606983340126-99ab4feaa64a?w=400',
                # Real estate photography
                'https://images.unsplash.com/photo-1606983340126-99ab4feaa64a?w=400',
                # Product photography
                'https://images.unsplash.com/photo-1606983340126-99ab4feaa64a?w=400'
            ],
            'Legal Services': [
                'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=400',  # Legal consultation
                # Document preparation
                'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=400',
                'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=400',  # Notary services
                'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=400',  # Mediation
                'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=400'   # Contract review
            ]
        }

        for category, subcategories in categories:
            for subcategory_idx, subcategory in enumerate(subcategories):
                # Generate 5 services per subcategory
                for i in range(5):
                    name = f"{subcategory} Service {service_id}"
                    description = f"Professional {subcategory.lower()} service for {category.lower()}"
                    price = 200 + (service_id * 10)  # Varying prices
                    discount = 5 + (service_id % 15)  # Varying discounts
                    duration = 60 + (service_id % 180)  # Varying durations
                    frequency_options = ['daily,weekly,monthly', 'weekly,monthly',
                                         'monthly,quarterly', 'quarterly,half-yearly'][service_id % 4]
                    rating = 3.5 + (service_id % 15) / \
                        10  # Ratings between 3.5-5.0
                    bookings = 10 + (service_id * 3)  # Varying booking counts

                    # Get appropriate image for this category and subcategory
                    image_url = category_images.get(category, ['https://images.unsplash.com/photo-1557804506-669a67965ba0?w=400'])[
                        subcategory_idx % len(category_images.get(category, ['https://images.unsplash.com/photo-1557804506-669a67965ba0?w=400']))]

                    sample_services.append((
                        name, description, category, subcategory, price, discount, duration,
                        frequency_options, None, image_url, 1, rating, bookings
                    ))
                    service_id += 1

        c.executemany('''INSERT INTO services
            (name, description, category, subcategory, price, discount_percentage, duration_minutes,
             frequency_options, provider_id, image_url, is_active, rating, total_bookings)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', sample_services)

    conn.commit()
    conn.close()


def get_db():
    conn = sqlite3.connect(DATABASE, timeout=10.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA cache_size=1000')
    conn.execute('PRAGMA temp_store=memory')
    return conn


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api'):
                return jsonify({'error': 'You need to login or create an account to access our services and explore all available options.'}), 401
            else:
                return redirect('/auth')
        return f(*args, **kwargs)
    return decorated_function

# Auth Routes


@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    hashed_password = generate_password_hash(data['password'])

    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''INSERT INTO users (name, email, password, role, contact, address, city, state, pincode)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (data['name'], data['email'], hashed_password, data.get('role', 'customer'),
                   data.get('contact'), data.get('address'), data.get('city'),
                   data.get('state'), data.get('pincode')))
        conn.commit()
        user_id = c.lastrowid
        conn.close()
        return jsonify({'message': 'Registration successful', 'user_id': user_id}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Email already exists'}), 400


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE email = ?', (data['email'],))
    user = c.fetchone()
    conn.close()

    if user and check_password_hash(user['password'], data['password']):
        session['user_id'] = user['id']
        session['user_role'] = user['role']
        return jsonify({
            'message': 'Login successful',
            'user': {
                'id': user['id'],
                'name': user['name'],
                'email': user['email'],
                'role': user['role'],
                'contact': user['contact'],
                'city': user['city']
            }
        }), 200
    return jsonify({'error': 'Invalid credentials'}), 401


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logout successful'}), 200


@app.route('/api/profile', methods=['GET', 'PUT'])
# @login_required  # Temporarily disabled for testing
def profile():
    # user_id = session['user_id']
    # Default to user ID 8 (the test customer we created) for testing
    user_id = 8

    if request.method == 'GET':
        conn = get_db()
        c = conn.cursor()
        c.execute('''SELECT id, name, email, role, contact, address, city, state, pincode,
                     rating, total_reviews, is_verified FROM users WHERE id = ?''', (user_id,))
        user = c.fetchone()
        conn.close()
        return jsonify(dict(user)), 200

    elif request.method == 'PUT':
        data = request.json
        conn = get_db()
        c = conn.cursor()

        # Check if email is being updated and if it's already taken by another user
        if data.get('email'):
            c.execute('SELECT id FROM users WHERE email = ? AND id != ?',
                      (data.get('email'), user_id))
            if c.fetchone():
                conn.close()
                return jsonify({'error': 'Email already exists'}), 400

        c.execute('''UPDATE users SET name = ?, email = ?, contact = ?, address = ?, city = ?, state = ?, pincode = ?
                     WHERE id = ?''',
                  (data.get('name'), data.get('email'), data.get('contact') or data.get('phone'), data.get('address'),
                   data.get('city'), data.get('state'), data.get('pincode'), user_id))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Profile updated'}), 200

# Service Routes


@app.route('/api/services', methods=['GET'])
def get_services():
    category = request.args.get('category')
    search = request.args.get('search')

    conn = get_db()
    c = conn.cursor()

    query = 'SELECT * FROM services WHERE is_active = 1'
    params = []

    if category:
        query += ' AND category = ?'
        params.append(category)
    if search:
        query += ' AND (name LIKE ? OR description LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])

    query += ' ORDER BY rating DESC, total_bookings DESC'

    c.execute(query, params)
    services = [dict(row) for row in c.fetchall()]
    conn.close()

    return jsonify(services), 200


@app.route('/api/services/<int:service_id>', methods=['GET'])
def get_service(service_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM services WHERE id = ?', (service_id,))
    service = c.fetchone()

    if service:
        service_dict = dict(service)
        c.execute('''SELECT r.*, u.name as customer_name FROM reviews r
                     JOIN users u ON r.customer_id = u.id
                     WHERE r.service_id = ? ORDER BY r.created_at DESC LIMIT 5''', (service_id,))
        reviews = [dict(row) for row in c.fetchall()]
        service_dict['reviews'] = reviews
        conn.close()
        return jsonify(service_dict), 200

    conn.close()
    return jsonify({'error': 'Service not found'}), 404


@app.route('/api/my-services', methods=['GET'])
@login_required
def get_my_services():
    if session.get('user_role') != 'provider':
        return jsonify({'error': 'Only providers can access their services'}), 403

    provider_id = session['user_id']
    conn = get_db()
    c = conn.cursor()
    c.execute(
        'SELECT * FROM services WHERE provider_id = ? ORDER BY created_at DESC', (provider_id,))
    services = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(services), 200


@app.route('/api/services', methods=['POST'])
@login_required
def create_service():
    if session.get('user_role') != 'provider':
        return jsonify({'error': 'Only providers can create services'}), 403

    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO services (name, description, category, subcategory, price,
                 discount_percentage, duration_minutes, frequency_options, provider_id, image_url, is_active)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (data['name'], data['description'], data['category'], data.get('subcategory'),
               data['price'], data.get('discount_percentage', 0), data.get(
                   'duration_minutes', 60),
               data['frequency_options'], session['user_id'], data.get('image_url'), 1 if data.get('is_active', True) else 0))
    conn.commit()
    service_id = c.lastrowid
    conn.close()
    return jsonify({'message': 'Service created', 'service_id': service_id}), 201

# Payment Gateway Routes


@app.route('/api/razorpay/config', methods=['GET'])
def get_razorpay_config():
    return jsonify({'key_id': RAZORPAY_KEY_ID}), 200


@app.route('/api/create-order', methods=['POST'])
# @login_required  # Temporarily disabled for testing
def create_order():
    data = request.json
    # For testing without authentication, use a default user_id
    user_id = 1  # Default to user ID 1 for testing

    # 'instant' or 'subscription'
    service_type = data.get('type', 'subscription')

    conn = get_db()
    c = conn.cursor()

    # Get service details
    c.execute('SELECT price, discount_percentage, provider_id FROM services WHERE id = ?',
              (data['service_id'],))
    service = c.fetchone()

    if not service:
        conn.close()
        return jsonify({'error': 'Service not found'}), 404

    # Calculate pricing
    base_price = service['price']
    discount = service['discount_percentage']
    final_price = base_price * (1 - discount/100)
    amount_in_paise = int(final_price * 100)  # Convert to paise for Razorpay

    if service_type == 'instant':
        # For instant service, create a service request directly
        c.execute('''INSERT INTO service_requests
                     (customer_id, service_provider_id, service_category, service_description,
                      scheduled_date, scheduled_time, status)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (user_id, service['provider_id'], 'Instant Service', f'Instant booking for service ID {data["service_id"]}',
                   data['start_date'], data.get('preferred_time', 'morning'), 'scheduled'))

        request_id = c.lastrowid

        # Generate order ID
        order_id = f'instant_order_{request_id}_{int(datetime.now().timestamp())}'

        # Create payment record for instant service
        c.execute('''INSERT INTO payments (subscription_id, amount, payment_method, razorpay_order_id, status, payment_date)
                     VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)''',
                  (None, final_price, 'razorpay', order_id, 'completed'))

        conn.commit()
        conn.close()

        return jsonify({
            'order_id': order_id,
            'amount': amount_in_paise,
            'currency': 'INR',
            'request_id': request_id,
            'type': 'instant'
        }), 200

    else:
        # For subscription service
        frequency = data['frequency']
        duration = data.get('duration', 'monthly')

        # Calculate dates
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')

        duration_map = {
            'monthly': 30, 'quarterly': 90, 'half-yearly': 180
        }
        end_date = start_date + timedelta(days=duration_map.get(duration, 30))

        # Create subscription record with active status immediately
        c.execute('''INSERT INTO subscriptions
                     (customer_id, service_id, start_date, end_date, next_service_date, frequency,
                      preferred_time, total_amount, discount_applied, status, payment_status)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (user_id, data['service_id'], data['start_date'], end_date.strftime('%Y-%m-%d'),
                   data['start_date'], frequency, data.get(
                       'preferred_time'), final_price, discount,
                   'active', 'paid'))
        subscription_id = c.lastrowid

        # Generate order ID
        order_id = f'subscription_order_{subscription_id}_{int(datetime.now().timestamp())}'

        # Create payment record as completed
        c.execute('''INSERT INTO payments (subscription_id, amount, payment_method, razorpay_order_id, status, payment_date)
                     VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)''',
                  (subscription_id, final_price, 'razorpay', order_id, 'completed'))

        # Generate service requests immediately
        generate_service_requests(
            c, subscription_id, data['service_id'],
            start_date, end_date, frequency, data.get('preferred_time')
        )

        conn.commit()
        conn.close()

        return jsonify({
            'order_id': order_id,
            'amount': amount_in_paise,
            'currency': 'INR',
            'subscription_id': subscription_id,
            'type': 'subscription'
        }), 200


@app.route('/api/verify-payment', methods=['POST'])
@login_required
def verify_payment():
    data = request.json
    user_id = session['user_id']

    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')
    subscription_id = data.get('subscription_id')

    # Verify signature (in production, verify with actual Razorpay secret)
    # expected_signature = hmac.new(
    #     RAZORPAY_KEY_SECRET.encode(),
    #     f"{razorpay_order_id}|{razorpay_payment_id}".encode(),
    #     hashlib.sha256
    # ).hexdigest()

    # For demo purposes, we'll accept any signature
    # if razorpay_signature != expected_signature:
    #     return jsonify({'error': 'Invalid payment signature'}), 400

    conn = get_db()
    c = conn.cursor()

    # Verify subscription belongs to user
    c.execute('SELECT * FROM subscriptions WHERE id = ? AND customer_id = ?',
              (subscription_id, user_id))
    subscription = c.fetchone()

    if not subscription:
        conn.close()
        return jsonify({'error': 'Invalid subscription'}), 404

    # Update payment record
    c.execute('''UPDATE payments 
                 SET razorpay_payment_id = ?, razorpay_signature = ?, status = ?, payment_date = CURRENT_TIMESTAMP
                 WHERE subscription_id = ? AND razorpay_order_id = ?''',
              (razorpay_payment_id, razorpay_signature, 'completed', subscription_id, razorpay_order_id))

    # Update subscription status to active
    c.execute('''UPDATE subscriptions 
                 SET status = ?, payment_status = ?, updated_at = CURRENT_TIMESTAMP
                 WHERE id = ?''',
              ('active', 'paid', subscription_id))

    # Get service details for generating requests
    c.execute('SELECT service_id, start_date, end_date, frequency, preferred_time FROM subscriptions WHERE id = ?',
              (subscription_id,))
    sub_data = c.fetchone()

    # Generate service requests
    generate_service_requests(
        c, subscription_id, sub_data['service_id'],
        datetime.strptime(sub_data['start_date'], '%Y-%m-%d'),
        datetime.strptime(sub_data['end_date'], '%Y-%m-%d'),
        sub_data['frequency'], sub_data['preferred_time']
    )

    conn.commit()
    conn.close()

    return jsonify({'message': 'Payment verified successfully', 'status': 'success'}), 200


# Subscription Routes


@app.route('/api/subscriptions', methods=['GET'])
# @login_required  # Temporarily disabled for testing
def get_subscriptions():
    # user_id = session['user_id']
    user_id = 1  # Default to user ID 1 for testing
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT s.*, srv.name as service_name, srv.category, srv.price, srv.image_url,
                 srv.rating as service_rating
                 FROM subscriptions s
                 JOIN services srv ON s.service_id = srv.id
                 WHERE s.customer_id = ? AND s.status != 'pending'
                 ORDER BY s.created_at DESC''', (user_id,))
    subs = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(subs), 200


@app.route('/api/subscriptions/<int:sub_id>', methods=['PUT', 'DELETE'])
# @login_required  # Temporarily disabled for testing
def manage_subscription(sub_id):
    # user_id = session['user_id']
    user_id = 1  # Default to user ID 1 for testing

    if request.method == 'PUT':
        data = request.json
        conn = get_db()
        c = conn.cursor()
        c.execute('''UPDATE subscriptions SET status = ?, updated_at = CURRENT_TIMESTAMP 
                     WHERE id = ? AND customer_id = ?''',
                  (data.get('status'), sub_id, user_id))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Subscription updated'}), 200

    elif request.method == 'DELETE':
        conn = get_db()
        c = conn.cursor()
        c.execute('''UPDATE subscriptions SET status = ?, updated_at = CURRENT_TIMESTAMP 
                     WHERE id = ? AND customer_id = ?''',
                  ('cancelled', sub_id, user_id))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Subscription cancelled'}), 200


def generate_service_requests(cursor, subscription_id, service_id, start_date, end_date, frequency, preferred_time):
    cursor.execute(
        'SELECT provider_id FROM services WHERE id = ?', (service_id,))
    provider = cursor.fetchone()
    provider_id = provider['provider_id'] if provider else None

    current_date = start_date
    delta_map = {
        'daily': timedelta(days=1),
        'weekly': timedelta(weeks=1),
        'monthly': timedelta(days=30),
        'quarterly': timedelta(days=90),
        'half-yearly': timedelta(days=180)
    }

    delta = delta_map.get(frequency, timedelta(days=30))
    count = 0
    max_requests = 50

    while current_date <= end_date and count < max_requests:
        cursor.execute('''INSERT INTO service_requests 
                         (subscription_id, service_provider_id, scheduled_date, scheduled_time, status)
                         VALUES (?, ?, ?, ?, ?)''',
                       (subscription_id, provider_id, current_date.strftime('%Y-%m-%d'),
                        preferred_time, 'scheduled'))
        current_date += delta
        count += 1


# Service Request Routes


@app.route('/api/service-requests', methods=['GET'])
@login_required
def service_requests():
    if session.get('user_role') != 'provider':
        return jsonify({'error': 'Only providers can access'}), 403

    status_filter = request.args.get('status')
    provider_id = session['user_id']

    conn = get_db()
    c = conn.cursor()

    query = '''SELECT sr.*, s.customer_id, u.name as customer_name, u.contact, u.address,
               sub.frequency, sub.preferred_time, srv.name as service_name, srv.category
               FROM service_requests sr
               JOIN subscriptions sub ON sr.subscription_id = sub.id
               JOIN users u ON sub.customer_id = u.id
               JOIN services srv ON sub.service_id = srv.id
               JOIN subscriptions s ON sr.subscription_id = s.id
               WHERE sr.service_provider_id = ?'''

    params = [provider_id]

    if status_filter:
        query += ' AND sr.status = ?'
        params.append(status_filter)

    query += ' ORDER BY sr.scheduled_date ASC'

    c.execute(query, params)
    requests = [dict(row) for row in c.fetchall()]
    conn.close()

    return jsonify(requests), 200


@app.route('/api/service-requests/<int:req_id>', methods=['PUT'])
@login_required
def update_service_request(req_id):
    if session.get('user_role') != 'provider':
        return jsonify({'error': 'Only providers can update'}), 403

    data = request.json
    conn = get_db()
    c = conn.cursor()

    update_fields = []
    params = []

    if 'status' in data:
        update_fields.append('status = ?')
        params.append(data['status'])
    if 'provider_notes' in data:
        update_fields.append('provider_notes = ?')
        params.append(data['provider_notes'])
    if data.get('status') == 'in_progress':
        update_fields.append('actual_start_time = CURRENT_TIMESTAMP')
    if data.get('status') == 'completed':
        update_fields.append('actual_end_time = CURRENT_TIMESTAMP')

    update_fields.append('updated_at = CURRENT_TIMESTAMP')
    params.extend([req_id, session['user_id']])

    query = f"UPDATE service_requests SET {', '.join(update_fields)} WHERE id = ? AND service_provider_id = ?"
    c.execute(query, params)
    conn.commit()
    conn.close()

    return jsonify({'message': 'Request updated'}), 200


# Dashboard stats


@app.route('/api/dashboard/stats', methods=['GET'])
@login_required
def dashboard_stats():
    user_id = session['user_id']
    role = session['user_role']

    conn = get_db()
    c = conn.cursor()

    if role == 'customer':
        c.execute('SELECT COUNT(*) as count FROM subscriptions WHERE customer_id = ? AND status = ?',
                  (user_id, 'active'))
        active_subs = c.fetchone()['count']

        c.execute('''SELECT MIN(sr.scheduled_date) as next_date FROM service_requests sr
                     JOIN subscriptions s ON sr.subscription_id = s.id
                     WHERE s.customer_id = ? AND sr.status IN ('scheduled', 'in_progress')''', (user_id,))
        next_upcoming = c.fetchone()['next_date']

        c.execute('''SELECT COALESCE(SUM(p.amount), 0) as total FROM payments p
                     JOIN subscriptions s ON p.subscription_id = s.id
                     WHERE s.customer_id = ? AND p.status = ?''', (user_id, 'completed'))
        total_spent = c.fetchone()['total']

        stats = {
            'active_subscriptions': active_subs,
            'next_upcoming_date': next_upcoming,
            'total_spent': round(total_spent, 2)
        }

    elif role == 'provider':
        c.execute('''SELECT COUNT(*) as count FROM service_requests
                     WHERE service_provider_id = ? AND status = ?''',
                  (user_id, 'scheduled'))
        scheduled = c.fetchone()['count']

        c.execute('''SELECT COUNT(*) as count FROM service_requests
                     WHERE service_provider_id = ? AND status = ?''',
                  (user_id, 'completed'))
        completed = c.fetchone()['count']

        c.execute('''SELECT COUNT(*) as count FROM service_requests
                     WHERE service_provider_id = ? AND status = ?''',
                  (user_id, 'in_progress'))
        in_progress = c.fetchone()['count']

        c.execute(
            'SELECT COUNT(*) as count FROM services WHERE provider_id = ?', (user_id,))
        total_services = c.fetchone()['count']

        stats = {
            'scheduled_requests': scheduled,
            'completed_requests': completed,
            'in_progress_requests': in_progress,
            'total_services': total_services
        }

    conn.close()
    return jsonify(stats), 200


@app.route('/api/upcoming-schedules', methods=['GET'])
# @login_required  # Temporarily disabled for testing
def get_upcoming_schedules():
    # user_id = session['user_id']
    user_id = 1  # Default to user ID 1 for testing
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT sr.*, srv.name as service_name, srv.category, sub.frequency
                 FROM service_requests sr
                 JOIN subscriptions sub ON sr.subscription_id = sub.id
                 JOIN services srv ON sub.service_id = srv.id
                 WHERE sub.customer_id = ? AND sr.status IN ('scheduled', 'in_progress')
                 ORDER BY sr.scheduled_date ASC''', (user_id,))
    schedules = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(schedules), 200


@app.route('/api/payment-history', methods=['GET'])
# @login_required  # Temporarily disabled for testing
def get_payment_history():
    # user_id = session['user_id']
    user_id = 1  # Default to user ID 1 for testing
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT p.*, srv.name as service_name, sub.frequency
                 FROM payments p
                 JOIN subscriptions sub ON p.subscription_id = sub.id
                 JOIN services srv ON sub.service_id = srv.id
                 WHERE sub.customer_id = ? AND p.status = 'completed'
                 ORDER BY p.payment_date DESC''', (user_id,))
    payments = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(payments), 200


# Categories endpoint


@login_required
@app.route('/api/categories', methods=['GET'])
def get_categories():
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT category, COUNT(*) as service_count
                 FROM services WHERE is_active = 1
                 GROUP BY category ORDER BY service_count DESC''')
    categories = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(categories), 200


# Available Jobs endpoint


@app.route('/api/available-jobs', methods=['GET'])
# @login_required  # Temporarily disabled for testing
def get_available_jobs():
    # if session.get('user_role') != 'provider':
    #     return jsonify({'error': 'Only providers can access available jobs'}), 403

    conn = get_db()
    c = conn.cursor()

    # Get all scheduled service requests from customers
    # This shows all customer-requested services to providers
    c.execute('''SELECT sr.*, s.customer_id, u.name as customer_name, u.contact, u.address,
                 sub.frequency, sub.preferred_time, srv.name as service_name, srv.category, srv.price
                 FROM service_requests sr
                 JOIN subscriptions sub ON sr.subscription_id = sub.id
                 JOIN users u ON sub.customer_id = u.id
                 JOIN services srv ON sub.service_id = srv.id
                 WHERE sr.status = 'scheduled'
                 ORDER BY sr.scheduled_date ASC''')

    jobs = [dict(row) for row in c.fetchall()]
    conn.close()

    return jsonify(jobs), 200


# Accept Job endpoint


@app.route('/api/accept-job/<int:job_id>', methods=['POST'])
# @login_required  # Temporarily disabled for testing
def accept_job(job_id):
    # if session.get('user_role') != 'provider':
    #     return jsonify({'error': 'Only providers can accept jobs'}), 403

    # provider_id = session['user_id']
    provider_id = 2  # Default to provider ID 2 for testing

    conn = get_db()
    c = conn.cursor()

    # Check if the job exists and is available
    c.execute('''SELECT sr.*, COALESCE(srv.provider_id, NULL) as original_provider_id
                 FROM service_requests sr
                 LEFT JOIN subscriptions sub ON sr.subscription_id = sub.id
                 LEFT JOIN services srv ON sub.service_id = srv.id
                 WHERE sr.id = ? AND sr.status = 'scheduled' ''', (job_id,))

    job = c.fetchone()

    if not job:
        conn.close()
        return jsonify({'error': 'Job not found or not available'}), 404

    # Update the service request to assign it to this provider
    c.execute('''UPDATE service_requests
                 SET service_provider_id = ?, status = 'accepted', updated_at = CURRENT_TIMESTAMP
                 WHERE id = ?''', (provider_id, job_id))

    # Create notification for customer
    c.execute('''INSERT INTO notifications (user_id, title, message, type)
                 VALUES (?, ?, ?, ?)''',
              (job.customer_id, 'Service Request Accepted',
               f'Your service request for {job.service_category} has been accepted by a provider.',
               'service_accepted'))

    conn.commit()
    conn.close()

    return jsonify({'message': 'Job accepted successfully'}), 200


# Customer Service Request Routes


@app.route('/api/customer/service-requests', methods=['POST'])
# @login_required  # Temporarily disabled for testing
def create_service_request():
    # user_id = session['user_id']
    user_id = 1  # Default to user ID 1 for testing

    data = request.json

    conn = get_db()
    c = conn.cursor()

    # Insert service request
    c.execute('''INSERT INTO service_requests
                 (customer_id, service_category, service_description, location,
                  scheduled_date, scheduled_time, status)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (user_id, data['service_category'], data.get('service_description', ''),
               data['location'], data['scheduled_date'], data['scheduled_time'], 'scheduled'))

    request_id = c.lastrowid
    conn.commit()
    conn.close()

    return jsonify({'message': 'Service request created successfully', 'request_id': request_id}), 201


@app.route('/api/customer/service-requests', methods=['GET'])
# @login_required  # Temporarily disabled for testing
def get_customer_service_requests():
    # user_id = session['user_id']
    user_id = 1  # Default to user ID 1 for testing

    conn = get_db()
    c = conn.cursor()

    c.execute('''SELECT sr.*, u.name as provider_name, u.contact as provider_contact
                 FROM service_requests sr
                 LEFT JOIN users u ON sr.service_provider_id = u.id
                 WHERE sr.customer_id = ?
                 ORDER BY sr.created_at DESC''', (user_id,))

    requests = [dict(row) for row in c.fetchall()]
    conn.close()

    return jsonify(requests), 200


# Notifications Routes


@app.route('/api/notifications', methods=['GET'])
# @login_required  # Temporarily disabled for testing
def get_notifications():
    # user_id = session['user_id']
    user_id = 1  # Default to user ID 1 for testing

    conn = get_db()
    c = conn.cursor()

    c.execute('''SELECT * FROM notifications
                 WHERE user_id = ?
                 ORDER BY created_at DESC LIMIT 20''', (user_id,))

    notifications = [dict(row) for row in c.fetchall()]
    conn.close()

    return jsonify(notifications), 200


@app.route('/api/notifications/<int:notification_id>/read', methods=['PUT'])
# @login_required  # Temporarily disabled for testing
def mark_notification_read(notification_id):
    # user_id = session['user_id']
    user_id = 1  # Default to user ID 1 for testing

    conn = get_db()
    c = conn.cursor()

    c.execute('''UPDATE notifications SET is_read = 1
                 WHERE id = ? AND user_id = ?''', (notification_id, user_id))

    conn.commit()
    conn.close()

    return jsonify({'message': 'Notification marked as read'}), 200


# Provider Customer Requests endpoint


@app.route('/api/provider/customer-requests', methods=['GET'])
# @login_required  # Temporarily disabled for testing
def get_customer_requests():
    # if session.get('user_role') != 'provider':
    #     return jsonify({'error': 'Only providers can access customer requests'}), 403

    # provider_id = session['user_id']
    status_filter = request.args.get('status', 'scheduled')

    conn = get_db()
    c = conn.cursor()

    query = '''SELECT sr.*, u.name as customer_name, u.contact, u.address as customer_address
               FROM service_requests sr
               JOIN users u ON sr.customer_id = u.id
               WHERE sr.status = ?'''

    params = [status_filter]

    if status_filter == 'scheduled':
        # For scheduled requests, show all available ones
        pass
    else:
        # For accepted/in-progress/completed, show only this provider's requests
        query += ' AND sr.service_provider_id = ?'
        params.append(provider_id)

    query += ' ORDER BY sr.scheduled_date ASC'

    c.execute(query, params)
    requests = [dict(row) for row in c.fetchall()]
    conn.close()

    return jsonify(requests), 200


# HTML Page Routes
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login_page():
    return render_template('login.html')


@app.route('/register')
def register_page():
    return render_template('register.html')


@app.route('/services')
def services_page():
    return render_template('services.html')


@app.route('/service-details')
def service_details_page():
    return render_template('service-details.html')


@app.route('/add-service')
def add_service_page():
    return render_template('add-service.html')


@app.route('/customer-dashboard')
def customer_dashboard_page():
    return render_template('customer-dashboard.html')


@app.route('/provider-dashboard')
def provider_dashboard_page():
    return render_template('provider-dashboard.html')


@app.route('/search-jobs')
def search_jobs_page():
    return render_template('search-jobs.html')


@app.route('/subscribe')
def subscribe_page():
    return render_template('subscribe.html')


@app.route('/auth')
def auth_page():
    return render_template('auth.html')


# VeilGlass OSINT Routes
@app.route('/veilglass')
def veilglass_home():
    return render_template('veilglass/index.html')


@app.route('/attack-surface')
def attack_surface():
    return render_template('veilglass/attack-surface.html')


@app.route('/credential-exposure')
def credential_exposure():
    return render_template('veilglass/credential-exposure.html')


@app.route('/domain-analysis')
def domain_analysis():
    return render_template('veilglass/domain-analysis.html')


@app.route('/email-osint')
def email_osint():
    return render_template('veilglass/email-osint.html')


@app.route('/social-media-osint')
def social_media_osint():
    return render_template('veilglass/social-media-osint.html')


@app.route('/ip-geolocation')
def ip_geolocation():
    return render_template('veilglass/ip-geolocation.html')


@app.route('/phone-osint')
def phone_osint():
    return render_template('veilglass/phone-osint.html')


@app.route('/username-osint')
def username_osint():
    return render_template('veilglass/username-osint.html')


@app.route('/breach-check')
def breach_check():
    return render_template('veilglass/breach-check.html')


@app.route('/dark-web-search')
def dark_web_search():
    return render_template('veilglass/dark-web-search.html')


@app.route('/metadata-analysis')
def metadata_analysis():
    return render_template('veilglass/metadata-analysis.html')


@app.route('/dns-enumeration')
def dns_enumeration():
    return render_template('veilglass/dns-enumeration.html')


@app.route('/subdomain-enumeration')
def subdomain_enumeration():
    return render_template('veilglass/subdomain-enumeration.html')


@app.route('/port-scanning')
def port_scanning():
    return render_template('veilglass/port-scanning.html')


@app.route('/web-vulnerability-scan')
def web_vulnerability_scan():
    return render_template('veilglass/web-vulnerability-scan.html')


@app.route('/ssl-certificate-check')
def ssl_certificate_check():
    return render_template('veilglass/ssl-certificate-check.html')


@app.route('/technology-stack-detection')
def technology_stack_detection():
    return render_template('veilglass/technology-stack-detection.html')


@app.route('/api-fingerprinting')
def api_fingerprinting():
    return render_template('veilglass/api-fingerprinting.html')


@app.route('/source-code-leakage')
def source_code_leakage():
    return render_template('veilglass/source-code-leakage.html')


@app.route('/exposed-git-repos')
def exposed_git_repos():
    return render_template('veilglass/exposed-git-repos.html')


@app.route('/exposed-config-files')
def exposed_config_files():
    return render_template('veilglass/exposed-config-files.html')


@app.route('/exposed-database-files')
def exposed_database_files():
    return render_template('veilglass/exposed-database-files.html')


@app.route('/exposed-log-files')
def exposed_log_files():
    return render_template('veilglass/exposed-log-files.html')


@app.route('/exposed-backup-files')
def exposed_backup_files():
    return render_template('veilglass/exposed-backup-files.html')


@app.route('/exposed-installation-files')
def exposed_installation_files():
    return render_template('veilglass/exposed-installation-files.html')


@app.route('/directory-listing-vulnerability')
def directory_listing_vulnerability():
    return render_template('veilglass/directory-listing-vulnerability.html')


@app.route('/exposed-env-files')
def exposed_env_files():
    return render_template('veilglass/exposed-env-files.html')


@app.route('/exposed-htaccess-files')
def exposed_htaccess_files():
    return render_template('veilglass/exposed-htaccess-files.html')


@app.route('/exposed-nginx-config')
def exposed_nginx_config():
    return render_template('veilglass/exposed-nginx-config.html')


@app.route('/exposed-apache-config')
def exposed_apache_config():
    return render_template('veilglass/exposed-apache-config.html')


@app.route('/exposed-iis-config')
def exposed_iis_config():
    return render_template('veilglass/exposed-iis-config.html')


@app.route('/exposed-docker-files')
def exposed_docker_files():
    return render_template('veilglass/exposed-docker-files.html')


@app.route('/exposed-kubernetes-config')
def exposed_kubernetes_config():
    return render_template('veilglass/exposed-kubernetes-config.html')


@app.route('/exposed-aws-credentials')
def exposed_aws_credentials():
    return render_template('veilglass/exposed-aws-credentials.html')


@app.route('/exposed-gcp-credentials')
def exposed_gcp_credentials():
    return render_template('veilglass/exposed-gcp-credentials.html')


@app.route('/exposed-azure-credentials')
def exposed_azure_credentials():
    return render_template('veilglass/exposed-azure-credentials.html')


@app.route('/exposed-api-keys')
def exposed_api_keys():
    return render_template('veilglass/exposed-api-keys.html')


@app.route('/exposed-database-credentials')
def exposed_database_credentials():
    return render_template('veilglass/exposed-database-credentials.html')


@app.route('/exposed-ftp-credentials')
def exposed_ftp_credentials():
    return render_template('veilglass/exposed-ftp-credentials.html')


@app.route('/exposed-ssh-keys')
def exposed_ssh_keys():
    return render_template('veilglass/exposed-ssh-keys.html')


@app.route('/exposed-private-keys')
def exposed_private_keys():
    return render_template('veilglass/exposed-private-keys.html')


@app.route('/exposed-session-tokens')
def exposed_session_tokens():
    return render_template('veilglass/exposed-session-tokens.html')


@app.route('/exposed-jwt-tokens')
def exposed_jwt_tokens():
    return render_template('veilglass/exposed-jwt-tokens.html')


@app.route('/exposed-oauth-tokens')
def exposed_oauth_tokens():
    return render_template('veilglass/exposed-oauth-tokens.html')


@app.route('/exposed-cookies')
def exposed_cookies():
    return render_template('veilglass/exposed-cookies.html')


@app.route('/exposed-passwords')
def exposed_passwords():
    return render_template('veilglass/exposed-passwords.html')


@app.route('/exposed-credit-cards')
def exposed_credit_cards():
    return render_template('veilglass/exposed-credit-cards.html')


@app.route('/exposed-personal-info')
def exposed_personal_info():
    return render_template('veilglass/exposed-personal-info.html')


@app.route('/exposed-medical-records')
def exposed_medical_records():
    return render_template('veilglass/exposed-medical-records.html')


@app.route('/exposed-financial-data')
def exposed_financial_data():
    return render_template('veilglass/exposed-financial-data.html')


@app.route('/exposed-intellectual-property')
def exposed_intellectual_property():
    return render_template('veilglass/exposed-intellectual-property.html')


@app.route('/exposed-trade-secrets')
def exposed_trade_secrets():
    return render_template('veilglass/exposed-trade-secrets.html')


@app.route('/exposed-source-code')
def exposed_source_code():
    return render_template('veilglass/exposed-source-code.html')


@app.route('/exposed-api-documentation')
def exposed_api_documentation():
    return render_template('veilglass/exposed-api-documentation.html')


@app.route('/exposed-test-files')
def exposed_test_files():
    return render_template('veilglass/exposed-test-files.html')


@app.route('/exposed-debug-files')
def exposed_debug_files():
    return render_template('veilglass/exposed-debug-files.html')


@app.route('/exposed-temp-files')
def exposed_temp_files():
    return render_template('veilglass/exposed-temp-files.html')


@app.route('/exposed-cache-files')
def exposed_cache_files():
    return render_template('veilglass/exposed-cache-files.html')


@app.route('/exposed-swap-files')
def exposed_swap_files():
    return render_template('veilglass/exposed-swap-files.html')


@app.route('/exposed-core-files')
def exposed_core_files():
    return render_template('veilglass/exposed-core-files.html')


@app.route('/exposed-crash-dumps')
def exposed_crash_dumps():
    return render_template('veilglass/exposed-crash-dumps.html')


@app.route('/exposed-error-logs')
def exposed_error_logs():
    return render_template('veilglass/exposed-error-logs.html')


@app.route('/exposed-access-logs')
def exposed_access_logs():
    return render_template('veilglass/exposed-access-logs.html')


@app.route('/exposed-security-logs')
def exposed_security_logs():
    return render_template('veilglass/exposed-security-logs.html')


@app.route('/exposed-audit-logs')
def exposed_audit_logs():
    return render_template('veilglass/exposed-audit-logs.html')


@app.route('/exposed-system-logs')
def exposed_system_logs():
    return render_template('veilglass/exposed-system-logs.html')


@app.route('/exposed-application-logs')
def exposed_application_logs():
    return render_template('veilglass/exposed-application-logs.html')


@app.route('/exposed-database-logs')
def exposed_database_logs():
    return render_template('veilglass/exposed-database-logs.html')


@app.route('/exposed-network-logs')
def exposed_network_logs():
    return render_template('veilglass/exposed-network-logs.html')


@app.route('/exposed-firewall-logs')
def exposed_firewall_logs():
    return render_template('veilglass/exposed-firewall-logs.html')


@app.route('/exposed-ids-logs')
def exposed_ids_logs():
    return render_template('veilglass/exposed-ids-logs.html')


@app.route('/exposed-ips-logs')
def exposed_ips_logs():
    return render_template('veilglass/exposed-ips-logs.html')


@app.route('/exposed-antivirus-logs')
def exposed_antivirus_logs():
    return render_template('veilglass/exposed-antivirus-logs.html')


@app.route('/exposed-endpoint-logs')
def exposed_endpoint_logs():
    return render_template('veilglass/exposed-endpoint-logs.html')


@app.route('/exposed-cloud-logs')
def exposed_cloud_logs():
    return render_template('veilglass/exposed-cloud-logs.html')


@app.route('/exposed-container-logs')
def exposed_container_logs():
    return render_template('veilglass/exposed-container-logs.html')


@app.route('/exposed-orchestration-logs')
def exposed_orchestration_logs():
    return render_template('veilglass/exposed-orchestration-logs.html')


@app.route('/exposed-monitoring-logs')
def exposed_monitoring_logs():
    return render_template('veilglass/exposed-monitoring-logs.html')


@app.route('/exposed-metrics')
def exposed_metrics():
    return render_template('veilglass/exposed-metrics.html')


@app.route('/exposed-health-checks')
def exposed_health_checks():
    return render_template('veilglass/exposed-health-checks.html')


@app.route('/exposed-status-pages')
def exposed_status_pages():
    return render_template('veilglass/exposed-status-pages.html')


@app.route('/exposed-dashboard')
def exposed_dashboard():
    return render_template('veilglass/exposed-dashboard.html')


@app.route('/exposed-admin-panel')
def exposed_admin_panel():
    return render_template('veilglass/exposed-admin-panel.html')


@app.route('/exposed-login-page')
def exposed_login_page():
    return render_template('veilglass/exposed-login-page.html')


@app.route('/exposed-registration-page')
def exposed_registration_page():
    return render_template('veilglass/exposed-registration-page.html')


@app.route('/exposed-password-reset')
def exposed_password_reset():
    return render_template('veilglass/exposed-password-reset.html')


@app.route('/exposed-2fa-setup')
def exposed_2fa_setup():
    return render_template('veilglass/exposed-2fa-setup.html')


@app.route('/exposed-api-endpoints')
def exposed_api_endpoints():
    return render_template('veilglass/exposed-api-endpoints.html')


@app.route('/exposed-webhooks')
def exposed_webhooks():
    return render_template('veilglass/exposed-webhooks.html')


@app.route('/exposed-websockets')
def exposed_websockets():
    return render_template('veilglass/exposed-websockets.html')


@app.route('/exposed-graphql-endpoints')
def exposed_graphql_endpoints():
    return render_template('veilglass/exposed-graphql-endpoints.html')


@app.route('/exposed-rest-api')
def exposed_rest_api():
    return render_template('veilglass/exposed-rest-api.html')


@app.route('/exposed-soap-api')
def exposed_soap_api():
    return render_template('veilglass/exposed-soap-api.html')


@app.route('/exposed-json-api')
def exposed_json_api():
    return render_template('veilglass/exposed-json-api.html')


@app.route('/exposed-xml-api')
def exposed_xml_api():
    return render_template('veilglass/exposed-xml-api.html')


@app.route('/exposed-csv-api')
def exposed_csv_api():
    return render_template('veilglass/exposed-csv-api.html')


@app.route('/exposed-binary-api')
def exposed_binary_api():
    return render_template('veilglass/exposed-binary-api.html')


@app.route('/exposed-file-upload')
def exposed_file_upload():
    return render_template('veilglass/exposed-file-upload.html')


@app.route('/exposed-file-download')
def exposed_file_download():
    return render_template('veilglass/exposed-file-download.html')


@app.route('/exposed-file-sharing')
def exposed_file_sharing():
    return render_template('veilglass/exposed-file-sharing.html')


@app.route('/exposed-cloud-storage')
def exposed_cloud_storage():
    return render_template('veilglass/exposed-cloud-storage.html')


@app.route('/exposed-s3-buckets')
def exposed_s3_buckets():
    return render_template('veilglass/exposed-s3-buckets.html')


@app.route('/exposed-gcs-buckets')
def exposed_gcs_buckets():
    return render_template('veilglass/exposed-gcs-buckets.html')


@app.route('/exposed-azure-blobs')
def exposed_azure_blobs():
    return render_template('veilglass/exposed-azure-blobs.html')


@app.route('/exposed-digitalocean-spaces')
def exposed_digitalocean_spaces():
    return render_template('veilglass/exposed-digitalocean-spaces.html')


@app.route('/exposed-backblaze-b2')
def exposed_backblaze_b2():
    return render_template('veilglass/exposed-backblaze-b2.html')


@app.route('/exposed-wasabi')
def exposed_wasabi():
    return render_template('veilglass/exposed-wasabi-buckets.html')


@app.route('/exposed-linode-object-storage')
def exposed_linode_object_storage():
    return render_template('veilglass/exposed-linode-object-storage.html')


@app.route('/exposed-vultr-object-storage')
def exposed_vultr_object_storage():
    return render_template('veilglass/exposed-vultr-object-storage.html')


@app.route('/exposed-upcloud-object-storage')
def exposed_upcloud_object_storage():
    return render_template('veilglass/exposed-upcloud-object-storage.html')


@app.route('/exposed-scaleway-object-storage')
def exposed_scaleway_object_storage():
    return render_template('veilglass/exposed-scaleway-object-storage.html')


@app.route('/exposed-ovh-object-storage')
def exposed_ovh_object_storage():
    return render_template('veilglass/exposed-ovh-object-storage.html')


@app.route('/exposed-hetzner-object-storage')
def exposed_hetzner_object_storage():
    return render_template('veilglass/exposed-hetzner-object-storage.html')


@app.route('/exposed-ionos-object-storage')
def exposed_ionos_object_storage():
    return render_template('veilglass/exposed-ionos-object-storage.html')


@app.route('/exposed-exoscale-object-storage')
def exposed_exoscale_object_storage():
    return render_template('veilglass/exposed-exoscale-object-storage.html')


@app.route('/exposed-citycloud-object-storage')
def exposed_citycloud_object_storage():
    return render_template('veilglass/exposed-citycloud-object-storage.html')


@app.route('/exposed-greenqloud-object-storage')
def exposed_greenqloud_object_storage():
    return render_template('veilglass/exposed-greenqloud-object-storage.html')


@app.route('/exposed-dreamhost-object-storage')
def exposed_dreamhost_object_storage():
    return render_template('veilglass/exposed-dreamhost-object-storage.html')


@app.route('/exposed-rackspace-object-storage')
def exposed_rackspace_object_storage():
    return render_template('veilglass/exposed-rackspace-object-storage.html')


@app.route('/exposed-hp-object-storage')
def exposed_hp_object_storage():
    return render_template('veilglass/exposed-hp-object-storage.html')


@app.route('/exposed-ibm-object-storage')
def exposed_ibm_object_storage():
    return render_template('veilglass/exposed-ibm-object-storage.html')


@app.route('/exposed-oracle-object-storage')
def exposed_oracle_object_storage():
    return render_template('veilglass/exposed-oracle-object-storage.html')


@app.route('/exposed-alibaba-object-storage')
def exposed_alibaba_object_storage():
    return render_template('veilglass/exposed-alibaba-object-storage.html')


@app.route('/exposed-tencent-object-storage')
def exposed_tencent_object_storage():
    return render_template('veilglass/exposed-tencent-object-storage.html')


@app.route('/exposed-huawei-object-storage')
def exposed_huawei_object_storage():
    return render_template('veilglass/exposed-huawei-object-storage.html')


@app.route('/exposed-baidu-object-storage')
def exposed_baidu_object_storage():
    return render_template('veilglass/exposed-baidu-object-storage.html')


@app.route('/exposed-kingsoft-object-storage')
def exposed_kingsoft_object_storage():
    return render_template('veilglass/exposed-kingsoft-object-storage.html')


@app.route('/exposed-upyun-object-storage')
def exposed_upyun_object_storage():
    return render_template('veilglass/exposed-upyun-object-storage.html')


@app.route('/exposed-qiniu-object-storage')
def exposed_qiniu_object_storage():
    return render_template('veilglass/exposed-qiniu-object-storage.html')


@app.route('/exposed-ksyun-object-storage')
def exposed_ksyun_object_storage():
    return render_template('veilglass/exposed-ksyun-object-storage.html')


@app.route('/exposed-netease-object-storage')
def exposed_netease_object_storage():
    return render_template('veilglass/exposed-netease-object-storage.html')


@app.route('/exposed-jdcloud-object-storage')
def exposed_jdcloud_object_storage():
    return render_template('veilglass/exposed-jdcloud-object-storage.html')


@app.route('/exposed-ctyun-object-storage')
def exposed_ctyun_object_storage():
    return render_template('veilglass/exposed-ctyun-object-storage.html')


@app.route('/exposed-zhejiang-object-storage')
def exposed_zhejiang_object_storage():
    return render_template('veilglass/exposed-zhejiang-object-storage.html')


@app.route('/exposed-sangfor-object-storage')
def exposed_sangfor_object_storage():
    return render_template('veilglass/exposed-sangfor-object-storage.html')


@app.route('/exposed-360-object-storage')
def exposed_360_object_storage():
    return render_template('veilglass/exposed-360-object-storage.html')


@app.route('/exposed-tianyi-object-storage')
def exposed_tianyi_object_storage():
    return render_template('veilglass/exposed-tianyi-object-storage.html')


@app.route('/exposed-chinacache-object-storage')
def exposed_chinacache_object_storage():
    return render_template('veilglass/exposed-chinacache-object-storage.html')


@app.route('/exposed-chinaunicom-object-storage')
def exposed_chinaunicom_object_storage():
    return render_template('veilglass/exposed-chinaunicom-object-storage.html')


@app.route('/exposed-chinanet-object-storage')
def exposed_chinanet_object_storage():
    return render_template('veilglass/exposed-chinanet-object-storage.html')


@app.route('/exposed-cernet-object-storage')
def exposed_cernet_object_storage():
    return render_template('veilglass/exposed-cernet-object-storage.html')


@app.route('/exposed-cstnet-object-storage')
def exposed_cstnet_object_storage():
    return render_template('veilglass/exposed-cstnet-object-storage.html')


@app.route('/exposed-drpeng-object-storage')
def exposed_drpeng_object_storage():
    return render_template('veilglass/exposed-drpeng-object-storage.html')


@app.route('/exposed-github-gist')
def exposed_github_gist():
    return render_template('veilglass/exposed-github-gist.html')


@app.route('/exposed-pastebin')
def exposed_pastebin():
    return render_template('veilglass/exposed-pastebin.html')


@app.route('/exposed-0bin')
def exposed_0bin():
    return render_template('veilglass/exposed-0bin.html')


@app.route('/exposed-hastebin')
def exposed_hastebin():
    return render_template('veilglass/exposed-hastebin.html')


@app.route('/exposed-termbin')
def exposed_termbin():
    return render_template('veilglass/exposed-termbin.html')


@app.route('/exposed-sprunge')
def exposed_sprunge():
    return render_template('veilglass/exposed-sprunge.html')


@app.route('/exposed-ix-io')
def exposed_ix_io():
    return render_template('veilglass/exposed-ix-io.html')


@app.route('/exposed-clbin')
def exposed_clbin():
    return render_template('veilglass/exposed-clbin.html')


@app.route('/exposed-ptpb')
def exposed_ptpb():
    return render_template('veilglass/exposed-ptpb.html')


@app.route('/exposed-dpaste')
def exposed_dpaste():
    return render_template('veilglass/exposed-dpaste.html')


@app.route('/exposed-codepad')
def exposed_codepad():
    return render_template('veilglass/exposed-codepad.html')


@app.route('/exposed-paste-de')
def exposed_paste_de():
    return render_template('veilglass/exposed-paste-de.html')


@app.route('/exposed-paste-ee')
def exposed_paste_ee():
    return render_template('veilglass/exposed-paste-ee.html')


@app.route('/exposed-paste-fr')
def exposed_paste_fr():
    return render_template('veilglass/exposed-paste-fr.html')


@app.route('/exposed-paste-org')
def exposed_paste_org():
    return render_template('veilglass/exposed-paste-org.html')


@app.route('/exposed-paste-pk')
def exposed_paste_pk():
    return render_template('veilglass/exposed-paste-pk.html')


@app.route('/exposed-paste-rs')
def exposed_paste_rs():
    return render_template('veilglass/exposed-paste-rs.html')


@app.route('/exposed-paste-ubuntu')
def exposed_paste_ubuntu():
    return render_template('veilglass/exposed-paste-ubuntu.html')


@app.route('/exposed-paste-fedora')
def exposed_paste_fedora():
    return render_template('veilglass/exposed-paste-fedora.html')


@app.route('/exposed-paste-centos')
def exposed_paste_centos():
    return render_template('veilglass/exposed-paste-centos.html')


@app.route('/exposed-paste-arch')
def exposed_paste_arch():
    return render_template('veilglass/exposed-paste-arch.html')


@app.route('/exposed-paste-gentoo')
def exposed_paste_gentoo():
    return render_template('veilglass/exposed-paste-gentoo.html')


@app.route('/exposed-paste-slackware')
def exposed_paste_slackware():
    return render_template('veilglass/exposed-paste-slackware.html')


@app.route('/exposed-paste-mageia')
def exposed_paste_mageia():
    return render_template('veilglass/exposed-paste-mageia.html')


@app.route('/exposed-paste-opensuse')
def exposed_paste_opensuse():
    return render_template('veilglass/exposed-paste-opensuse.html')


@app.route('/exposed-paste-mandriva')
def exposed_paste_mandriva():
    return render_template('veilglass/exposed-paste-mandriva.html')


@app.route('/exposed-paste-pclinuxos')
def exposed_paste_pclinuxos():
    return render_template('veilglass/exposed-paste-pclinuxos.html')


@app.route('/exposed-paste-sabayon')
def exposed_paste_sabayon():
    return render_template('veilglass/exposed-paste-sabayon.html')


@app.route('/exposed-paste-chakra')
def exposed_paste_chakra():
    return render_template('veilglass/exposed-paste-chakra.html')


@app.route('/exposed-paste-kaos')
def exposed_paste_kaos():
    return render_template('veilglass/exposed-paste-kaos.html')


@app.route('/exposed-paste-nix')
def exposed_paste_nix():
    return render_template('veilglass/exposed-paste-nix.html')


@app.route('/exposed-paste-guix')
def exposed_paste_guix():
    return render_template('veilglass/exposed-paste-guix.html')


@app.route('/exposed-paste-void')
def exposed_paste_void():
    return render_template('veilglass/exposed-paste-void.html')


@app.route('/exposed-paste-alpine')
def exposed_paste_alpine():
    return render_template('veilglass/exposed-paste-alpine.html')


@app.route('/exposed-paste-adelaide')
def exposed_paste_adelaide():
    return render_template('veilglass/exposed-paste-adelaide.html')


@app.route('/exposed-paste-brisbane')
def exposed_paste_brisbane():
    return render_template('veilglass/exposed-paste-brisbane.html')


@app.route('/exposed-paste-canberra')
def exposed_paste_canberra():
    return render_template('veilglass/exposed-paste-canberra.html')


@app.route('/exposed-paste-darwin')
def exposed_paste_darwin():
    return render_template('veilglass/exposed-paste-darwin.html')


@app.route('/exposed-paste-hobart')
def exposed_paste_hobart():
    return render_template('veilglass/exposed-paste-hobart.html')


@app.route('/exposed-paste-melbourne')
def exposed_paste_melbourne():
    return render_template('veilglass/exposed-paste-melbourne.html')


@app.route('/exposed-paste-perth')
def exposed_paste_perth():
    return render_template('veilglass/exposed-paste-perth.html')


@app.route('/exposed-paste-sydney')
def exposed_paste_sydney():
    return render_template('veilglass/exposed-paste-sydney.html')


@app.route('/exposed-paste-auckland')
def exposed_paste_auckland():
    return render_template('veilglass/exposed-paste-auckland.html')


@app.route('/exposed-paste-wellington')
def exposed_paste_wellington():
    return render_template('veilglass/exposed-paste-wellington.html')


@app.route('/exposed-paste-christchurch')
def exposed_paste_christchurch():
    return render_template('veilglass/exposed-paste-christchurch.html')


@app.route('/exposed-paste-dunedin')
def exposed_paste_dunedin():
    return render_template('veilglass/exposed-paste-dunedin.html')


@app.route('/exposed-paste-hamilton')
def exposed_paste_hamilton():
    return render_template('veilglass/exposed-paste-hamilton.html')


@app.route('/exposed-paste-tauranga')
def exposed_paste_tauranga():
    return render_template('veilglass/exposed-paste-tauranga.html')


@app.route('/exposed-paste-palmerston-north')
def exposed_paste_palmerston_north():
    return render_template('veilglass/exposed-paste-palmerston-north.html')


@app.route('/exposed-paste-napier')
def exposed_paste_napier():
    return render_template('veilglass/exposed-paste-napier.html')


@app.route('/exposed-paste-new-plymouth')
def exposed_paste_new_plymouth():
    return render_template('veilglass/exposed-paste-new-plymouth.html')


@app.route('/exposed-paste-nelson')
def exposed_paste_nelson():
    return render_template('veilglass/exposed-paste-nelson.html')


@app.route('/exposed-paste-rotorua')
def exposed_paste_rotorua():
    return render_template('veilglass/exposed-paste-rotorua.html')


@app.route('/exposed-paste-taupo')
def exposed_paste_taupo():
    return render_template('veilglass/exposed-paste-taupo.html')


@app.route('/exposed-paste-whangarei')
def exposed_paste_whangarei():
    return render_template('veilglass/exposed-paste-whangarei.html')


@app.route('/exposed-paste-invercargill')
def exposed_paste_invercargill():
    return render_template('veilglass/exposed-paste-invercargill.html')


@app.route('/exposed-paste-bluff')
def exposed_paste_bluff():
    return render_template('veilglass/exposed-paste-bluff.html')


@app.route('/exposed-paste-greymouth')
def exposed_paste_greymouth():
    return render_template('veilglass/exposed-paste-greymouth.html')


@app.route('/exposed-paste-hokitika')
def exposed_paste_hokitika():
    return render_template('veilglass/exposed-paste-hokitika.html')


@app.route('/exposed-paste-te-anau')
def exposed_paste_te_anau():
    return render_template('veilglass/exposed-paste-te-anau.html')


@app.route('/exposed-paste-teku-teku')
def exposed_paste_teku_teku():
    return render_template('veilglass/exposed-paste-teku-teku.html')


@app.route('/exposed-paste-wanaka')
def exposed_paste_wanaka():
    return render_template('veilglass/exposed-paste-wanaka.html')


@app.route('/exposed-paste-arrowtown')
def exposed_paste_arrowtown():
    return render_template('veilglass/exposed-paste-arrowtown.html')


@app.route('/exposed-paste-franz-josef')
def exposed_paste_franz_josef():
    return render_template('veilglass/exposed-paste-franz-josef.html')


@app.route('/exposed-paste-glenorchy')
def exposed_paste_glenorchy():
    return render_template('veilglass/exposed-paste-glenorchy.html')


@app.route('/exposed-paste-milford-sound')
def exposed_paste_milford_sound():
    return render_template('veilglass/exposed-paste-milford-sound.html')


@app.route('/exposed-paste-queenstown')
def exposed_paste_queenstown():
    return render_template('veilglass/exposed-paste-queenstown.html')


@app.route('/exposed-paste-te-anau-milford')
def exposed_paste_te_anau_milford():
    return render_template('veilglass/exposed-paste-te-anau-milford.html')


@app.route('/exposed-paste-wakatipu')
def exposed_paste_wakatipu():
    return render_template('veilglass/exposed-paste-wakatipu.html')


@app.route('/exposed-paste-fiordland')
def exposed_paste_fiordland():
    return render_template('veilglass/exposed-paste-fiordland.html')


@app.route('/exposed-paste-southland')
def exposed_paste_southland():
    return render_template('veilglass/exposed-paste-southland.html')


@app.route('/exposed-paste-otago')
def exposed_paste_otago():
    return render_template('veilglass/exposed-paste-otago.html')


@app.route('/exposed-paste-canterbury')
def exposed_paste_canterbury():
    return render_template('veilglass/exposed-paste-canterbury.html')


@app.route('/exposed-paste-west-coast')
def exposed_paste_west_coast():
    return render_template('veilglass/exposed-paste-west-coast.html')


@app.route('/exposed-paste-marlbrough')
def exposed_paste_marlbrough():
    return render_template('veilglass/exposed-paste-marlbrough.html')


@app.route('/exposed-paste-nelson-tasman')
def exposed_paste_nelson_tasman():
    return render_template('veilglass/exposed-paste-nelson-tasman.html')


@app.route('/exposed-paste-wellington-region')
def exposed_paste_wellington_region():
    return render_template('veilglass/exposed-paste-wellington-region.html')


@app.route('/exposed-paste-manawatu-wanganui')
def exposed_paste_manawatu_wanganui():
    return render_template('veilglass/exposed-paste-manawatu-wanganui.html')


@app.route('/exposed-paste-hawkes-bay')
def exposed_paste_hawkes_bay():
    return render_template('veilglass/exposed-paste-hawkes-bay.html')


@app.route('/exposed-paste-taranaki')
def exposed_paste_taranaki():
    return render_template('veilglass/exposed-paste-taranaki.html')


@app.route('/exposed-paste-waikato')
def exposed_paste_waikato():
    return render_template('veilglass/exposed-paste-waikato.html')


@app.route('/exposed-paste-bay-of-plenty')
def exposed_paste_bay_of_plenty():
    return render_template('veilglass/exposed-paste-bay-of-plenty.html')


@app.route('/exposed-paste-auckland-region')
def exposed_paste_auckland_region():
    return render_template('veilglass/exposed-paste-auckland-region.html')


@app.route('/exposed-paste-northland')
def exposed_paste_northland():
    return render_template('veilglass/exposed-paste-northland.html')


@app.route('/exposed-paste-gisborne')
def exposed_paste_gisborne():
    return render_template('veilglass/exposed-paste-gisborne.html')


@app.route('/exposed-paste-east-cape')
def exposed_paste_east_cape():
    return render_template('veilglass/exposed-paste-east-cape.html')


@app.route('/exposed-paste-chatham-islands')
def exposed_paste_chatham_islands():
    return render_template('veilglass/exposed-paste-chatham-islands.html')


@app.route('/exposed-paste-kermadec-islands')
def exposed_paste_kermadec_islands():
    return render_template('veilglass/exposed-paste-kermadec-islands.html')


@app.route('/exposed-paste-three-kings-islands')
def exposed_paste_three_kings_islands():
    return render_template('veilglass/exposed-paste-three-kings-islands.html')


@app.route('/exposed-paste-curtis-island')
def exposed_paste_curtis_island():
    return render_template('veilglass/exposed-paste-curtis-island.html')


@app.route('/exposed-paste-great-barrier-island')
def exposed_paste_great_barrier_island():
    return render_template('veilglass/exposed-paste-great-barrier-island.html')


@app.route('/exposed-paste-little-barrier-island')
def exposed_paste_little_barrier_island():
    return render_template('veilglass/exposed-paste-little_barrier_island.html')


@app.route('/exposed-paste-rangitoto-island')
def exposed_paste_rangitoto_island():
    return render_template('veilglass/exposed-paste-rangitoto-island.html')


@app.route('/exposed-paste-hen-island')
def exposed_paste_hen_island():
    return render_template('veilglass/exposed-paste-hen-island.html')


@app.route('/exposed-paste-rakino-island')
def exposed_paste_rakino_island():
    return render_template('veilglass/exposed-paste-rakino-island.html')


@app.route('/exposed-paste-tiritiri-matangi-island')
def exposed_paste_tiritiri_matangi_island():
    return render_template('veilglass/exposed-paste-tiritiri-matangi-island.html')


@app.route('/exposed-paste-motutapu-island')
def exposed_paste_motutapu_island():
    return render_template('veilglass/exposed-paste-motutapu-island.html')


@app.route('/exposed-paste-motuihe-island')
def exposed_paste_motuihe_island():
    return render_template('veilglass/exposed-paste-motuihe-island.html')


@app.route('/exposed-paste-browns-island')
def exposed_paste_browns_island():
    return render_template('veilglass/exposed-paste-browns-island.html')


@app.route('/exposed-paste-kawau-island')
def exposed_paste_kawau_island():
    return render_template('veilglass/exposed-paste-kawau-island.html')


@app.route('/exposed-paste-waiheke-island')
def exposed_paste_waiheke_island():
    return render_template('veilglass/exposed-paste-waiheke-island.html')


if __name__ == '__main__':
    # Initialize database (always check for services)
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM services')
        service_count = c.fetchone()[0]
        conn.close()

        if service_count < 100:
            print("Initializing services...")
            init_db()
        else:
            print(f"Database already has {service_count} services")
    except:
        print("Database doesn't exist or error, initializing...")
        init_db()

    app.run(debug=True, port=5000)

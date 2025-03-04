# Load AI model for email content generation
# generator = pipeline("text-generation", model="gpt2")
import os
import re
import pandas as pd
import smtplib
import uuid
import hashlib
import jwt
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, render_template, url_for, send_from_directory, session
from flask_cors import CORS
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from werkzeug.utils import secure_filename
import warnings
import threading
import webbrowser
import tempfile
from io import BytesIO
from flask import Response, session
import numpy as np
from pathlib import Path
#from transformers import pipeline
import mysql.connector
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Flask & JWT Secret Keys
SECRET_KEY = os.getenv("SECRET_KEY")
JWT_SECRET = os.getenv("JWT_SECRET")

# Database Configuration
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# SMTP Email Configuration
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Connect to MySQL
def connect_db():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

# Example function: Get user by email
def get_user_by_email(email):
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    conn.close()
    return user


# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning)

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = "your-flask-secret-key"  # Important for session management
CORS(app)  # Allow frontend requests

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Secret key for JWT tokens
JWT_SECRET = "your-secret-key"  # In production, use a secure secret and environment variables

# Database setup
DATABASE_PATH = 'data/users.db'

# Load AI model for email content generation
#generator = pipeline("text-generation", model="gpt2")

# Create data directory if it doesn't exist
Path("data").mkdir(exist_ok=True)

def init_db():
    """Initialize the database with users table"""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        ''')
        conn.commit()

# In-memory storage for uploaded email lists (not persisting these for now)
email_lists = {}

def allowed_file(filename):
    """Check if file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def hash_password(password):
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def is_valid_email(email):
    """Validate email format using regex."""
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None

def get_user_by_id(user_id):
    """Get user by ID from database"""
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if user:
            return dict(user)
        return None

def get_user_by_email(email):
    """Get user by email from database"""
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        if user:
            return dict(user)
        return None

# Simple email content generation (placeholder for AI model)
def generate_email_content(prompt):
    """Generate email content based on a prompt."""
    # This is a simple placeholder. In production, you'd use an actual AI model
    templates = {
        "sales": "Dear {name},\n\nI hope this email finds you well. We're excited to share our latest products with you.\n\nBest regards,\nThe Sales Team",
        "newsletter": "Hello {name},\n\nWelcome to our monthly newsletter. Here are the latest updates from our company.\n\nBest,\nThe Newsletter Team",
        "follow-up": "Hi {name},\n\nJust following up on our previous conversation. Let me know if you have any questions.\n\nRegards,\nCustomer Support",
        "default": "Hello {name},\n\nThank you for your interest in our services. Please let me know if you need any further information.\n\nBest regards,\nArrow Email Assistant"
    }
    
    # Determine template based on keywords in prompt
    if "sales" in prompt.lower() or "product" in prompt.lower():
        return templates["sales"]
    elif "newsletter" in prompt.lower() or "update" in prompt.lower():
        return templates["newsletter"]
    elif "follow" in prompt.lower() or "previous" in prompt.lower():
        return templates["follow-up"]
    else:
        return templates["default"]
    
# Add these routes to your existing email_sender.py file

# Admin dashboard routes
@app.route('/admin')
def admin_login_page():
    """Render admin login page"""
    return render_template('admin_login.html')

@app.route('/admin/login', methods=['POST'])
def admin_login():
    """Handle admin login"""
    data = request.json
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'success': False, 'message': 'Missing email or password'}), 400
        
    email = data['email'].lower().strip()
    password_hash = hash_password(data['password'])
    
    # Check if user exists and is admin
    user = get_user_by_email(email)
    
    if not user or user['password'] != password_hash or email != 'admin@example.com':
        return jsonify({'success': False, 'message': 'Invalid admin credentials'}), 401
    
    # Generate admin JWT token
    token = jwt.encode({
        'user_id': user['id'],
        'email': user['email'],
        'is_admin': True,
        'exp': datetime.utcnow() + timedelta(hours=12)  # Admin token expires in 12 hours
    }, JWT_SECRET, algorithm="HS256")
    
    return jsonify({
        'success': True,
        'message': 'Admin login successful',
        'token': token
    }), 200

# Admin authorization decorator
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
        if not token:
            return jsonify({'success': False, 'message': 'Admin token is missing'}), 401
            
        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            
            if not data.get('is_admin', False):
                raise Exception("Not an admin user")
                
            current_admin = get_user_by_id(data['user_id'])
            
            if not current_admin or current_admin['email'] != 'admin@example.com':
                raise Exception("Invalid admin user")
                
        except Exception as e:
            return jsonify({'success': False, 'message': 'Invalid admin token'}), 401
            
        return f(current_admin, *args, **kwargs)
    
    return decorated

@app.route('/admin/dashboard')
def admin_dashboard_page():
    """Render admin dashboard page"""
    return render_template('admin_dashboard.html')

# Define the send_welcome_email function before create_user
def send_welcome_email(email, name, password):
    """Send a welcome email to the new user with their login credentials."""
    try:
        # Email configuration (replace with your SMTP server details)
        smtp_server = "smtp.gmail.com"  # Replace with your SMTP server
        smtp_port = 587  # Replace with your SMTP port
        sender_email = "krixh15@gmail.com  "  # Replace with your sender email
        sender_password = "wywy rwgt bxak frxe"  # Replace with your sender email password

        # Create the email content
        subject = "Welcome to Our Platform!"
        body = f"""
        Hello {name},

        Welcome to our platform! Your account has been successfully created.

        Here are your login credentials:
        - Email: {email}
        - Password: {password}

        Please log in to your account and change your password after your first login.

        Best regards,
        The Admin Team
        """

        # Create the email message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Connect to the SMTP server and send the email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Secure the connection
            server.login(sender_email, sender_password)
            server.send_message(msg)

        print(f"Welcome email sent to {email}")
    except Exception as e:
        print(f"Failed to send welcome email to {email}: {str(e)}")

# Now define the create_user function
@app.route('/api/admin/users', methods=['POST'])
@admin_required
def create_user_admin(current_admin):
    """Create a new user from the admin panel"""
    data = request.json
    
    if not data or not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
    email = data['email'].lower().strip()
    
    # Check if email is valid
    if not is_valid_email(email):
        return jsonify({'success': False, 'message': 'Invalid email format'}), 400
        
    # Check if user already exists
    if get_user_by_email(email):
        return jsonify({'success': False, 'message': 'Email already registered'}), 400
    
    try:
        # Create new user
        user_id = str(uuid.uuid4())
        
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO users (id, name, email, password, created_at)
            VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id,
                data['name'],
                email,
                hash_password(data['password']),
                datetime.now().isoformat()
            ))
            conn.commit()
        
        # Send welcome email with login credentials
        send_welcome_email(
            email=data['email'],
            name=data['name'],
            password=data['password']
        )
        
        return jsonify({
            'success': True, 
            'message': 'User created successfully',
            'user_id': user_id
        }), 201
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error creating user: {str(e)}'}), 500
    
@app.route('/api/admin/users', methods=['GET'])
@admin_required
def get_all_users(current_admin):
    """Get all users for admin"""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, email, created_at FROM users")
            users = [dict(row) for row in cursor.fetchall()]
            
        return jsonify({
            'success': True,
            'users': users
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error fetching users: {str(e)}'}), 500

@app.route('/api/admin/users/<user_id>', methods=['DELETE'])
@admin_required
def delete_user(current_admin, user_id):
    """Delete a user"""
    try:
        # Don't allow deleting the admin user
        user = get_user_by_id(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
            
        if user['email'] == 'admin@example.com':
            return jsonify({'success': False, 'message': 'Cannot delete admin user'}), 403
        
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            
        return jsonify({
            'success': True,
            'message': 'User deleted successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error deleting user: {str(e)}'}), 500
    
    # Add these routes to your existing email_sender.py file

@app.route('/api/admin/users', methods=['POST'])
@admin_required
def create_user(current_admin):
    """Create a new user from the admin panel"""
    data = request.json
    
    if not data or not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
    email = data['email'].lower().strip()
    
    # Check if email is valid
    if not is_valid_email(email):
        return jsonify({'success': False, 'message': 'Invalid email format'}), 400
        
    # Check if user already exists
    if get_user_by_email(email):
        return jsonify({'success': False, 'message': 'Email already registered'}), 400
    
    try:
        # Create new user
        user_id = str(uuid.uuid4())
        
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO users (id, name, email, password, created_at)
            VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id,
                data['name'],
                email,
                hash_password(data['password']),
                datetime.now().isoformat()
            ))
            conn.commit()
        
        # Send welcome email with login credentials
        send_welcome_email(
            email=data['email'],
            name=data['name'],
            password=data['password']
        )
        
        return jsonify({
            'success': True, 
            'message': 'User created successfully',
            'user_id': user_id
        }), 201
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error creating user: {str(e)}'}), 500
    
@app.route('/api/admin/users/<user_id>', methods=['PUT'])
@admin_required
def update_user(current_admin, user_id):
    """Update an existing user"""
    data = request.json
    
    if not data or (not data.get('name') and not data.get('email') and not data.get('password')):
        return jsonify({'success': False, 'message': 'No update data provided'}), 400
    
    # Get the user to update
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
        
    # Don't allow updating admin's email to non-admin
    if user['email'] == 'admin@example.com' and data.get('email') and data['email'] != 'admin@example.com':
        return jsonify({'success': False, 'message': 'Cannot change admin email'}), 403
    
    # Prepare update data
    update_fields = []
    update_values = []
    
    if data.get('name'):
        update_fields.append("name = ?")
        update_values.append(data['name'])
        
    if data.get('email'):
        email = data['email'].lower().strip()
        
        # Check if email is valid
        if not is_valid_email(email):
            return jsonify({'success': False, 'message': 'Invalid email format'}), 400
            
        # Check if email is already in use by another user
        existing_user = get_user_by_email(email)
        if existing_user and existing_user['id'] != user_id:
            return jsonify({'success': False, 'message': 'Email already in use by another user'}), 400
            
        update_fields.append("email = ?")
        update_values.append(email)
        
    if data.get('password'):
        update_fields.append("password = ?")
        update_values.append(hash_password(data['password']))
    
    if not update_fields:
        return jsonify({'success': False, 'message': 'No valid update data provided'}), 400
    
    try:
        # Update the user
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
            update_values.append(user_id)
            cursor.execute(query, update_values)
            conn.commit()
            
        return jsonify({
            'success': True,
            'message': 'User updated successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error updating user: {str(e)}'}), 500

@app.route('/api/admin/users/<user_id>', methods=['GET'])
@admin_required
def get_user(current_admin, user_id):
    """Get a single user by ID"""
    user = get_user_by_id(user_id)
    
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
        
    # Don't include password in the response
    if 'password' in user:
        del user['password']
        
    return jsonify({
        'success': True,
        'user': user
    }), 200

# Enhanced route for filtering users
@app.route('/api/admin/users/filtered', methods=['GET'])
@admin_required
def get_filtered_users(current_admin):
    """Get all users with optional filtering"""
    try:
        # Get query parameters for filtering
        name_filter = request.args.get('name', '').lower()
        email_filter = request.args.get('email', '').lower()
        created_after = request.args.get('created_after', '')
        created_before = request.args.get('created_before', '')

        # Base query
        query = "SELECT id, name, email, created_at FROM users WHERE 1=1"
        params = []

        # Apply name filter
        if name_filter:
            query += " AND LOWER(name) LIKE ?"
            params.append(f"%{name_filter}%")

        # Apply email filter
        if email_filter:
            query += " AND LOWER(email) LIKE ?"
            params.append(f"%{email_filter}%")

        # Apply created_after filter
        if created_after:
            query += " AND created_at >= ?"
            params.append(created_after)

        # Apply created_before filter
        if created_before:
            query += " AND created_at <= ?"
            params.append(created_before)

        # Execute the query
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            users = [dict(row) for row in cursor.fetchall()]

        return jsonify({
            'success': True,
            'users': users
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error fetching users: {str(e)}'}), 500
    
@app.route('/api/admin/email-lists', methods=['GET'])
@admin_required
def get_all_email_lists(current_admin):
    """Get all email lists for the admin dashboard."""
    try:
        # Retrieve all email lists from the in-memory storage
        lists = []
        for list_id, list_data in email_lists.items():
            lists.append({
                'id': list_id,
                'filename': list_data['filename'],
                'created_at': list_data['created_at'],
                'user_id': list_data['user_id'],
                'valid_count': len(list_data['emails']),
                'invalid_count': list_data.get('invalid_count', 0)
            })

        return jsonify({
            'success': True,
            'email_lists': lists
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error fetching email lists: {str(e)}'}), 500
    
@app.route('/api/admin/email-lists/<list_id>', methods=['DELETE'])
@admin_required
def delete_email_list(current_admin, list_id):
    """Delete an email list."""
    try:
        if list_id not in email_lists:
            return jsonify({'success': False, 'message': 'Email list not found'}), 404

        # Delete the email list
        del email_lists[list_id]

        return jsonify({
            'success': True,
            'message': 'Email list deleted successfully'
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error deleting email list: {str(e)}'}), 500
    
@app.route('/api/admin/email-lists/<list_id>', methods=['GET'])
@admin_required
def get_email_list_details(current_admin, list_id):
    """Get details of a specific email list."""
    try:
        if list_id not in email_lists:
            return jsonify({'success': False, 'message': 'Email list not found'}), 404

        list_data = email_lists[list_id]
        return jsonify({
            'success': True,
            'email_list': {
                'id': list_id,
                'filename': list_data['filename'],
                'created_at': list_data['created_at'],
                'user_id': list_data['user_id'],
                'valid_emails': list_data['emails'],
                'invalid_emails': list_data.get('invalid_emails', [])
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error fetching email list details: {str(e)}'}), 500
    
@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """Return system statistics"""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get user count
            cursor.execute("SELECT COUNT(*) AS total_users FROM users")
            total_users = cursor.fetchone()["total_users"]

            # Check if sent_emails table exists before querying
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sent_emails'")
            table_exists = cursor.fetchone()
            
            total_emails = 0
            if table_exists:
                cursor.execute("SELECT COUNT(*) AS total_emails FROM sent_emails")
                total_emails = cursor.fetchone()["total_emails"]

            return jsonify({
                "success": True,
                "statistics": {
                    "total_users": total_users,
                    "total_emails": total_emails
                }
            })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# Update the data-visualization route to better handle Excel files
@app.route('/data-visualization', methods=['GET', 'POST'])
def data_visualization():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file part in the request'}), 400
        
        file = request.files['file']
        
        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No selected file'}), 400
        
        # Check if the file type is allowed
        if file and allowed_file(file.filename):
            temp_file = None
            try:
                # Create a temporary file to avoid file IO issues
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp:
                    temp_file = temp.name
                    file.save(temp_file)
                    
                    # Read the file based on its extension with error handling
                    if file.filename.endswith('.csv'):
                        # Handle potential encoding issues and separator detection
                        try:
                            df = pd.read_csv(temp_file)
                        except UnicodeDecodeError:
                            # Try with different encoding if UTF-8 fails
                            df = pd.read_csv(temp_file, encoding='latin1')
                        except pd.errors.ParserError:
                            # Try with different separators if comma fails
                            df = pd.read_csv(temp_file, sep=None, engine='python')
                    elif file.filename.endswith(('.xlsx', '.xls')):
                        try:
                            df = pd.read_excel(temp_file)
                        except Exception as excel_error:
                            return jsonify({'success': False, 'message': f'Error reading Excel file: {str(excel_error)}'}), 400
                    else:
                        return jsonify({'success': False, 'message': 'Unsupported file format'}), 400
                
                # Handle missing values
                # Replace NaN values with empty strings for JSON serialization
                df = df.replace({np.nan: None})
                
                # Process the data to handle any potential issues
                processed_data = []
                for _, row in df.iterrows():
                    row_dict = {}
                    for col in df.columns:
                        # Handle different types of data and missing values
                        value = row[col]
                        if pd.isna(value) or value is None:
                            row_dict[col] = None
                        elif isinstance(value, (int, float)):
                            row_dict[col] = value
                        else:
                            # Convert to string to avoid JSON serialization issues
                            row_dict[col] = str(value)
                    processed_data.append(row_dict)
                
                # Store the processed data in session
                session['uploaded_data'] = processed_data
                session['original_filename'] = file.filename
                
                # Extract headers (column names)
                headers = df.columns.tolist()
                
                # Return the headers and sample data to the frontend
                return jsonify({
                    'success': True,
                    'message': 'File uploaded successfully',
                    'headers': headers,
                    'data': processed_data[:50]  # Send first 50 rows to frontend
                }), 200
            
            except Exception as e:
                # Log the full error for debugging
                import traceback
                print(f"Error processing file: {str(e)}")
                print(traceback.format_exc())
                return jsonify({'success': False, 'message': f'Error processing file: {str(e)}'}), 500
            
            finally:
                # Clean up temporary file
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.unlink(temp_file)
                    except:
                        pass
        
        return jsonify({'success': False, 'message': 'File type not allowed'}), 400
    
    # Render the data visualization page for GET requests
    return render_template('data_visualization.html')

@app.route('/search-data', methods=['POST'])
def search_data():
    data = request.json
    selected_columns = data.get('selected_columns', [])
    numeric_filter = data.get('numeric_filter', None)
    
    if not selected_columns:
        return jsonify({'success': False, 'message': 'No columns selected'}), 400
    
    try:
        # Retrieve the uploaded data from the session
        if 'uploaded_data' not in session:
            return jsonify({'success': False, 'message': 'No file uploaded. Please upload a file first.'}), 400
        
        uploaded_data = session['uploaded_data']
        
        # Filter the data to include only the selected columns
        filtered_data = []
        for item in uploaded_data:
            # Apply numeric filter if specified
            if numeric_filter:
                column = numeric_filter['column']
                threshold = numeric_filter['threshold']
                
                if column in item:
                    value = item[column]
                    
                    # Skip items that don't meet the numeric threshold
                    if value is not None and value != '':
                        try:
                            num_value = float(value)
                            if num_value < threshold:
                                continue
                        except (ValueError, TypeError):
                            # Skip non-numeric values if filtering by a numeric column
                            continue
            
            filtered_item = {}
            for col in selected_columns:
                # Check if the column exists in the item
                if col in item:
                    filtered_item[col] = item[col]
                else:
                    # Handle missing columns
                    filtered_item[col] = None
            filtered_data.append(filtered_item)
        
        # Store the filtered results in the session for download
        session['filtered_data'] = filtered_data
        
        return jsonify({
            'success': True,
            'message': 'Search successful',
            'results': filtered_data
        }), 200
    
    except Exception as e:
        import traceback
        print(f"Error searching data: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': f'Error searching data: {str(e)}'}), 500
    
# Add a new route for downloading the filtered data as Excel
@app.route('/download-results', methods=['GET'])
def download_results():
    try:
        # Check if filtered data exists in session
        if 'filtered_data' not in session or 'original_filename' not in session:
            return jsonify({'success': False, 'message': 'No filtered data available to download'}), 400
        
        # Get filtered data
        filtered_data = session.get('filtered_data')
        original_filename = session.get('original_filename')
        
        # Create DataFrame from filtered data
        df = pd.DataFrame(filtered_data)
        
        # Generate Excel file in memory
        output = BytesIO()
        
        # Get filename without extension
        base_filename = os.path.splitext(original_filename)[0]
        download_filename = f"{base_filename}_filtered.xlsx"
        
        # Create Excel writer
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Filtered Data', index=False)
            
            # Auto-adjust columns' width
            worksheet = writer.sheets['Filtered Data']
            for i, col in enumerate(df.columns):
                # Calculate column width based on content
                max_len = df[col].astype(str).map(lambda x: len(str(x)) if x else 0).max()
                col_len = max(max_len, len(col)) + 2
                worksheet.set_column(i, i, col_len)
        
        # Seek to beginning of file
        output.seek(0)
        
        # Create response with Excel file
        return Response(
            output.getvalue(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={
                'Content-Disposition': f'attachment; filename="{download_filename}"',
                'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
        )
    
    except Exception as e:
        import traceback
        print(f"Error downloading data: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': f'Error downloading data: {str(e)}'}), 500
    
# Authentication decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
        if not token:
            return jsonify({'success': False, 'message': 'Token is missing'}), 401
            
        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            current_user = get_user_by_id(data['user_id'])
            
            if not current_user:
                raise Exception("User not found")
                
        except Exception as e:
            return jsonify({'success': False, 'message': 'Invalid token'}), 401
            
        return f(current_user, *args, **kwargs)
    
    return decorated

# Serve static files
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

# Serve the frontend
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.json
    
    if not data or not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
    email = data['email'].lower().strip()
    
    # Check if email is valid
    if not is_valid_email(email):
        return jsonify({'success': False, 'message': 'Invalid email format'}), 400
        
    # Check if user already exists
    if get_user_by_email(email):
        return jsonify({'success': False, 'message': 'Email already registered'}), 400
    
    try:
        # Create new user
        user_id = str(uuid.uuid4())
        
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO users (id, name, email, password, created_at)
            VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id,
                data['name'],
                email,
                hash_password(data['password']),
                datetime.now().isoformat()
            ))
            conn.commit()
        
        return jsonify({'success': True, 'message': 'User registered successfully'}), 201
    
    except Exception as e:
        import traceback
        print(f"Error registering user: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': f'Error registering user: {str(e)}'}), 500

@app.route('/login', methods=['POST'])
def login():
    """Authenticate a user and return a JWT token."""
    data = request.json
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'success': False, 'message': 'Missing email or password'}), 400
        
    email = data['email'].lower().strip()
    password_hash = hash_password(data['password'])
    
    # Find user by email
    user = get_user_by_email(email)
            
    if not user or user['password'] != password_hash:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
    # Generate JWT token
    token = jwt.encode({
        'user_id': user['id'],
        'email': user['email'],
        'exp': datetime.utcnow() + timedelta(hours=24)  # Token expires in 24 hours
    }, JWT_SECRET, algorithm="HS256")
    
    return jsonify({
        'success': True,
        'message': 'Login successful',
        'userId': user['id'],
        'name': user['name'],
        'email': user['email'],
        'token': token
    }), 200

@app.route('/user-profile', methods=['GET'])
@token_required
def get_user_profile(current_user):
    """Get the current user's profile information."""
    return jsonify({
        'success': True,
        'user': {
            'id': current_user['id'],
            'name': current_user['name'],
            'email': current_user['email'],
            'created_at': current_user['created_at']
        }
    })

@app.route('/upload-email-list', methods=['POST'])
@token_required
def upload_email_list(current_user):
    """Upload and process an email list."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'}), 400
        
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        try:
            # Read the file with error handling
            if filename.endswith('.csv'):
                try:
                    df = pd.read_csv(file_path)
                except UnicodeDecodeError:
                    # Try with different encoding if UTF-8 fails
                    df = pd.read_csv(file_path, encoding='latin1')
                except pd.errors.ParserError:
                    # Try with different separators if comma fails
                    df = pd.read_csv(file_path, sep=None, engine='python')
            else:
                df = pd.read_excel(file_path)
                
            # Validate required columns
            if 'email' not in df.columns:
                return jsonify({'success': False, 'message': 'File must contain an "email" column'}), 400
                
            # Create email list ID
            list_id = str(uuid.uuid4())
            
            # Clean and validate emails
            valid_emails = []
            invalid_emails = []
            
            for idx, row in df.iterrows():
                # Handle missing email values
                if pd.isna(row.get('email')) or row.get('email') is None:
                    continue
                    
                email = str(row['email']).strip().lower()
                if is_valid_email(email):
                    # Handle missing name values
                    name = ""
                    if 'name' in df.columns and not pd.isna(row.get('name')):
                        name = str(row.get('name', '')).strip()
                        
                    valid_emails.append({
                        'email': email,
                        'name': name
                    })
                else:
                    invalid_emails.append(email)
            
            # Store the email list
            email_lists[list_id] = {
                'user_id': current_user['id'],
                'filename': filename,
                'created_at': datetime.now().isoformat(),
                'emails': valid_emails
            }
            
            return jsonify({
                'success': True,
                'message': 'Email list uploaded successfully',
                'list_id': list_id,
                'valid_count': len(valid_emails),
                'invalid_count': len(invalid_emails),
                'emails': valid_emails
            }), 200
            
        except Exception as e:
            import traceback
            print(f"Error processing email list: {str(e)}")
            print(traceback.format_exc())
            return jsonify({'success': False, 'message': f'Error processing file: {str(e)}'}), 500
        finally:
            # Clean up uploaded file after processing
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
    
    return jsonify({'success': False, 'message': 'File type not allowed'}), 400

@app.route('/generate-email', methods=['POST'])
@token_required
def generate_email(current_user):
    """Generate email content using AI."""
    data = request.json
    
    if not data or not data.get('prompt'):
        return jsonify({'success': False, 'message': 'Missing prompt'}), 400
        
    prompt = data['prompt']
    
    try:
        # Generate email content
        content = generate_email_content(prompt)
        
        return jsonify({
            'success': True,
            'message': 'Email content generated successfully',
            'content': content
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error generating email: {str(e)}'}), 500

@app.route('/send-emails', methods=['POST'])
@token_required
def send_emails(current_user):
    """Send emails to a list of recipients."""
    data = request.json
    
    if not data or not data.get('list_id') or not data.get('subject') or not data.get('body') or not data.get('sender_email') or not data.get('smtp_server') or not data.get('smtp_port'):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
    list_id = data['list_id']
    subject = data['subject']
    body = data['body']
    sender_email = data['sender_email']
    sender_password = data.get('sender_password', '')
    smtp_server = data['smtp_server']
    smtp_port = int(data['smtp_port'])
    bcc_emails = [email.strip() for email in data.get('bcc_emails', '').split(',') if email.strip()]
    
    # Validate sender email
    if not is_valid_email(sender_email):
        return jsonify({'success': False, 'message': 'Invalid sender email'}), 400
        
    # Get the email list
    email_list = email_lists.get(list_id)
    
    if not email_list or email_list['user_id'] != current_user['id']:
        return jsonify({'success': False, 'message': 'Email list not found'}), 404
        
    try:
        # Connect to SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        
        # Send emails
        successful = []
        failed = []
        
        for recipient in email_list['emails']:
            try:
                # Create message
                msg = MIMEMultipart()
                msg['From'] = sender_email
                msg['To'] = recipient['email']
                msg['Subject'] = subject
                
                # Add BCC recipients
                if bcc_emails:
                    msg['Bcc'] = ', '.join(bcc_emails)
                
                # Personalize the message body
                personalized_body = body.replace('{name}', recipient.get('name', ''))
                msg.attach(MIMEText(personalized_body, 'plain'))
                
                # Send the email
                server.send_message(msg)
                successful.append(recipient['email'])
                
            except Exception as e:
                failed.append({
                    'email': recipient['email'],
                    'error': str(e)
                })
        
        # Close the connection
        server.quit()
        
        return jsonify({
            'success': True,
            'message': 'Emails sent',
            'successful_count': len(successful),
            'failed_count': len(failed),
            'failed_details': failed
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error sending emails: {str(e)}'}), 500

# Add a route to create an admin user 
@app.route('/create-admin', methods=['POST'])
def create_admin():
    """Create admin user - only accessible from localhost for security"""
    # Check if the request is coming from localhost
    if request.remote_addr != '127.0.0.1' and request.remote_addr != 'localhost':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    data = request.json
    
    if not data or not data.get('password'):
        return jsonify({'success': False, 'message': 'Missing password'}), 400
        
    try:
        # Check if admin already exists
        admin = get_user_by_email('admin@example.com')
        
        if admin:
            return jsonify({'success': False, 'message': 'Admin user already exists'}), 400
            
        # Create admin user
        admin_id = str(uuid.uuid4())
        
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO users (id, name, email, password, created_at)
            VALUES (?, ?, ?, ?, ?)
            ''', (
                admin_id,
                'Admin User',
                'admin@example.com',
                hash_password(data['password']),
                datetime.now().isoformat()
            ))
            conn.commit()
            
        return jsonify({'success': True, 'message': 'Admin user created successfully'}), 201
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error creating admin user: {str(e)}'}), 500

if __name__ == '__main__':
    # Initialize the database
    init_db()
    
    # Check if admin user exists, create if not
    admin = get_user_by_email('admin@example.com')
    if not admin:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            admin_id = str(uuid.uuid4())
            cursor.execute('''
            INSERT INTO users (id, name, email, password, created_at)
            VALUES (?, ?, ?, ?, ?)
            ''', (
                admin_id,
                'Admin User',
                'admin@example.com',
                hash_password('admin123'),
                datetime.now().isoformat()
            ))
            conn.commit()
        print("Default admin user created: admin@example.com / admin123")
    
    # Run the app
    app.run(debug=True)

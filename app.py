import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import random
import string
from datetime import datetime
import uuid
import qrcode
from io import BytesIO
import base64

# Initialize Flask app
app = Flask(__name__)

# Get the absolute path to the instance folder
instance_path = os.path.join(os.getcwd(), 'instance')
os.makedirs(instance_path, exist_ok=True)
os.chmod(instance_path, 0o777)

# Basic configuration
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'your-secret-key-here'),
    SQLALCHEMY_DATABASE_URI=f'sqlite:///{os.path.join(instance_path, "derby.db")}',
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    UPLOAD_FOLDER=os.path.join(os.getcwd(), 'static', 'uploads')
)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.chmod(app.config['UPLOAD_FOLDER'], 0o777)

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

class Car(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, unique=True, nullable=False)
    owner_name = db.Column(db.String(100), nullable=False)
    image_path = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    votes = db.Column(db.Integer, default=0)

class VoteCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(5), unique=True, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    used_at = db.Column(db.DateTime)
    car_voted_for = db.Column(db.Integer, db.ForeignKey('car.id'))
    qr_code = db.Column(db.String(10000), nullable=True)

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    voting_start = db.Column(db.DateTime, nullable=True)
    voting_end = db.Column(db.DateTime, nullable=True)

    @staticmethod
    def get_settings():
        settings = Settings.query.first()
        if not settings:
            settings = Settings()
            db.session.add(settings)
            db.session.commit()
        return settings

def generate_vote_code():
    while True:
        code = ''.join(random.choices(string.digits, k=5))
        if not VoteCode.query.filter_by(code=code).first():
            return code

def safe_generate_password_hash(password):
    """Generate password hash using a method available in Python 3.8"""
    return generate_password_hash(password, method='pbkdf2:sha256:260000')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    cars = Car.query.all()
    settings = Settings.get_settings()
    now = datetime.utcnow()
    
    voting_status = "not_started"
    if settings.voting_start and settings.voting_end:
        if now < settings.voting_start:
            voting_status = "not_started"
        elif now > settings.voting_end:
            voting_status = "ended"
        else:
            voting_status = "active"
    
    return render_template('index.html', 
                         cars=cars,
                         voting_status=voting_status,
                         voting_start=settings.voting_start,
                         voting_end=settings.voting_end)

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if request.method == 'POST':
        if 'car_name' in request.form:
            # Handle car upload
            car_name = request.form['car_name']
            car_number = request.form['car_number']
            photo = request.files['photo']
            
            if photo:
                filename = secure_filename(photo.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                
                car = Car(
                    number=car_number,
                    owner_name=car_name,
                    image_path=os.path.join('uploads', unique_filename)
                )
                db.session.add(car)
                db.session.commit()
                flash('Car added successfully!')
        
        elif 'voting_start' in request.form:
            # Handle voting period settings
            try:
                start_str = request.form['voting_start']
                end_str = request.form['voting_end']
                
                settings = Settings.get_settings()
                settings.voting_start = datetime.fromisoformat(start_str) if start_str else None
                settings.voting_end = datetime.fromisoformat(end_str) if end_str else None
                db.session.commit()
                flash('Voting period updated successfully!')
            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DDTHH:MM format.')
    
    cars = Car.query.all()
    settings = Settings.get_settings()
    return render_template('admin.html', 
                         cars=cars,
                         voting_start=settings.voting_start,
                         voting_end=settings.voting_end)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('admin'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/upload', methods=['POST'])
@login_required
def upload_car():
    if 'image' not in request.files:
        flash('No image file')
        return redirect(url_for('admin'))
    
    file = request.files['image']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('admin'))
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        car = Car(
            number=request.form.get('number'),
            owner_name=request.form.get('owner_name'),
            image_path=os.path.join('uploads', filename)
        )
        db.session.add(car)
        db.session.commit()
        
        flash('Car added successfully')
    return redirect(url_for('admin'))

@app.route('/admin/generate_codes', methods=['POST'])
@login_required
def generate_codes():
    try:
        count = int(request.form.get('code_count', 1))
        if count < 1 or count > 1000:
            flash('Please enter a number between 1 and 1000')
            return redirect(url_for('admin'))
        
        new_codes = []
        for _ in range(count):
            code = VoteCode(code=generate_vote_code())
            db.session.add(code)
            new_codes.append(code)
        
        db.session.commit()
        flash(f'Successfully generated {count} new voting codes')
    except Exception as e:
        db.session.rollback()
        flash('Error generating codes: ' + str(e))
    
    return redirect(url_for('admin'))

@app.route('/admin/print_codes')
@login_required
def print_codes():
    # Get the base URL for QR codes
    if request.headers.get('X-Forwarded-Proto') and request.headers.get('X-Forwarded-Host'):
        base_url = f"{request.headers.get('X-Forwarded-Proto')}://{request.headers.get('X-Forwarded-Host')}"
    else:
        base_url = request.host_url.rstrip('/')
    
    # Get codes and generate QR codes
    unused_codes = VoteCode.query.filter_by(is_used=False).order_by(VoteCode.created_at.desc()).all()
    used_codes = VoteCode.query.filter_by(is_used=True).order_by(VoteCode.used_at.desc()).all()
    
    # Generate QR codes for unused codes
    for code in unused_codes:
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(f"{base_url}/?code={code.code}")
        qr.make(fit=True)

        # Create QR code image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 for embedding in HTML
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        code.qr_code = base64.b64encode(buffered.getvalue()).decode()
    
    return render_template('print_codes.html', unused_codes=unused_codes, used_codes=used_codes)

@app.route('/vote', methods=['POST'])
def vote():
    settings = Settings.get_settings()
    now = datetime.utcnow()
    
    if not settings.voting_start or not settings.voting_end:
        return jsonify({'error': 'Voting period has not been set'}), 400
    if now < settings.voting_start:
        return jsonify({'error': 'Voting has not started yet'}), 400
    if now > settings.voting_end:
        return jsonify({'error': 'Voting has ended'}), 400
        
    code = request.form.get('code')
    car_id = request.form.get('car_id')
    
    if not code or not car_id:
        return jsonify({'error': 'Missing code or car_id'}), 400
        
    vote_code = VoteCode.query.filter_by(code=code).first()
    if not vote_code:
        return jsonify({'error': 'Invalid code'}), 400
    if vote_code.is_used:
        return jsonify({'error': 'Code already used'}), 400
        
    car = Car.query.get(car_id)
    if not car:
        return jsonify({'error': 'Invalid car'}), 400
        
    vote_code.is_used = True
    vote_code.car_voted_for = car_id
    car.votes += 1
    db.session.commit()
    
    return jsonify({'message': 'Vote recorded successfully'})

@app.route('/results')
def results():
    cars = Car.query.order_by(Car.votes.desc()).all()
    return render_template('results.html', cars=cars)

@app.route('/admin/reset_votes', methods=['POST'])
@login_required
def reset_votes():
    try:
        # Reset all car votes to 0
        Car.query.update({Car.votes: 0})
        # Delete all vote codes
        VoteCode.query.delete()
        db.session.commit()
        flash('All votes and voting codes have been reset successfully')
    except Exception as e:
        db.session.rollback()
        flash('Error resetting votes: ' + str(e))
    return redirect(url_for('admin'))

@app.route('/health')
def health_check():
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        app.logger.error(f"Health check failed: {str(e)}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

# Initialize database
with app.app_context():
    try:
        db.create_all()
        # Create admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password_hash=safe_generate_password_hash('admin123')
            )
            db.session.add(admin)
            db.session.commit()
            
        # Create settings if not exists
        Settings.get_settings()
    except Exception as e:
        app.logger.error(f"Database initialization error: {str(e)}")
        raise

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

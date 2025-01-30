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

def generate_vote_code():
    while True:
        code = ''.join(random.choices(string.digits, k=5))
        if not VoteCode.query.filter_by(code=code).first():
            return code

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    cars = Car.query.all()
    return render_template('index.html', cars=cars)

@app.route('/admin')
@login_required
def admin():
    cars = Car.query.all()
    return render_template('admin.html', cars=cars)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('admin'))
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
    unused_codes = VoteCode.query.filter_by(is_used=False).order_by(VoteCode.created_at.desc()).all()
    used_codes = VoteCode.query.filter_by(is_used=True).order_by(VoteCode.used_at.desc()).all()
    return render_template('print_codes.html', unused_codes=unused_codes, used_codes=used_codes)

@app.route('/vote/<int:car_id>', methods=['POST'])
def vote(car_id):
    vote_code = request.form.get('vote_code')
    if not vote_code:
        return jsonify({'error': 'Vote code is required'}), 400
    
    code_record = VoteCode.query.filter_by(code=vote_code, is_used=False).first()
    if not code_record:
        return jsonify({'error': 'Invalid or already used vote code'}), 400
    
    car = Car.query.get_or_404(car_id)
    car.votes += 1
    
    code_record.is_used = True
    code_record.used_at = datetime.utcnow()
    code_record.car_voted_for = car_id
    
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
            admin = User(username='admin', password_hash=generate_password_hash('admin123'))
            db.session.add(admin)
            db.session.commit()
    except Exception as e:
        app.logger.error(f"Database initialization error: {str(e)}")
        raise

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

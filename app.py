import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import random
import string
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///derby.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123')
            )
            db.session.add(admin)
            db.session.commit()
            
        # Add sample cars if none exist
        if Car.query.count() == 0:
            sample_cars = [
                Car(number=1, owner_name="John Smith", image_path="uploads/car1.svg", votes=3),
                Car(number=2, owner_name="Jane Doe", image_path="uploads/car2.svg", votes=5),
                Car(number=3, owner_name="Mike Johnson", image_path="uploads/car3.svg", votes=4)
            ]
            for car in sample_cars:
                db.session.add(car)
            db.session.commit()
            
    app.run(debug=True, port=5001)

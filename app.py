import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Admin, Doctor, Patient, Department, Appointment, Treatment, DoctorAvailability
from config import Config
from datetime import datetime, timedelta, date, time
from functools import wraps


app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    user_type = session.get('user_type')
    if user_type == 'admin':
        return Admin.query.get(int(user_id))
    elif user_type == 'doctor':
        return Doctor.query.get(int(user_id))
    elif user_type == 'patient':
        return Patient.query.get(int(user_id))
    return None

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if session.get('user_type') != role:
                flash('Unauthorized access', 'danger')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def change_user_password(user_id, new_password):

    user = Patient.query.get(user_id) or Doctor.query.get(user_id)

    if user:
        user.set_password(new_password)
        db.session.commit()
        return True
    return False


def init_database():
    with app.app_context():
        db.create_all()
        
        if not Admin.query.filter_by(username='admin').first():
            admin = Admin(username='admin', email='admin@hospital.com')
            admin.set_password('admin123')
            db.session.add(admin)
        
        departments_data = [
            ('Cardiology', 'Heart and cardiovascular system'),
            ('Neurology', 'Brain and nervous system'),
            ('Orthopedics', 'Bones and muscles'),
            ('Pediatrics', 'Children health'),
            ('Dermatology', 'Skin disorders'),
            ('ENT', 'Ear, Nose, and Throat'),
            ('General Medicine', 'General health issues')
        ]
        
        for dept_name, dept_desc in departments_data:
            if not Department.query.filter_by(name=dept_name).first():
                dept = Department(name=dept_name, description=dept_desc)
                db.session.add(dept)
        
        db.session.commit()

@app.route('/')
def index():
    if current_user.is_authenticated:
        user_type = session.get('user_type')
        if user_type == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif user_type == 'doctor':
            return redirect(url_for('doctor_dashboard'))
        elif user_type == 'patient':
            return redirect(url_for('patient_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_type = request.form.get('user_type')
        
        user = None
        if user_type == 'admin':
            user = Admin.query.filter_by(username=username).first()
        elif user_type == 'doctor':
            user = Doctor.query.filter_by(username=username).first()
        elif user_type == 'patient':
            user = Patient.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if hasattr(user, 'is_active') and not user.is_active:
                flash('Your account has been deactivated', 'danger')
                return redirect(url_for('login'))
            
            login_user(user)
            session['user_type'] = user_type
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('user_type', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        dob = request.form.get('date_of_birth')
        gender = request.form.get('gender')
        address = request.form.get('address')
        blood_group = request.form.get('blood_group')
        
        if Patient.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        
        if Patient.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
        
        patient = Patient(
            username=username,
            name=name,
            email=email,
            phone=phone,
            date_of_birth=datetime.strptime(dob, '%Y-%m-%d').date() if dob else None,
            gender=gender,
            address=address,
            blood_group=blood_group
        )
        patient.set_password(password)
        
        db.session.add(patient)
        db.session.commit()
        
        flash('Registration successful! Please login', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

# ADMIN ROUTES
@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    total_doctors = Doctor.query.filter_by(is_active=True).count()
    total_patients = Patient.query.filter_by(is_active=True).count()
    total_appointments = Appointment.query.count()
    pending_appointments = Appointment.query.filter_by(status='Booked').count()
    
    recent_appointments = Appointment.query.order_by(Appointment.created_at.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         total_doctors=total_doctors,
                         total_patients=total_patients,
                         total_appointments=total_appointments,
                         pending_appointments=pending_appointments,
                         recent_appointments=recent_appointments)

@app.route('/admin/doctors')
@login_required
@role_required('admin')
def admin_doctors():
    search = request.args.get('search', '')
    if search:
        doctors = Doctor.query.filter(
            (Doctor.name.contains(search)) | 
            (Doctor.email.contains(search))
        ).all()
    else:
        doctors = Doctor.query.all()
    
    departments = Department.query.all()
    return render_template('admin/doctors.html', doctors=doctors, departments=departments)

@app.route('/admin/doctor/add', methods=['POST'])
@login_required
@role_required('admin')
def admin_add_doctor():
    username = request.form.get('username')
    password = request.form.get('password')
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    department_id = request.form.get('department_id')
    experience_years = request.form.get('experience_years')
    qualification = request.form.get('qualification')
    
    if Doctor.query.filter_by(username=username).first():
        flash('Username already exists', 'danger')
        return redirect(url_for('admin_doctors'))
    
    doctor = Doctor(
        username=username,
        name=name,
        email=email,
        phone=phone,
        department_id=department_id,
        experience_years=experience_years,
        qualification=qualification
    )
    doctor.set_password(password)
    
    db.session.add(doctor)
    db.session.commit()
    
    flash('Doctor added successfully', 'success')
    return redirect(url_for('admin_doctors'))

@app.route('/admin/doctor/edit/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def admin_edit_doctor(id):
    doctor = Doctor.query.get_or_404(id)
    
    doctor.name = request.form.get('name')
    doctor.email = request.form.get('email')
    doctor.phone = request.form.get('phone')
    doctor.department_id = request.form.get('department_id')
    doctor.experience_years = request.form.get('experience_years')
    doctor.qualification = request.form.get('qualification')
    
    password = request.form.get('password')
    if password:
        doctor.set_password(password)
    
    db.session.commit()
    flash('Doctor updated successfully', 'success')
    return redirect(url_for('admin_doctors'))

@app.route('/admin/doctor/delete/<int:id>')
@login_required
@role_required('admin')
def admin_delete_doctor(id):
    doctor = Doctor.query.get_or_404(id)
    doctor.is_active = False
    db.session.commit()
    flash('Doctor deactivated successfully', 'success')
    return redirect(url_for('admin_doctors'))

@app.route('/admin/patients')
@login_required
@role_required('admin')
def admin_patients():
    search = request.args.get('search', '')
    if search:
        patients = Patient.query.filter(
            (Patient.name.contains(search)) | 
            (Patient.email.contains(search)) |
            (Patient.phone.contains(search))
        ).all()
    else:
        patients = Patient.query.all()
    
    return render_template('admin/patients.html', patients=patients)

@app.route('/admin/patient/edit/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def admin_edit_patient(id):
    patient = Patient.query.get_or_404(id)
    
    patient.name = request.form.get('name')
    patient.email = request.form.get('email')
    patient.phone = request.form.get('phone')
    patient.address = request.form.get('address')
    
    db.session.commit()
    flash('Patient updated successfully', 'success')
    return redirect(url_for('admin_patients'))

@app.route('/admin/patient/delete/<int:id>')
@login_required
@role_required('admin')
def admin_delete_patient(id):
    patient = Patient.query.get_or_404(id)
    patient.is_active = False
    db.session.commit()
    flash('Patient deactivated successfully', 'success')
    return redirect(url_for('admin_patients'))

@app.route('/admin/appointments')
@login_required
@role_required('admin')
def admin_appointments():
    appointments = Appointment.query.order_by(Appointment.appointment_date.desc()).all()
    return render_template('admin/appointments.html', appointments=appointments)

@app.route('/admin/appointment/cancel/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def admin_cancel_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    appointment.status = 'Cancelled'
    appointment.cancel_reason = request.form.get('cancel_reason')
    db.session.commit()
    flash('Appointment cancelled successfully', 'success')
    return redirect(url_for('admin_appointments'))
@app.route('/admin/change_password', methods=['POST'])
@login_required
@role_required('admin')
def admin_change_password():

    user_id = int(request.form.get("user_id"))
    new_password = request.form.get("password")

    success = change_user_password(user_id, new_password)

    if success:
        flash("Password updated successfully", "success")
    else:
        flash("User not found", "danger")

    return redirect(url_for('admin_dashboard'))

# DOCTOR ROUTES
@app.route('/doctor/dashboard')
@login_required
@role_required('doctor')
def doctor_dashboard():
    today = date.today()
    week_later = today + timedelta(days=7)
    
    upcoming_appointments = Appointment.query.filter(
        Appointment.doctor_id == current_user.id,
        Appointment.appointment_date >= today,
        Appointment.appointment_date <= week_later,
        Appointment.status == 'Booked'
    ).order_by(Appointment.appointment_date).all()
    
    total_patients = db.session.query(Appointment.patient_id).filter(
        Appointment.doctor_id == current_user.id
    ).distinct().count()
    
    completed_today = Appointment.query.filter(
        Appointment.doctor_id == current_user.id,
        Appointment.appointment_date == today,
        Appointment.status == 'Completed'
    ).count()
    
    return render_template('doctor/dashboard.html',
                         upcoming_appointments=upcoming_appointments,
                         total_patients=total_patients,
                         completed_today=completed_today)

@app.route('/doctor/appointments')
@login_required
@role_required('doctor')
def doctor_appointments():
    appointments = Appointment.query.filter_by(doctor_id=current_user.id).order_by(Appointment.appointment_date.desc()).all()
    return render_template('doctor/appointments.html', appointments=appointments)

@app.route('/doctor/appointment/complete/<int:id>', methods=['POST'])
@login_required
@role_required('doctor')
def doctor_complete_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    
    if appointment.doctor_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('doctor_appointments'))
    
    appointment.status = 'Completed'
    
    diagnosis = request.form.get('diagnosis')
    prescription = request.form.get('prescription')
    notes = request.form.get('notes')
    
    treatment = Treatment(
        appointment_id=appointment.id,
        diagnosis=diagnosis,
        prescription=prescription,
        notes=notes
    )
    
    db.session.add(treatment)
    db.session.commit()
    
    flash('Appointment completed successfully', 'success')
    return redirect(url_for('doctor_appointments'))

@app.route('/doctor/appointment/cancel/<int:id>', methods=['POST'])
@login_required
@role_required('doctor')
def doctor_cancel_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    
    if appointment.doctor_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('doctor_appointments'))
    
    appointment.status = 'Cancelled'
    appointment.cancel_reason = request.form.get('cancel_reason')
    db.session.commit()
    
    flash('Appointment cancelled successfully', 'success')
    return redirect(url_for('doctor_appointments'))

@app.route('/doctor/availability', methods=['GET', 'POST'])
@login_required
@role_required('doctor')
def doctor_availability():
    if request.method == 'POST':
        date_str = request.form.get('date')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        
        availability = DoctorAvailability(
            doctor_id=current_user.id,
            date=datetime.strptime(date_str, '%Y-%m-%d').date(),
            start_time=datetime.strptime(start_time_str, '%H:%M').time(),
            end_time=datetime.strptime(end_time_str, '%H:%M').time()
        )
        
        db.session.add(availability)
        db.session.commit()
        
        flash('Availability added successfully', 'success')
        return redirect(url_for('doctor_availability'))
    
    availabilities = DoctorAvailability.query.filter_by(doctor_id=current_user.id).order_by(DoctorAvailability.date.desc()).all()
    return render_template('doctor/availability.html', availabilities=availabilities)

@app.route('/doctor/patients')
@login_required
@role_required('doctor')
def doctor_patients():
    patients = db.session.query(Patient).join(Appointment).filter(
        Appointment.doctor_id == current_user.id
    ).distinct().all()
    
    return render_template('doctor/patients.html', patients=patients)

@app.route('/doctor/patient/history/<int:id>')
@login_required
@role_required('doctor')
def doctor_patient_history(id):
    patient = Patient.query.get_or_404(id)
    appointments = Appointment.query.filter_by(
        patient_id=id,
        doctor_id=current_user.id,
        status='Completed'
    ).order_by(Appointment.appointment_date.desc()).all()
    
    return render_template('doctor/patient_history.html', patient=patient, appointments=appointments)

# PATIENT ROUTES
@app.route('/patient/dashboard')
@login_required
@role_required('patient')
def patient_dashboard():
    departments = Department.query.all()
    
    today = date.today()
    upcoming_appointments = Appointment.query.filter(
        Appointment.patient_id == current_user.id,
        Appointment.appointment_date >= today,
        Appointment.status == 'Booked'
    ).order_by(Appointment.appointment_date).all()
    
    return render_template('patient/dashboard.html',
                         departments=departments,
                         upcoming_appointments=upcoming_appointments)

@app.route('/patient/doctors')
@login_required
@role_required('patient')
def patient_doctors():
    search = request.args.get('search', '')
    department_id = request.args.get('department_id', '')
    
    query = Doctor.query.filter_by(is_active=True)
    
    if search:
        query = query.filter(Doctor.name.contains(search))
    
    if department_id:
        query = query.filter_by(department_id=department_id)
    
    doctors = query.all()
    departments = Department.query.all()
    
    today = date.today()
    week_later = today + timedelta(days=7)
    
    return render_template('patient/doctors.html',
                         doctors=doctors,
                         departments=departments,
                         today=today,
                         week_later=week_later)

@app.route('/patient/book/<int:doctor_id>', methods=['POST'])
@login_required
@role_required('patient')
def patient_book_appointment(doctor_id):
    appointment_date = request.form.get('appointment_date')
    appointment_time = request.form.get('appointment_time')
    reason = request.form.get('reason')
    
    existing = Appointment.query.filter_by(
        doctor_id=doctor_id,
        appointment_date=datetime.strptime(appointment_date, '%Y-%m-%d').date(),
        appointment_time=datetime.strptime(appointment_time, '%H:%M').time(),
        status='Booked'
    ).first()
    
    if existing:
        flash('This time slot is already booked', 'danger')
        return redirect(url_for('patient_doctors'))
    
    appointment = Appointment(
        patient_id=current_user.id,
        doctor_id=doctor_id,
        appointment_date=datetime.strptime(appointment_date, '%Y-%m-%d').date(),
        appointment_time=datetime.strptime(appointment_time, '%H:%M').time(),
        reason=reason
    )
    
    db.session.add(appointment)
    db.session.commit()
    
    flash('Appointment booked successfully', 'success')
    return redirect(url_for('patient_appointments'))

@app.route('/patient/appointments')
@login_required
@role_required('patient')
def patient_appointments():
    appointments = Appointment.query.filter_by(patient_id=current_user.id).order_by(Appointment.appointment_date.desc()).all()
    return render_template('patient/appointments.html', appointments=appointments)

@app.route('/patient/appointment/cancel/<int:id>', methods=['POST'])
@login_required
@role_required('patient')
def patient_cancel_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    
    if appointment.patient_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('patient_appointments'))
    
    appointment.status = 'Cancelled'
    appointment.cancel_reason = request.form.get('cancel_reason')
    db.session.commit()
    
    flash('Appointment cancelled successfully', 'success')
    return redirect(url_for('patient_appointments'))

@app.route('/patient/history')
@login_required
@role_required('patient')
def patient_history():
    appointments = Appointment.query.filter_by(
        patient_id=current_user.id,
        status='Completed'
    ).order_by(Appointment.appointment_date.desc()).all()
    
    return render_template('patient/history.html', appointments=appointments)

@app.route('/patient/profile', methods=['GET', 'POST'])
@login_required
@role_required('patient')
def patient_profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name')
        current_user.email = request.form.get('email')
        current_user.phone = request.form.get('phone')
        current_user.address = request.form.get('address')
        current_user.blood_group = request.form.get('blood_group')
        
        password = request.form.get('password')
        if password:
            current_user.set_password(password)
        
        db.session.commit()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('patient_profile'))
    
    return render_template('patient/profile.html')

if __name__ == '__main__':
    init_database()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
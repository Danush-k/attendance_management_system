import os
import logging
from datetime import timedelta
from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string
from datetime import datetime, timedelta

# Create Base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
mail = Mail()

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Configure login manager
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

# Configure mail
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')
mail.init_app(app)

# Initialize database
db.init_app(app)

# Import models and initialize them within app context
with app.app_context():
    from models import User, Student, Faculty, Course, Router, Attendance, LeaveRequest, AttendanceOTP, Session
    db.create_all()

# Import forms
from forms import LoginForm, StudentRegistrationForm, FacultyRegistrationForm, CourseForm, RouterForm, OTPForm, LeaveRequestForm, SessionForm, MarkAttendanceForm, PasswordResetForm, PasswordResetRequestForm

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'student':
            return redirect(url_for('student_dashboard'))
        elif current_user.role == 'faculty':
            return redirect(url_for('faculty_dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if user.role == 'student':
                return redirect(next_page or url_for('student_dashboard'))
            elif user.role == 'faculty':
                return redirect(next_page or url_for('faculty_dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

# Student routes
@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        flash('Access denied: You must be a student to view this page', 'danger')
        return redirect(url_for('index'))
    
    student = Student.query.filter_by(user_id=current_user.id).first()
    courses = student.courses
    
    # Get attendance statistics
    attendance_stats = {}
    for course in courses:
        total_sessions = Session.query.filter_by(course_id=course.id).count()
        if total_sessions > 0:
            attended = Attendance.query.filter_by(
                student_id=student.id, 
                status='present'
            ).join(Session).filter(Session.course_id == course.id).count()
            
            percentage = (attended / total_sessions) * 100
            attendance_stats[course.course_code] = {
                'total': total_sessions,
                'attended': attended,
                'percentage': round(percentage, 2)
            }
        else:
            attendance_stats[course.course_code] = {
                'total': 0,
                'attended': 0,
                'percentage': 0
            }
    
    # Get recent attendance
    recent_attendance = (Attendance.query
                         .filter_by(student_id=student.id)
                         .join(Session)
                         .order_by(Session.date.desc())
                         .limit(5)
                         .all())
    
    # Get pending leave requests
    pending_leaves = LeaveRequest.query.filter_by(
        student_id=student.id, 
        status='pending'
    ).all()
    
    return render_template('student/dashboard.html', 
                          student=student, 
                          courses=courses, 
                          attendance_stats=attendance_stats,
                          recent_attendance=recent_attendance,
                          pending_leaves=pending_leaves)

@app.route('/student/profile', methods=['GET', 'POST'])
@login_required
def student_profile():
    if current_user.role != 'student':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    student = Student.query.filter_by(user_id=current_user.id).first()
    form = StudentRegistrationForm(obj=student)
    
    if form.validate_on_submit():
        student.department = form.department.data
        student.year = form.year.data
        student.phone = form.phone.data
        db.session.commit()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('student_profile'))
    
    return render_template('student/profile.html', student=student, form=form)

@app.route('/student/attendance')
@login_required
def student_attendance():
    if current_user.role != 'student':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    student = Student.query.filter_by(user_id=current_user.id).first()
    courses = student.courses
    
    course_id = request.args.get('course_id', type=int)
    if course_id:
        selected_course = Course.query.get_or_404(course_id)
        if selected_course not in courses:
            flash('You are not enrolled in this course', 'danger')
            return redirect(url_for('student_attendance'))
        
        sessions = Session.query.filter_by(course_id=course_id).order_by(Session.date.desc()).all()
        attendance_records = {}
        
        for session in sessions:
            attendance = Attendance.query.filter_by(
                student_id=student.id,
                session_id=session.id
            ).first()
            
            attendance_records[session.id] = attendance
    else:
        selected_course = None
        sessions = []
        attendance_records = {}
    
    return render_template('student/attendance.html', 
                          student=student, 
                          courses=courses,
                          selected_course=selected_course,
                          sessions=sessions,
                          attendance_records=attendance_records)

@app.route('/student/mark_attendance', methods=['GET', 'POST'])
@login_required
def mark_attendance():
    if current_user.role != 'student':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    student = Student.query.filter_by(user_id=current_user.id).first()
    form = MarkAttendanceForm()
    
    # Get the student's courses and active OTP sessions
    courses = student.courses
    active_sessions = []
    
    # Find all active OTP sessions for courses the student is enrolled in
    for course in courses:
        active_otps = AttendanceOTP.query.filter_by(
            course_id=course.id, 
            is_active=True
        ).all()
        
        for otp in active_otps:
            # Check if attendance is not already marked
            session = Session.query.get(otp.session_id)
            existing_attendance = Attendance.query.filter_by(
                student_id=student.id,
                session_id=session.id
            ).first()
            
            if not existing_attendance:
                active_sessions.append({
                    'course': course,
                    'session': session,
                    'otp': otp
                })
    
    if form.validate_on_submit():
        otp_value = form.otp.data
        router_id = form.router_id.data
        
        # Verify OTP and router ID
        otp_obj = AttendanceOTP.query.filter_by(
            otp=otp_value,
            is_active=True
        ).first()
        
        if not otp_obj:
            flash('Invalid or expired OTP', 'danger')
            return redirect(url_for('mark_attendance'))
        
        # Get the course and its associated router
        course = Course.query.get(otp_obj.course_id)
        if course.router_id != int(router_id):
            flash('You are not in the correct location for this class', 'danger')
            return redirect(url_for('mark_attendance'))
        
        # Mark attendance
        attendance = Attendance(
            student_id=student.id,
            session_id=otp_obj.session_id,
            status='present',
            marked_at=datetime.now()
        )
        db.session.add(attendance)
        db.session.commit()
        
        flash('Attendance marked successfully', 'success')
        return redirect(url_for('student_dashboard'))
    
    return render_template('student/mark_attendance.html', 
                          form=form, 
                          active_sessions=active_sessions)

@app.route('/student/leave_request', methods=['GET', 'POST'])
@login_required
def leave_request():
    if current_user.role != 'student':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    student = Student.query.filter_by(user_id=current_user.id).first()
    form = LeaveRequestForm()
    
    # Populate course choices
    form.course_id.choices = [(c.id, f"{c.course_code} - {c.title}") for c in student.courses]
    
    if form.validate_on_submit():
        leave_request = LeaveRequest(
            student_id=student.id,
            course_id=form.course_id.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            reason=form.reason.data,
            status='pending'
        )
        db.session.add(leave_request)
        db.session.commit()
        flash('Leave request submitted successfully', 'success')
        return redirect(url_for('student_dashboard'))
    
    # Display existing leave requests
    leave_requests = LeaveRequest.query.filter_by(student_id=student.id).order_by(LeaveRequest.created_at.desc()).all()
    
    return render_template('student/leave_request.html', 
                          form=form, 
                          student=student,
                          leave_requests=leave_requests)

# Faculty routes
@app.route('/faculty/dashboard')
@login_required
def faculty_dashboard():
    if current_user.role != 'faculty':
        flash('Access denied: You must be a faculty member to view this page', 'danger')
        return redirect(url_for('index'))
    
    faculty = Faculty.query.filter_by(user_id=current_user.id).first()
    courses = Course.query.filter_by(faculty_id=faculty.id).all()
    
    # Get recent sessions
    recent_sessions = (Session.query
                       .filter(Session.course_id.in_([c.id for c in courses]))
                       .order_by(Session.date.desc())
                       .limit(5)
                       .all())
    
    # Get pending leave requests
    pending_leaves = (LeaveRequest.query
                     .filter(LeaveRequest.course_id.in_([c.id for c in courses]))
                     .filter_by(status='pending')
                     .order_by(LeaveRequest.created_at.desc())
                     .all())
    
    # Get attendance statistics for each course
    course_stats = {}
    for course in courses:
        total_students = len(course.students)
        if total_students > 0:
            sessions = Session.query.filter_by(course_id=course.id).all()
            attendance_rate = 0
            
            if sessions:
                attendance_count = 0
                total_possible = len(sessions) * total_students
                
                for session in sessions:
                    attendance_count += Attendance.query.filter_by(
                        session_id=session.id,
                        status='present'
                    ).count()
                
                if total_possible > 0:
                    attendance_rate = (attendance_count / total_possible) * 100
            
            course_stats[course.id] = {
                'student_count': total_students,
                'attendance_rate': round(attendance_rate, 2)
            }
    
    return render_template('faculty/dashboard.html', 
                          faculty=faculty, 
                          courses=courses,
                          recent_sessions=recent_sessions,
                          pending_leaves=pending_leaves,
                          course_stats=course_stats)

@app.route('/faculty/manage_courses', methods=['GET', 'POST'])
@login_required
def manage_courses():
    if current_user.role != 'faculty':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    faculty = Faculty.query.filter_by(user_id=current_user.id).first()
    form = CourseForm()
    
    # Populate router choices
    routers = Router.query.all()
    form.router_id.choices = [(r.id, f"{r.location} - {r.name}") for r in routers]
    
    if form.validate_on_submit():
        course = Course(
            course_code=form.course_code.data,
            title=form.title.data,
            faculty_id=faculty.id,
            schedule=form.schedule.data,
            classroom=form.classroom.data,
            router_id=form.router_id.data
        )
        db.session.add(course)
        db.session.commit()
        flash('Course added successfully', 'success')
        return redirect(url_for('manage_courses'))
    
    # Get existing courses
    courses = Course.query.filter_by(faculty_id=faculty.id).all()
    
    return render_template('faculty/manage_courses.html', 
                          form=form, 
                          faculty=faculty,
                          courses=courses,
                          routers=routers)

@app.route('/faculty/course/<int:course_id>', methods=['GET', 'POST'])
@login_required
def course_detail(course_id):
    if current_user.role != 'faculty':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    faculty = Faculty.query.filter_by(user_id=current_user.id).first()
    course = Course.query.get_or_404(course_id)
    
    # Verify course belongs to faculty
    if course.faculty_id != faculty.id:
        flash('Access denied: This course does not belong to you', 'danger')
        return redirect(url_for('manage_courses'))
    
    # Create session form
    session_form = SessionForm()
    
    if session_form.validate_on_submit():
        # Create new session
        session = Session(
            course_id=course.id,
            date=session_form.date.data,
            start_time=session_form.start_time.data,
            end_time=session_form.end_time.data,
            topic=session_form.topic.data
        )
        db.session.add(session)
        db.session.commit()
        flash('Session added successfully', 'success')
        return redirect(url_for('course_detail', course_id=course.id))
    
    # Get sessions and students
    sessions = Session.query.filter_by(course_id=course.id).order_by(Session.date.desc()).all()
    students = course.students
    
    # Get attendance data for course
    attendance_data = {}
    for student in students:
        attendance_data[student.id] = {
            'present': 0,
            'absent': 0,
            'total': len(sessions),
            'percentage': 0
        }
        
        for session in sessions:
            attendance = Attendance.query.filter_by(
                student_id=student.id,
                session_id=session.id
            ).first()
            
            if attendance and attendance.status == 'present':
                attendance_data[student.id]['present'] += 1
        
        if attendance_data[student.id]['total'] > 0:
            attendance_data[student.id]['percentage'] = round(
                (attendance_data[student.id]['present'] / attendance_data[student.id]['total']) * 100, 2
            )
            attendance_data[student.id]['absent'] = attendance_data[student.id]['total'] - attendance_data[student.id]['present']
    
    return render_template('faculty/course_detail.html',
                          course=course,
                          faculty=faculty,
                          session_form=session_form,
                          sessions=sessions,
                          students=students,
                          attendance_data=attendance_data)

@app.route('/faculty/generate_otp/<int:session_id>', methods=['GET', 'POST'])
@login_required
def generate_otp(session_id):
    if current_user.role != 'faculty':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    faculty = Faculty.query.filter_by(user_id=current_user.id).first()
    session_obj = Session.query.get_or_404(session_id)
    course = Course.query.get(session_obj.course_id)
    
    # Verify course belongs to faculty
    if course.faculty_id != faculty.id:
        flash('Access denied: This session does not belong to your course', 'danger')
        return redirect(url_for('faculty_dashboard'))
    
    form = OTPForm()
    form.router_id.data = course.router_id
    
    if form.validate_on_submit():
        router_id = form.router_id.data
        
        # Verify faculty is in the correct location
        if int(router_id) != course.router_id:
            flash('Error: You are not in the correct location for this class', 'danger')
            return redirect(url_for('generate_otp', session_id=session_id))
        
        # Deactivate any existing OTPs for this session
        existing_otps = AttendanceOTP.query.filter_by(session_id=session_id).all()
        for otp in existing_otps:
            otp.is_active = False
        
        # Generate new OTP (6-digit alphanumeric)
        otp_value = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        # Store OTP with 15-minute expiration
        expiration = datetime.now() + timedelta(minutes=15)
        otp = AttendanceOTP(
            session_id=session_id,
            course_id=course.id,
            otp=otp_value,
            is_active=True,
            expiration=expiration
        )
        db.session.add(otp)
        db.session.commit()
        
        flash(f'OTP generated successfully: {otp_value}', 'success')
        return redirect(url_for('course_detail', course_id=course.id))
    
    return render_template('faculty/generate_otp.html',
                          form=form,
                          session=session_obj,
                          course=course)

@app.route('/faculty/attendance_report')
@login_required
def attendance_report():
    if current_user.role != 'faculty':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    faculty = Faculty.query.filter_by(user_id=current_user.id).first()
    courses = Course.query.filter_by(faculty_id=faculty.id).all()
    
    course_id = request.args.get('course_id', type=int)
    if course_id:
        selected_course = Course.query.get_or_404(course_id)
        if selected_course.faculty_id != faculty.id:
            flash('Access denied: This course does not belong to you', 'danger')
            return redirect(url_for('attendance_report'))
        
        students = selected_course.students
        sessions = Session.query.filter_by(course_id=course_id).order_by(Session.date).all()
        
        # Generate attendance data
        attendance_data = {}
        for student in students:
            attendance_data[student.id] = {
                'name': f"{student.user.first_name} {student.user.last_name}",
                'id': student.student_id,
                'sessions': {},
                'total_present': 0,
                'percentage': 0
            }
            
            for session in sessions:
                attendance = Attendance.query.filter_by(
                    student_id=student.id,
                    session_id=session.id
                ).first()
                
                if attendance and attendance.status == 'present':
                    attendance_data[student.id]['sessions'][session.id] = 'present'
                    attendance_data[student.id]['total_present'] += 1
                else:
                    attendance_data[student.id]['sessions'][session.id] = 'absent'
            
            if sessions:
                attendance_data[student.id]['percentage'] = round(
                    (attendance_data[student.id]['total_present'] / len(sessions)) * 100, 2
                )
    else:
        selected_course = None
        students = []
        sessions = []
        attendance_data = {}
    
    return render_template('faculty/attendance_report.html',
                          faculty=faculty,
                          courses=courses,
                          selected_course=selected_course,
                          students=students,
                          sessions=sessions,
                          attendance_data=attendance_data)

@app.route('/faculty/leave_requests')
@login_required
def leave_requests():
    if current_user.role != 'faculty':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    faculty = Faculty.query.filter_by(user_id=current_user.id).first()
    course_ids = [course.id for course in Course.query.filter_by(faculty_id=faculty.id).all()]
    
    # Get all leave requests for faculty's courses
    leave_requests = LeaveRequest.query.filter(
        LeaveRequest.course_id.in_(course_ids)
    ).order_by(LeaveRequest.created_at.desc()).all()
    
    return render_template('faculty/leave_requests.html',
                          faculty=faculty,
                          leave_requests=leave_requests)

@app.route('/faculty/leave_request/<int:request_id>/<string:action>', methods=['POST'])
@login_required
def process_leave_request(request_id, action):
    if current_user.role != 'faculty':
        return jsonify({'success': False, 'message': 'Access denied'})
    
    faculty = Faculty.query.filter_by(user_id=current_user.id).first()
    leave_request = LeaveRequest.query.get_or_404(request_id)
    
    # Verify course belongs to faculty
    course = Course.query.get(leave_request.course_id)
    if course.faculty_id != faculty.id:
        return jsonify({'success': False, 'message': 'Access denied: This request is not for your course'})
    
    if action == 'approve':
        leave_request.status = 'approved'
        
        # Mark student as present for sessions during leave period
        sessions = Session.query.filter_by(course_id=leave_request.course_id).filter(
            Session.date >= leave_request.start_date,
            Session.date <= leave_request.end_date
        ).all()
        
        for session in sessions:
            # Check if attendance record exists
            attendance = Attendance.query.filter_by(
                student_id=leave_request.student_id,
                session_id=session.id
            ).first()
            
            if attendance:
                attendance.status = 'present'
                attendance.notes = f"Approved leave: {leave_request.reason}"
            else:
                # Create new attendance record
                attendance = Attendance(
                    student_id=leave_request.student_id,
                    session_id=session.id,
                    status='present',
                    marked_at=datetime.now(),
                    notes=f"Approved leave: {leave_request.reason}"
                )
                db.session.add(attendance)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Leave request approved'})
    
    elif action == 'reject':
        leave_request.status = 'rejected'
        db.session.commit()
        return jsonify({'success': True, 'message': 'Leave request rejected'})
    
    return jsonify({'success': False, 'message': 'Invalid action'})

@app.route('/faculty/cancel_class/<int:session_id>', methods=['POST'])
@login_required
def cancel_class(session_id):
    if current_user.role != 'faculty':
        return jsonify({'success': False, 'message': 'Access denied'})
    
    faculty = Faculty.query.filter_by(user_id=current_user.id).first()
    session_obj = Session.query.get_or_404(session_id)
    
    # Verify course belongs to faculty
    course = Course.query.get(session_obj.course_id)
    if course.faculty_id != faculty.id:
        return jsonify({'success': False, 'message': 'Access denied: This session does not belong to your course'})
    
    # Mark all students as present
    for student in course.students:
        # Check if attendance record exists
        attendance = Attendance.query.filter_by(
            student_id=student.id,
            session_id=session_id
        ).first()
        
        if attendance:
            attendance.status = 'present'
            attendance.notes = "Class cancelled by faculty"
        else:
            # Create new attendance record
            attendance = Attendance(
                student_id=student.id,
                session_id=session_id,
                status='present',
                marked_at=datetime.now(),
                notes="Class cancelled by faculty"
            )
            db.session.add(attendance)
    
    session_obj.status = 'cancelled'
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Class cancelled and all students marked present'})

# API route for checking router ID (for location validation)
@app.route('/api/validate_router', methods=['POST'])
@login_required
def validate_router():
    router_id = request.json.get('router_id')
    course_id = request.json.get('course_id')
    
    if not router_id or not course_id:
        return jsonify({'valid': False, 'message': 'Missing router_id or course_id'})
    
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'valid': False, 'message': 'Course not found'})
    
    if int(router_id) == course.router_id:
        return jsonify({'valid': True, 'message': 'Location validated'})
    else:
        return jsonify({'valid': False, 'message': 'You are not in the correct location for this class'})

# Password reset routes
@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            # Generate token
            token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
            user.reset_token = token
            user.reset_token_expiry = datetime.now() + timedelta(hours=1)
            db.session.commit()
            
            # Send email (commented out since we don't have mail server configured)
            # send_password_reset_email(user)
            
            flash('Check your email for the instructions to reset your password', 'info')
            return redirect(url_for('login'))
        else:
            flash('Email not found', 'danger')
    
    return render_template('reset_password_request.html', form=form)

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    user = User.query.filter_by(reset_token=token).first()
    if not user or user.reset_token_expiry < datetime.now():
        flash('The reset link is invalid or has expired', 'danger')
        return redirect(url_for('index'))
    
    form = PasswordResetForm()
    if form.validate_on_submit():
        user.password_hash = generate_password_hash(form.password.data)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        flash('Your password has been reset', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html', form=form)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

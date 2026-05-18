import os
import logging
from datetime import timedelta
from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
from database import db  # Import db from database.py
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string
from datetime import datetime, timedelta
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, HiddenField, SelectMultipleField
from wtforms.validators import DataRequired, Optional
from flask_migrate import Migrate  # Import Flask-Migrate
from sqlalchemy import inspect

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "your-secret-key-here")

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///attendance.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize extensions
login_manager = LoginManager()
mail = Mail()
migrate = Migrate()

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

# Initialize database and migrations
db.init_app(app)
migrate.init_app(app, db)  # Initialize Flask-Migrate with the app and db

# Import models after db is initialized
from models import User, Student, Faculty, Course, Router, Attendance, LeaveRequest, AttendanceOTP, Session, student_course

# Check database tables
with app.app_context():
    inspector = inspect(db.engine)
    print("Database tables created:", inspector.get_table_names())

# Import forms after app and db are initialized
from forms import LoginForm, StudentRegistrationForm, FacultyRegistrationForm, CourseForm, RouterForm, OTPForm, LeaveRequestForm, SessionForm, MarkAttendanceForm, PasswordResetForm, PasswordResetRequestForm

# Define a form for updating attendance status
class AttendanceUpdateForm(FlaskForm):
    student_id = HiddenField('Student ID', validators=[DataRequired()])
    status = SelectField('Status', choices=[
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late')
    ], validators=[DataRequired()])
    submit = SubmitField('Update')

# Define a form for managing students in a course
class ManageStudentsForm(FlaskForm):
    student_id = StringField('Student ID', validators=[DataRequired()])  # Added field for student ID input
    students_to_remove = SelectMultipleField('Remove Students', coerce=int, validators=[Optional()])
    submit = SubmitField('Update Enrollment')

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
    session.clear()  # Clear Flask session to avoid stale data
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
    if not student:
        flash('No student profile found for your account. Please contact an administrator.', 'danger')
        return redirect(url_for('index'))
    
    db.session.refresh(student)  # Refresh to ensure latest courses
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
    
    # Prepare course_data for the template (for charting)
    course_data = [
        {
            'code': course.course_code,
            'attendance': attendance_stats.get(course.course_code, {}).get('percentage', 0)
        }
        for course in courses
    ]
    return render_template('student/dashboard.html', 
                          student=student, 
                          courses=courses, 
                          attendance_stats=attendance_stats,
                          course_stats=attendance_stats,
                          course_data=course_data,  # Add this line
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
    if not student:
        flash('No student profile found for your account. Please contact an administrator.', 'danger')
        return redirect(url_for('index'))
    
    # Refresh the student object to ensure relationships are up-to-date
    db.session.refresh(student)
    courses = student.courses
    
    course_id = request.args.get('course_id', type=int)
    if course_id:
        selected_course = Course.query.get_or_404(course_id)
        if (selected_course not in courses):
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

def get_subnet(ip):
    return '.'.join(ip.split('.')[:3])

@app.route('/student/mark_attendance', methods=['GET', 'POST'])
@login_required
def mark_attendance():
    if current_user.role != 'student':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    student = Student.query.filter_by(user_id=current_user.id).first()
    form = MarkAttendanceForm()
    
    # Get the student's courses and active OTP sessions
    db.session.refresh(student)
    courses = student.courses
    active_sessions = []
    
    # Get current time for calculating remaining time
    now = datetime.now()
    app.logger.info(f"Checking active OTPs at {now}")
    
    # Find all active OTP sessions for courses the student is enrolled in
    for course in courses:
        active_otps = AttendanceOTP.query.filter_by(
            course_id=course.id, 
            is_active=True
        ).all()
        
        for otp in active_otps:
            # Check if OTP has expired
            if otp.expiration < now:
                app.logger.info(f"OTP {otp.otp} for session {otp.session_id} has expired, deactivating")
                otp.is_active = False
                db.session.commit()
                continue
            
            # Check if attendance is not already marked by the student
            session = Session.query.get(otp.session_id)
            if not session:
                app.logger.warning(f"Session {otp.session_id} not found for OTP {otp.otp}")
                continue
            
            existing_attendance = Attendance.query.filter_by(
                student_id=student.id,
                session_id=session.id
            ).first()
            
            # Allow marking if no attendance record exists or if it was created by the system
            if not existing_attendance or existing_attendance.marked_by == 'system':
                # Calculate remaining time in minutes
                remaining_minutes = (otp.expiration - now).total_seconds() // 60
                router_id = course.router_id if course.router_id else None
                active_sessions.append({
                    'course': course,
                    'session': session,
                    'otp': otp,
                    'remaining_minutes': int(remaining_minutes),
                    'router_id': router_id
                })
                app.logger.info(f"Found active session for course {course.course_code}, OTP {otp.otp}, router_id {router_id}")
            else:
                app.logger.info(f"Student {student.student_id} already marked attendance for session {session.id}")
    
    if form.validate_on_submit():
        otp_value = form.otp.data
        router_id = form.router_id.data
        
        # --- IP address validation ---
        course = None
        if router_id:
            course = Course.query.filter_by(router_id=int(router_id)).first()
        if course:
            router = Router.query.get(course.router_id)
            expected_ip = router.mac_address  # Actually stores IP address now
            student_ip = request.remote_addr
            # Compare subnet instead of full IP
            if expected_ip and get_subnet(student_ip) != get_subnet(expected_ip):
                flash(f"Your network subnet ({get_subnet(student_ip)}) does not match the class router's subnet ({get_subnet(expected_ip)}). Please connect to the correct Wi-Fi.", 'danger')
                return render_template('student/mark_attendance.html', form=form, active_sessions=active_sessions)
        # --- end IP address validation ---
        
        # Verify OTP and router ID
        otp_obj = AttendanceOTP.query.filter_by(
            otp=otp_value,
            is_active=True
        ).first()
        
        if not otp_obj or otp_obj.expiration < datetime.now():
            flash('Invalid or expired OTP', 'danger')
            return render_template('student/mark_attendance.html', form=form, active_sessions=active_sessions)
        
        # Get the course and its associated router
        course = Course.query.get(otp_obj.course_id)
        if not course or (router_id and int(router_id) != course.router_id):
            flash('You are not in the correct location for this class', 'danger')
            return render_template('student/mark_attendance.html', form=form, active_sessions=active_sessions)
        
        # Check for existing attendance
        existing_attendance = Attendance.query.filter_by(
            student_id=student.id,
            session_id=otp_obj.session_id
        ).first()
        
        if existing_attendance and existing_attendance.marked_by == 'student':
            flash('You have already marked attendance for this session', 'warning')
            return render_template('student/mark_attendance.html', form=form, active_sessions=active_sessions)
        
        if existing_attendance:
            existing_attendance.status = 'present'
            existing_attendance.marked_at = datetime.now()
            existing_attendance.marked_by = 'student'
        else:
            attendance = Attendance(
                student_id=student.id,
                session_id=otp_obj.session_id,
                status='present',
                marked_at=datetime.now(),
                marked_by='student'
            )
            db.session.add(attendance)
        
        db.session.commit()
        flash('Attendance marked successfully', 'success')
        return redirect(url_for('student_dashboard'))
    
    # Pre-populate router_id in the form for each active session
    if active_sessions and form.router_id.data is None and active_sessions[0].get('router_id'):
        form.router_id.data = str(active_sessions[0]['router_id'])
    
    # Ensure the form is rendered even if no active sessions are found
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
    db.session.refresh(student)
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
    if not faculty:
        flash('No faculty profile found for your account. Please contact an administrator.', 'danger')
        return redirect(url_for('index'))
    
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
    
    # Prepare course_data for the template
    course_data = [
        {
            'code': course.course_code,
            'attendance': course_stats.get(course.id, {}).get('attendance_rate', 0)
        }
        for course in courses
    ]
    
    return render_template('faculty/dashboard.html', 
                          faculty=faculty, 
                          courses=courses,
                          recent_sessions=recent_sessions,
                          pending_leaves=pending_leaves,
                          course_stats=course_stats,
                          course_data=course_data)

@app.route('/faculty/manage_courses', methods=['GET', 'POST'])
@login_required
def manage_courses():
    if current_user.role != 'faculty':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    faculty = Faculty.query.filter_by(user_id=current_user.id).first()
    if not faculty:
        flash('No faculty profile found for your account. Please contact an administrator.', 'danger')
        return redirect(url_for('index'))
    
    form = CourseForm()
    routers = Router.query.all()
    form.router_id.choices = [(r.id, f"{r.location} - {r.name}") for r in routers]
    
    if form.validate_on_submit():
        try:
            course = Course(
                course_code=form.course_code.data,
                title=form.title.data,
                faculty_id=faculty.id,
                schedule=form.schedule.data,
                classroom=form.classroom.data,
                router_id=form.router_id.data
            )
            db.session.add(course)
            db.session.flush()  # Get course.id before commit
            
            # Automatically enroll students
            if faculty.department:
                students = Student.query.filter_by(department=faculty.department).all()
                if not students:
                    # Fallback: Enroll all students if no department match
                    students = Student.query.all()
                    flash('No students found in your department. Enrolled all students instead.', 'warning')
            else:
                # Fallback: Enroll all students if faculty.department is None
                students = Student.query.all()
                flash('Faculty department not set. Enrolled all students instead.', 'warning')
            
            for student in students:
                course.students.append(student)
            
            db.session.commit()
            flash('Course added and students enrolled successfully', 'success')
            return redirect(url_for('manage_courses'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding course: {str(e)}", 'danger')
            return redirect(url_for('manage_courses'))
    
    courses = Course.query.filter_by(faculty_id=faculty.id).all()
    return render_template('faculty/manage_courses.html', 
                          form=form, 
                          faculty=faculty,
                          courses=courses,
                          routers=routers)

@app.route('/faculty/add_router', methods=['GET', 'POST'])
@login_required
def add_router_route():
    if current_user.role != 'faculty':
        flash('Access denied: You must be a faculty member to add routers', 'danger')
        return redirect(url_for('index'))

    faculty = Faculty.query.filter_by(user_id=current_user.id).first()
    if not faculty:
        flash('No faculty profile found for your account. Please contact an administrator.', 'danger')
        return redirect(url_for('index'))

    # Import add_router here to avoid circular import
    from add_router import add_router

    form = RouterForm()
    if form.validate_on_submit():
        success, message = add_router(
            name=form.name.data,
            location=form.location.data,
            ip_address=form.mac_address.data  # Updated to ip_address
        )
        if success:
            flash(message, 'success')
            return redirect(url_for('manage_courses'))
        else:
            flash(message, 'danger')

    # Display existing routers
    routers = Router.query.all()
    return render_template('faculty/add_router.html', form=form, faculty=faculty, routers=routers)

@app.route('/faculty/edit_router/<int:router_id>', methods=['GET', 'POST'])
@login_required
def edit_router(router_id):
    if current_user.role != 'faculty':
        flash('Access denied: You must be a faculty member to edit routers', 'danger')
        return redirect(url_for('index'))

    router = Router.query.get_or_404(router_id)
    form = RouterForm(obj=router)

    if form.validate_on_submit():
        router.name = form.name.data
        router.location = form.location.data
        router.mac_address = form.mac_address.data
        try:
            db.session.commit()
            flash(f"Router '{router.name}' updated successfully!", 'success')
            return redirect(url_for('add_router_route'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating router: {str(e)}", 'danger')

    return render_template('faculty/edit_router.html', form=form, router=router)

@app.route('/faculty/delete_router/<int:router_id>', methods=['POST'])
@login_required
def delete_router(router_id):
    if current_user.role != 'faculty':
        flash('Access denied: You must be a faculty member to delete routers', 'danger')
        return redirect(url_for('index'))

    router = Router.query.get_or_404(router_id)
    # Check if any course is using this router
    courses_using_router = Course.query.filter_by(router_id=router.id).all()
    if courses_using_router:
        flash("Cannot delete router: It is assigned to one or more courses. Please reassign or delete those courses first.", "danger")
        return redirect(url_for('add_router_route'))

    try:
        db.session.delete(router)
        db.session.commit()
        flash(f"Router '{router.name}' deleted successfully!", 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting router: {str(e)}", 'danger')

    return redirect(url_for('add_router_route'))

@app.route('/faculty/delete_course/<int:course_id>', methods=['POST'])
@login_required
def delete_course(course_id):
    if current_user.role != 'faculty':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    faculty = Faculty.query.filter_by(user_id=current_user.id).first()
    course = Course.query.get_or_404(course_id)
    
    # Verify course belongs to faculty
    if course.faculty_id != faculty.id:
        flash('Access denied: This course does not belong to you', 'danger')
        return redirect(url_for('manage_courses'))
    
    try:
        # Delete related OTPs manually (since cascade isn't defined for AttendanceOTP)
        AttendanceOTP.query.filter_by(course_id=course.id).delete()

        # Explicitly delete all attendance records for all sessions in this course
        session_ids = [s.id for s in course.sessions]
        if session_ids:
            Attendance.query.filter(Attendance.session_id.in_(session_ids)).delete(synchronize_session=False)

        # The cascade="all, delete-orphan" on Course model handles:
        # - Sessions (and their Attendance records via backref)
        # - LeaveRequests
        # The StudentCourse entries are automatically deleted due to the relationship

        db.session.delete(course)
        db.session.commit()
        flash(f'Course {course.course_code} deleted successfully', 'success')
        app.logger.info(f"Faculty {faculty.faculty_id} deleted course {course.course_code}")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting course: {str(e)}", 'danger')
        app.logger.error(f"Error deleting course {course_id} by faculty {faculty.faculty_id}: {str(e)}")
    
    return redirect(url_for('manage_courses'))

@app.route('/faculty/course/<int:course_id>', methods=['GET', 'POST'])
@login_required
def course_detail(course_id):
    if current_user.role != 'faculty':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    faculty = Faculty.query.filter_by(user_id=current_user.id).first()
    if not faculty:
        flash('No faculty profile found for your account. Please contact an administrator.', 'danger')
        return redirect(url_for('index'))
    
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
    
    # Prepare attendance data for each session and student
    session_attendance = {}
    for session in sessions:
        session_attendance[session.id] = {}
        for student in students:
            attendance = Attendance.query.filter_by(
                student_id=student.id,
                session_id=session.id
            ).first()
            if not attendance:
                # Create a default attendance record if none exists
                attendance = Attendance(
                    student_id=student.id,
                    session_id=session.id,
                    status='absent',
                    marked_at=datetime.now(),
                    marked_by='system'
                )
                db.session.add(attendance)
            session_attendance[session.id][student.id] = attendance
    db.session.commit()

    # Get attendance statistics for the course
    attendance_data = {}
    for student in students:
        attendance_data[student.id] = {
            'present': 0,
            'absent': 0,
            'late': 0,
            'total': len(sessions),
            'percentage': 0
        }
        
        for session in sessions:
            attendance = session_attendance[session.id][student.id]
            if attendance.status == 'present':
                attendance_data[student.id]['present'] += 1
            elif attendance.status == 'absent':
                attendance_data[student.id]['absent'] += 1
            elif attendance.status == 'late':
                attendance_data[student.id]['late'] += 1
        
        if attendance_data[student.id]['total'] > 0:
            attendance_data[student.id]['percentage'] = round(
                (attendance_data[student.id]['present'] / attendance_data[student.id]['total']) * 100, 2
            )
    
    # Calculate attendance distribution counts (based on percentage)
    high_count = sum(1 for student in students if attendance_data.get(student.id, {}).get('percentage', 0) >= 75)
    medium_count = sum(1 for student in students if 60 <= attendance_data.get(student.id, {}).get('percentage', 0) < 75)
    low_count = sum(1 for student in students if attendance_data.get(student.id, {}).get('percentage', 0) < 60)
    
    return render_template('faculty/course_detail.html',
                          course=course,
                          faculty=faculty,
                          session_form=session_form,
                          sessions=sessions,
                          students=students,
                          session_attendance=session_attendance,
                          attendance_data=attendance_data,
                          high_count=high_count,
                          medium_count=medium_count,
                          low_count=low_count)

@app.route('/faculty/course/<int:course_id>/manage_students', methods=['GET', 'POST'])
@login_required
def manage_students(course_id):
    if current_user.role != 'faculty':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    faculty = Faculty.query.filter_by(user_id=current_user.id).first()
    course = Course.query.get_or_404(course_id)
    
    # Verify course belongs to faculty
    if course.faculty_id != faculty.id:
        flash('Access denied: This course does not belong to you', 'danger')
        return redirect(url_for('manage_courses'))
    
    # Get enrolled students
    enrolled_students = course.students
    
    form = ManageStudentsForm()
    # Populate the students_to_remove choices with enrolled students
    form.students_to_remove.choices = [
        (student.id, f"{student.student_id} - {student.user.first_name} {student.user.last_name}")
        for student in enrolled_students
    ]
    
    if form.validate_on_submit():
        # Handle adding a student by student_id
        student_id_input = form.student_id.data
        student_to_add = Student.query.filter_by(student_id=student_id_input).first()
        
        if student_to_add:
            if student_to_add in enrolled_students:
                flash(f'Student {student_to_add.student_id} is already enrolled in this course', 'warning')
            else:
                course.students.append(student_to_add)
                app.logger.info(f"Faculty {faculty.faculty_id} added student {student_to_add.student_id} to course {course.course_code}")
                flash(f'Student {student_to_add.student_id} added successfully', 'success')
        else:
            flash(f'Student with ID {student_id_input} not found', 'danger')
        
        # Handle removing students
        students_to_remove = form.students_to_remove.data
        for student_id in students_to_remove:
            student = Student.query.get(student_id)
            if student and student in enrolled_students:
                course.students.remove(student)
                # Remove associated attendance and leave requests for this student in this course
                Attendance.query.filter_by(student_id=student.id).join(Session).filter(Session.course_id == course.id).delete()
                LeaveRequest.query.filter_by(student_id=student.id, course_id=course.id).delete()
                app.logger.info(f"Faculty {faculty.faculty_id} removed student {student.student_id} from course {course.course_code}")
                flash(f'Student {student.student_id} removed successfully', 'success')
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating enrollment for course {course.course_code}: {str(e)}")
            flash(f"Error updating enrollment: {str(e)}", 'danger')
        
        return redirect(url_for('course_detail', course_id=course.id))
    
    # If the form is not submitted, render the template with the current enrollment status
    all_students = Student.query.all()
    available_students = [student for student in all_students if student not in enrolled_students]
    
    return render_template('faculty/manage_students.html',
                          form=form,
                          course=course,
                          faculty=faculty,
                          enrolled_students=enrolled_students,
                          available_students=available_students)

@app.route('/faculty/update_attendance/<int:session_id>', methods=['POST'])
@login_required
def update_attendance(session_id):
    if current_user.role != 'faculty':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    faculty = Faculty.query.filter_by(user_id=current_user.id).first()
    session_obj = Session.query.get_or_404(session_id)
    course = Course.query.get(session_obj.course_id)

    if course.faculty_id != faculty.id:
        flash('Access denied: This session does not belong to your course', 'danger')
        return redirect(url_for('course_detail', course_id=course.id))

    if session_obj.status == 'cancelled':
        flash('Cannot update attendance for a cancelled session', 'danger')
        return redirect(url_for('course_detail', course_id=course.id))

    updated_records = 0

    for key, value in request.form.items():
        if key.startswith('status_'):
            try:
                student_id = int(key.split('_')[1])
            except (IndexError, ValueError):
                continue
            student = Student.query.get(student_id)
            if not student or student not in course.students:
                continue
            if value not in ['present', 'absent', 'late']:
                continue

            attendance = Attendance.query.filter_by(
                student_id=student_id,
                session_id=session_id
            ).with_for_update().first()
            if attendance:
                # Remove "Class cancelled by faculty" note if present
                if attendance.notes and "Class cancelled by faculty" in str(attendance.notes):
                    attendance.notes = None
                attendance.status = value
                attendance.marked_at = datetime.now()
                attendance.marked_by = 'faculty'
                # No need to add again, just update
            else:
                attendance = Attendance(
                    student_id=student_id,
                    session_id=session_id,
                    status=value,
                    marked_at=datetime.now(),
                    marked_by='faculty'
                )
                db.session.add(attendance)
            updated_records += 1

    try:
        db.session.flush()  # Ensure all changes are staged
        db.session.commit()
        flash(f'Attendance updated for {updated_records} student(s)', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating attendance: {e}', 'danger')

    return redirect(url_for('course_detail', course_id=course.id))

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
    
    # Check if the session is in the past
    session_date = datetime.combine(session_obj.date, session_obj.start_time)
    if session_date < datetime.now():
        flash('Cannot generate OTP for a past session', 'danger')
        return redirect(url_for('course_detail', course_id=course.id))
    
    # Check if the session is cancelled
    if session_obj.status == 'cancelled':
        flash('Cannot generate OTP for a cancelled session', 'danger')
        return redirect(url_for('course_detail', course_id=course.id))
    
    form = OTPForm()
    form.router_id.data = str(course.router_id) if course.router_id else ''
    
    if form.validate_on_submit():
        router_id = form.router_id.data
        
        # Verify faculty is in the correct location
        if int(router_id) != course.router_id:
            app.logger.warning(f"Faculty {faculty.faculty_id} failed location validation for course {course.course_code}")
            flash('Error: You are not in the correct location for this class', 'danger')
            return redirect(url_for('generate_otp', session_id=session_id))
        
        # Check if an active OTP already exists
        existing_active_otp = AttendanceOTP.query.filter_by(
            session_id=session_id,
            is_active=True
        ).first()
        if existing_active_otp:
            flash(f'An active OTP already exists: {existing_active_otp.otp} (expires at {existing_active_otp.expiration})', 'warning')
            return redirect(url_for('course_detail', course_id=course.id))
        
        # Deactivate any existing OTPs for this session (as a precaution)
        existing_otps = AttendanceOTP.query.filter_by(session_id=session_id).all()
        for otp in existing_otps:
            otp.is_active = False
            app.logger.info(f"Deactivated OTP {otp.otp} for session {session_id}")
        
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
        
        app.logger.info(f"Generated OTP {otp_value} for session {session_id} by faculty {faculty.faculty_id}")
        flash(f'OTP generated successfully: {otp_value} (expires at {expiration.strftime("%H:%M:%S")})', 'success')
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
        
        # Calculate attendance distribution counts
        high_count = sum(1 for data in attendance_data.values() if data['percentage'] >= 75)
        medium_count = sum(1 for data in attendance_data.values() if 60 <= data['percentage'] < 75)
        low_count = sum(1 for data in attendance_data.values() if data['percentage'] < 60)
    else:
        selected_course = None
        students = []
        sessions = []
        attendance_data = {}
        high_count = medium_count = low_count = 0
    
    return render_template('faculty/attendance_report.html',
                          faculty=faculty,
                          courses=courses,
                          selected_course=selected_course,
                          students=students,
                          sessions=sessions,
                          attendance_data=attendance_data,
                          high_count=high_count,
                          medium_count=medium_count,
                          low_count=low_count)

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
        
        updated_sessions = 0
        for session in sessions:
            # Skip cancelled sessions
            if session.status == 'cancelled':
                app.logger.info(f"Skipped marking attendance for cancelled session {session.id} during leave approval")
                continue
            
            # Check if attendance record exists
            attendance = Attendance.query.filter_by(
                student_id=leave_request.student_id,
                session_id=session.id
            ).first()
            
            if attendance:
                old_status = attendance.status
                attendance.status = 'present'
                attendance.notes = f"Approved leave: {leave_request.reason}"
                attendance.marked_by = 'faculty'
                app.logger.info(f"Updated attendance for student {leave_request.student_id} in session {session.id} due to approved leave: status changed from {old_status} to present")
            else:
                # Create new attendance record
                attendance = Attendance(
                    student_id=leave_request.student_id,
                    session_id=session.id,
                    status='present',
                    marked_at=datetime.now(),
                    marked_by='faculty',
                    notes=f"Approved leave: {leave_request.reason}"
                )
                db.session.add(attendance)
                app.logger.info(f"Created new attendance record for student {leave_request.student_id} in session {session.id} due to approved leave: status=present")
            
            updated_sessions += 1
        
        db.session.commit()
        app.logger.info(f"Approved leave request {request_id} by faculty {faculty.faculty_id}: updated {updated_sessions} sessions")
        return jsonify({'success': True, 'message': f'Leave request approved and attendance updated for {updated_sessions} session(s)'})
    
    elif action == 'reject':
        leave_request.status = 'rejected'
        db.session.commit()
        app.logger.info(f"Rejected leave request {request_id} by faculty {faculty.faculty_id}")
        return jsonify({'success': True, 'message': 'Leave request rejected'})
    
    app.logger.warning(f"Invalid action {action} for leave request {request_id} by faculty {faculty.faculty_id}")
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
    
    # Check if the session is already cancelled
    if session_obj.status == 'cancelled':
        app.logger.warning(f"Session {session_id} is already cancelled by faculty {faculty.faculty_id}")
        return jsonify({'success': False, 'message': 'This session is already cancelled'})
    
    # Mark all students as present
    updated_students = 0
    for student in course.students:
        # Check if attendance record exists
        attendance = Attendance.query.filter_by(
            student_id=student.id,
            session_id=session_id
        ).first()
        
        if attendance:
            old_status = attendance.status
            attendance.status = 'present'
            attendance.notes = "Class cancelled by faculty"
            attendance.marked_by = 'faculty'
            app.logger.info(f"Updated attendance for student {student.student_id} in session {session_id} due to class cancellation: status changed from {old_status} to present")
        else:
            # Create new attendance record
            attendance = Attendance(
                student_id=student.id,
                session_id=session_id,
                status='present',
                marked_at=datetime.now(),
                marked_by='faculty',
                notes="Class cancelled by faculty"
            )
            db.session.add(attendance)
            app.logger.info(f"Created new attendance record for student {student.student_id} in session {session_id} due to class cancellation: status=present")
        
        updated_students += 1
    
    session_obj.status = 'cancelled'
    db.session.commit()
    
    app.logger.info(f"Cancelled session {session_id} by faculty {faculty.faculty_id}: marked {updated_students} students as present")
    return jsonify({'success': True, 'message': f'Class cancelled and {updated_students} students marked present'})

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
    
    # Simulate server-side validation of the student's network
    # In a real-world scenario, you'd use the client's IP address or a network identifier
    # Here, we assume the router_id is a placeholder for network validation
    # Example: Check client's IP against a known IP range for the router (requires additional setup)
    client_ip = request.remote_addr
    # For demonstration, we'll assume a simple check (you'd need a mapping of router_id to IP ranges)
    # This is a placeholder; actual implementation requires network infrastructure
    expected_router_id = course.router_id
    if int(router_id) == expected_router_id:
        app.logger.info(f"Location validated for course {course.course_code}, router_id {router_id}, client IP {client_ip}")
        return jsonify({'valid': True, 'message': 'Location validated'})
    else:
        app.logger.warning(f"Location validation failed for course {course.course_code}, router_id {router_id}, client IP {client_ip}")
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

@app.route('/faculty/course/<int:course_id>/remove_student/<int:student_id>', methods=['POST'])
@login_required
def remove_student_from_course(course_id, student_id):
    if current_user.role != 'faculty':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    faculty = Faculty.query.filter_by(user_id=current_user.id).first()
    course = Course.query.get_or_404(course_id)
    student = Student.query.get_or_404(student_id)

    # Verify course belongs to faculty
    if course.faculty_id != faculty.id:
        flash('Access denied: This course does not belong to you', 'danger')
        return redirect(url_for('manage_courses'))

    # Remove student from course
    if student in course.students:
        course.students.remove(student)
        # Remove associated attendance and leave requests for this student in this course
        # Fix: Do NOT use .join(Session) in delete query, use subquery for session_ids
        session_ids = [s.id for s in course.sessions]
        if session_ids:
            Attendance.query.filter(
                Attendance.student_id == student.id,
                Attendance.session_id.in_(session_ids)
            ).delete(synchronize_session=False)
        LeaveRequest.query.filter_by(student_id=student.id, course_id=course.id).delete(synchronize_session=False)
        db.session.commit()
        flash(f"Student {student.student_id} removed from course.", "success")
    else:
        flash("Student not enrolled in this course.", "warning")

    return redirect(url_for('course_detail', course_id=course.id))

@app.route('/faculty/course/<int:course_id>/update_student/<int:student_id>/<string:field>', methods=['POST'])
@login_required
def update_student_field(course_id, student_id, field):
    if current_user.role != 'faculty':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    student = Student.query.get_or_404(student_id)
    user = student.user

    if field == 'student_id':
        value = request.form.get('value')
        if value:
            student.student_id = value
            db.session.commit()
            flash('Student ID updated.', 'success')
    elif field == 'name':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        if first_name and last_name:
            user.first_name = first_name
            user.last_name = last_name
            db.session.commit()
            flash('Student name updated.', 'success')
    elif field == 'status':
        # This is just a display status, not stored in DB, so just flash a message.
        flash('Status is calculated from attendance and cannot be changed directly.', 'info')
    else:
        flash('Invalid field.', 'danger')

    return redirect(url_for('course_detail', course_id=course_id))

@app.route('/faculty/edit_course/<int:course_id>', methods=['POST'])
@login_required
def edit_course(course_id):
    if current_user.role != 'faculty':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    faculty = Faculty.query.filter_by(user_id=current_user.id).first()
    course = Course.query.get_or_404(course_id)
    if course.faculty_id != faculty.id:
        flash('Access denied: This course does not belong to you', 'danger')
        return redirect(url_for('manage_courses'))

    # Update editable fields
    course.title = request.form.get('title')
    course.schedule = request.form.get('schedule')
    course.classroom = request.form.get('classroom')
    router_id = request.form.get('router_id', type=int)
    if router_id:
        course.router_id = router_id

    try:
        db.session.commit()
        flash('Course updated successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating course: {str(e)}', 'danger')
    return redirect(url_for('manage_courses'))

if __name__ == '__main__':
    app.run(debug=True)
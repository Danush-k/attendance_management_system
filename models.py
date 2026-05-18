from datetime import datetime
from flask_login import UserMixin
from database import db  # Import db from database.py

# Association table for student-course many-to-many relationship
student_course = db.Table('student_course',
    db.Column('student_id', db.Integer, db.ForeignKey('student.id'), primary_key=True),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'), primary_key=True),
    extend_existing=True  # Allow redefinition of the table
)

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student' or 'faculty'
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime, nullable=True)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    
    # Relationships (aligned with app.py expectations)
    students = db.relationship('Student', backref='user', lazy=True)
    faculty = db.relationship('Faculty', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.email}>'

class Student(db.Model):
    __tablename__ = 'student'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student_id = db.Column(db.String(20), unique=True, nullable=False)  # University ID
    department = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    
    # Relationships
    courses = db.relationship('Course', secondary=student_course, lazy='subquery',
                            backref=db.backref('students', lazy=True))
    attendances = db.relationship('Attendance', backref='student', lazy=True)
    leave_requests = db.relationship('LeaveRequest', backref='student', lazy=True)
    
    def __repr__(self):
        return f'<Student {self.student_id}>'

class Faculty(db.Model):
    __tablename__ = 'faculty'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    faculty_id = db.Column(db.String(20), unique=True, nullable=False)  # University ID
    department = db.Column(db.String(100), nullable=False)
    designation = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    
    # Relationships
    courses = db.relationship('Course', backref='faculty', lazy=True)
    
    def __repr__(self):
        return f'<Faculty {self.faculty_id}>'

class Router(db.Model):
    __tablename__ = 'router'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    mac_address = db.Column(db.String(20), nullable=True)
    
    # Relationships
    courses = db.relationship('Course', backref='router', lazy=True)
    
    def __repr__(self):
        return f'<Router {self.name} at {self.location}>'

class Course(db.Model):
    __tablename__ = 'course'
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), nullable=False, unique=True)
    title = db.Column(db.String(200), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    schedule = db.Column(db.String(255), nullable=True)  # Days and times
    classroom = db.Column(db.String(100), nullable=True)
    router_id = db.Column(db.Integer, db.ForeignKey('router.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships (students is defined via backref in student_course)
    sessions = db.relationship('Session', backref='course', lazy=True, cascade="all, delete-orphan")
    leave_requests = db.relationship('LeaveRequest', backref='course', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Course {self.course_code}: {self.title}>'

class Session(db.Model):
    __tablename__ = 'session'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    topic = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='scheduled')  # scheduled, ongoing, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    attendances = db.relationship('Attendance', backref='session', lazy=True)
    otps = db.relationship('AttendanceOTP', backref='session', lazy=True)
    
    def __repr__(self):
        return f'<Session {self.id} for {self.course.course_code} on {self.date}>'

class Attendance(db.Model):
    __tablename__ = 'attendance'
    __table_args__ = (
        db.UniqueConstraint('student_id', 'session_id', name='_student_session_uc'),
    )
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # present, absent, late
    marked_at = db.Column(db.DateTime, nullable=False)
    marked_by = db.Column(db.String(20), nullable=False, default='system')  # 'system', 'student', or 'faculty'
    notes = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<Attendance: Student {self.student_id} for Session {self.session_id}>'

class AttendanceOTP(db.Model):
    __tablename__ = 'attendance_otp'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    otp = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    expiration = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    course = db.relationship('Course')
    
    def __repr__(self):
        return f'<AttendanceOTP {self.otp} for Session {self.session_id}>'

class LeaveRequest(db.Model):
    __tablename__ = 'leave_request'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<LeaveRequest {self.id} from Student {self.student_id}>'
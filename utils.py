import random
import string
from datetime import datetime, timedelta
from flask import current_app
from flask_mail import Message
from app import mail

def generate_otp(length=6):
    """Generate a random OTP (alphanumeric)"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def validate_router_location(router_id, course_router_id):
    """
    Validate if the current router matches the course's assigned router
    (This is a simplified version - in a real system, you'd use MAC addresses or signal strength)
    """
    return int(router_id) == int(course_router_id)

def calculate_attendance_percentage(present_count, total_sessions):
    """Calculate attendance percentage"""
    if total_sessions == 0:
        return 0
    return round((present_count / total_sessions) * 100, 2)

def is_attendance_below_threshold(percentage, threshold=75):
    """Check if attendance is below threshold"""
    return percentage < threshold

def send_attendance_warning_email(student, course, percentage):
    """Send warning email to student for low attendance"""
    subject = f"Low Attendance Warning - {course.course_code}"
    body = f"""
    Dear {student.user.first_name} {student.user.last_name},
    
    This is to inform you that your attendance in {course.course_code} ({course.title}) has fallen below the minimum required threshold.
    
    Current Attendance: {percentage}%
    Minimum Required: 75%
    
    Please ensure you attend classes regularly to meet the attendance requirements for course completion.
    
    Regards,
    Administration
    """
    
    try:
        msg = Message(
            subject=subject,
            recipients=[student.user.email],
            body=body
        )
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send email: {str(e)}")
        return False

def send_password_reset_email(user):
    """Send password reset email"""
    reset_url = f"http://localhost:5000/reset_password/{user.reset_token}"
    subject = "Password Reset Request"
    body = f"""
    Dear {user.first_name} {user.last_name},
    
    To reset your password, please visit the following link:
    
    {reset_url}
    
    If you did not make this request, please ignore this email.
    
    Regards,
    Administration
    """
    
    try:
        msg = Message(
            subject=subject,
            recipients=[user.email],
            body=body
        )
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send email: {str(e)}")
        return False

def send_leave_request_notification(faculty, student, leave_request):
    """Send notification to faculty about new leave request"""
    subject = f"New Leave Request - {student.user.first_name} {student.user.last_name}"
    body = f"""
    Dear {faculty.user.first_name} {faculty.user.last_name},
    
    A new leave request has been submitted by {student.user.first_name} {student.user.last_name} ({student.student_id}).
    
    Course: {leave_request.course.course_code} - {leave_request.course.title}
    Period: {leave_request.start_date.strftime('%d-%m-%Y')} to {leave_request.end_date.strftime('%d-%m-%Y')}
    Reason: {leave_request.reason}
    
    Please review this request in your dashboard.
    
    Regards,
    Administration
    """
    
    try:
        msg = Message(
            subject=subject,
            recipients=[faculty.user.email],
            body=body
        )
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send email: {str(e)}")
        return False

def get_attendance_summary(student, course):
    """Get attendance summary for a student in a course"""
    from models import Session, Attendance
    
    sessions = Session.query.filter_by(course_id=course.id).all()
    total_sessions = len(sessions)
    present_count = 0
    absent_count = 0
    late_count = 0
    
    for session in sessions:
        attendance = Attendance.query.filter_by(
            student_id=student.id,
            session_id=session.id
        ).first()
        
        if attendance:
            if attendance.status == 'present':
                present_count += 1
            elif attendance.status == 'absent':
                absent_count += 1
            elif attendance.status == 'late':
                late_count += 1
                present_count += 0.5  # Count late as partial attendance
    
    percentage = calculate_attendance_percentage(present_count, total_sessions)
    
    return {
        'total_sessions': total_sessions,
        'present': present_count,
        'absent': absent_count,
        'late': late_count,
        'percentage': percentage
    }

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField
from wtforms import TextAreaField, DateField, TimeField, IntegerField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional
from datetime import date

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class StudentRegistrationForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    student_id = StringField('Student ID', validators=[DataRequired(), Length(min=5, max=20)])
    department = StringField('Department', validators=[DataRequired()])
    year = IntegerField('Year of Study', validators=[DataRequired()])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=15)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class FacultyRegistrationForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    faculty_id = StringField('Faculty ID', validators=[DataRequired(), Length(min=5, max=20)])
    department = StringField('Department', validators=[DataRequired()])
    designation = StringField('Designation', validators=[Optional()])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=15)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class CourseForm(FlaskForm):
    course_code = StringField('Course Code', validators=[DataRequired(), Length(min=3, max=20)])
    title = StringField('Course Title', validators=[DataRequired(), Length(min=3, max=200)])
    schedule = StringField('Schedule (e.g., Mon-Wed-Fri 10:00-11:00)', validators=[DataRequired()])
    classroom = StringField('Classroom', validators=[DataRequired()])
    router_id = SelectField('Wi-Fi Router', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Add Course')

class RouterForm(FlaskForm):
    name = StringField('Router Name', validators=[DataRequired()])
    location = StringField('Location', validators=[DataRequired()])
    mac_address = StringField('MAC Address', validators=[Optional()])
    submit = SubmitField('Add Router')

class SessionForm(FlaskForm):
    date = DateField('Date', validators=[DataRequired()])
    start_time = TimeField('Start Time', validators=[DataRequired()])
    end_time = TimeField('End Time', validators=[DataRequired()])
    topic = StringField('Topic', validators=[Optional()])
    submit = SubmitField('Add Session')
    
    def validate_date(self, date_field):
        if date_field.data < date.today():
            raise ValidationError('Session date cannot be in the past')
    
    def validate_end_time(self, end_time_field):
        if self.start_time.data and end_time_field.data and end_time_field.data <= self.start_time.data:
            raise ValidationError('End time must be after start time')

class OTPForm(FlaskForm):
    router_id = HiddenField('Router ID', validators=[DataRequired()])
    submit = SubmitField('Generate OTP')

class MarkAttendanceForm(FlaskForm):
    otp = StringField('Enter OTP', validators=[DataRequired(), Length(min=6, max=6)])
    router_id = HiddenField('Router ID')
    submit = SubmitField('Mark Attendance')

class LeaveRequestForm(FlaskForm):
    course_id = SelectField('Course', coerce=int, validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    reason = TextAreaField('Reason', validators=[DataRequired(), Length(min=10, max=500)])
    submit = SubmitField('Submit Request')
    
    def validate_end_date(self, end_date_field):
        if self.start_date.data and end_date_field.data and end_date_field.data < self.start_date.data:
            raise ValidationError('End date must be after or equal to start date')

class PasswordResetRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

class PasswordResetForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')

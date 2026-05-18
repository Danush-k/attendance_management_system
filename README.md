# Attendance Management System with Proxy Elimination

A comprehensive web-based attendance management system designed for educational institutions with **router-based location detection** to eliminate proxy attendance and ensure authentic classroom presence verification.

## 📋 Overview

This system provides an integrated solution for managing student attendance with advanced location-based verification using WiFi router detection. Built with Flask and SQLAlchemy, it offers a secure, scalable, and user-friendly platform for faculty and students to manage attendance records efficiently.

### Key Features

- **Proxy Elimination**: Router-based location detection ensures students mark attendance only from designated classroom locations
- **Role-Based Access Control**: Separate interfaces for students and faculty
- **OTP Authentication**: Secure one-time password generation for attendance verification
- **Leave Management**: Streamlined leave request and approval workflow
- **Attendance Analytics**: Real-time attendance tracking and reporting with percentage calculations
- **Email Notifications**: Automated low attendance warnings and system notifications
- **Course Management**: Faculty can manage courses, students, and attendance sessions
- **Responsive Design**: Modern, mobile-friendly web interface
- **Database Persistence**: Reliable SQLAlchemy ORM with PostgreSQL/SQLite support

## 🏗️ System Architecture

### Technology Stack

#### 🔧 Backend & Framework
- **Flask** `3.1+` - Lightweight and flexible Python web framework
- **Python** `3.11+` - Core programming language
- **Gunicorn** - Production-grade WSGI HTTP Server

#### 💾 Database & ORM
- **SQLAlchemy** `2.0+` - Powerful Object-Relational Mapping (ORM)
- **PostgreSQL** - Primary production database (recommended)
- **SQLite** - Development/testing database option
- **Flask-Migrate** - Database migration management with Alembic

#### 🔐 Authentication & Security
- **Flask-Login** - User session management
- **Werkzeug** - WSGI utilities and password hashing
- **Flask-WTF** `1.2.2+` - CSRF protection and form security

#### 📧 Email & Communication
- **Flask-Mail** `0.10+` - SMTP email integration
- **Email-Validator** `2.2+` - Email validation utilities

#### 📝 Form Handling
- **WTForms** `3.2.1+` - Web form library with validation

#### 🎨 Frontend
- **HTML5** - Semantic markup
- **CSS3** - Responsive styling
- **JavaScript** - Client-side interactivity
- **Charts.js** - Data visualization for analytics

### Project Structure

```
StudentManagementSystem/
├── app.py                      # Flask application initialization
├── main.py                     # Application entry point
├── database.py                 # Database configuration
├── models.py                   # SQLAlchemy models (User, Student, Faculty, Course, etc.)
├── forms.py                    # WTForms form definitions
├── utils.py                    # Utility functions (OTP, email, validation)
├── inject_user.py              # User data injection script
├── add_router.py               # Router management utilities
├── pyproject.toml              # Project dependencies and metadata
├── migrations/                 # Database migration scripts
├── static/
│   ├── css/                    # Stylesheets
│   └── js/                     # Client-side scripts
└── templates/
    ├── base.html               # Base template
    ├── login.html              # Authentication
    ├── faculty/                # Faculty dashboard & management
    └── student/                # Student dashboard & attendance
```

## 📊 Core Data Models

### User Model
- User authentication and role management (Student/Faculty)
- Email-based login system
- Password reset functionality with token expiry

### Student Model
- Student information (ID, Department, Year)
- Course enrollment management
- Attendance records
- Leave requests

### Faculty Model
- Faculty information and designation
- Course teaching assignments
- Attendance session creation and management

### Router Model
- Physical WiFi router registration
- Location tagging (classroom/building/room)
- MAC address tracking for device identification

### Course Model
- Course metadata (code, title, credits)
- Student enrollment tracking
- Associated router for location verification
- Attendance session management

### Attendance Model
- Attendance records linked to students and courses
- Router-based location verification
- OTP verification status
- Timestamp tracking

## 🔐 Security Features

### Proxy Elimination Mechanism

The system employs a **router-based location detection** approach:

1. **Router Registration**: Each classroom has a registered WiFi router with unique MAC address
2. **Location Verification**: When marking attendance, the system validates that the student's device is connected to the assigned classroom router
3. **OTP-Based Verification**: Students receive a one-time password for additional authentication
4. **Session Validation**: Attendance marked outside designated class sessions is rejected

### Authentication & Authorization

- Password hashing with Werkzeug security
- Session-based authentication with Flask-Login
- Role-based access control (RBAC) for students and faculty
- Secure password reset with time-limited tokens
- Login tracking with last login timestamp

## 🚀 Installation & Setup

### Prerequisites

- Python 3.11+
- PostgreSQL (recommended) or SQLite
- pip or pipenv package manager
- SMTP server credentials (for email functionality)

### Step 1: Clone and Navigate

```bash
git clone https://github.com/Danush-k/attendance_management_system.git
cd attendance_management_system
```

### Step 2: Install Dependencies

```bash
pip install -e .
```

Or using the project configuration:

```bash
pip install -r requirements.txt
```

### Step 3: Environment Configuration

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/attendance_db
# For SQLite: DATABASE_URL=sqlite:///attendance.db

# Flask
SESSION_SECRET=your-secure-secret-key-here
FLASK_ENV=development

# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@institution.edu
```

### Step 4: Database Initialization

```bash
# Create database
flask db init

# Create initial migration
flask db migrate -m "Initial migration"

# Apply migrations
flask db upgrade
```

### Step 5: Create Admin/Faculty Users

Run the user injection script:

```bash
python inject_user.py
```

### Step 6: Register Routers

Use `add_router.py` to register classroom routers:

```bash
python add_router.py
```

### Step 7: Run the Application

```bash
python main.py
```

The application will be available at: `http://localhost:5005`

## 📱 Usage Guide

### For Students

1. **Login**: Access the system with student credentials
2. **View Dashboard**: See courses and attendance records
3. **Mark Attendance**: 
   - Navigate to "Mark Attendance"
   - Verify WiFi router connection for location validation
   - Enter OTP received
   - Submit attendance
4. **Request Leave**: Submit and track leave requests
5. **View Attendance**: Monitor personal attendance percentage

### For Faculty

1. **Login**: Access with faculty credentials
2. **Manage Courses**: Create and manage course rosters
3. **Assign Routers**: Designate classroom routers for each course
4. **Create Sessions**: Initiate attendance sessions for classes
5. **Generate OTP**: System generates OTP for each session
6. **View Reports**: Detailed attendance analytics and reports
7. **Manage Leaves**: Approve or reject student leave requests

## 🔄 Attendance Workflow

```
1. Faculty creates attendance session for a course
   ↓
2. System generates OTP and validates session router
   ↓
3. Student connects to classroom WiFi router
   ↓
4. Student enters session OTP
   ↓
5. System verifies:
   - Student router matches course router
   - OTP is correct
   - Session is active
   ↓
6. Attendance marked successfully
   ↓
7. System calculates attendance percentage
   ↓
8. Low attendance warning email sent (if <75%)
```

## � System Diagrams

### Architecture Diagram

This diagram illustrates the complete system architecture with all components and their interactions:

![Attendance Management System Architecture](docs/diagrams/architecture-diagram.png)

**Components:**
- **Frontend**: Student and Staff interfaces (HTML/CSS/JavaScript)
- **Attendance Management System**: Core application logic (Flask)
- **Database**: Stores login credentials, student data, attendance records, and router IDs
- **Backend Services**: Router detection and location-based verification
- **OTP & Fingerprint Verification**: Security mechanisms for authentication
- **WiFi Router**: Physical location detection for proxy elimination

### Sequence Diagram

This sequence diagram shows the step-by-step attendance marking process:

![Attendance Process Sequence Diagram](docs/diagrams/sequence-diagram.png)

**Flow:**
1. **Staff/Faculty Authentication**: Faculty member initiates attendance session
2. **Student Verification**: System identifies the student
3. **OTP & Fingerprint Verification**: Multi-layer security validation
   - OTP verification
   - Router location verification
4. **Successful/Failed Verification**: System processes verification result
5. **Database Update**: Attendance data persisted to database
6. **Reflection**: Updates reflected on both student and faculty dashboards

## �📈 Key Utilities

### OTP Generation
```python
from utils import generate_otp
otp = generate_otp(length=6)  # Generates 6-character alphanumeric OTP
```

### Router Location Validation
```python
from utils import validate_router_location
is_valid = validate_router_location(router_id, course_router_id)
```

### Attendance Calculation
```python
from utils import calculate_attendance_percentage
percentage = calculate_attendance_percentage(present_count=15, total_sessions=20)
```

## 🔔 Email Notifications

The system sends automated emails for:

- **Low Attendance Alerts**: Notifies students when attendance drops below 75%
- **Leave Request Status**: Confirms receipt and approval/rejection of leave requests
- **Password Reset**: Secure password reset links with time-limited tokens

## 📊 Database Schema

The system uses the following key tables:

| Table | Purpose |
|-------|---------|
| `user` | User accounts and authentication |
| `student` | Student profile information |
| `faculty` | Faculty profile and assignments |
| `course` | Course details and enrollment |
| `router` | WiFi router registration |
| `attendance` | Attendance records |
| `leave_request` | Leave application records |
| `student_course` | Student-course enrollment mapping |

## 🛠️ Development

### Adding New Features

1. Update data models in `models.py`
2. Create migration: `flask db migrate -m "description"`
3. Update forms in `forms.py`
4. Add routes in `app.py`
5. Create/update templates in `templates/`

### Running Migrations

```bash
# Create a migration
flask db migrate -m "Add new column"

# Apply migration
flask db upgrade

# Rollback migration
flask db downgrade
```

## 📝 API Endpoints

### Authentication
- `POST /login` - User login
- `POST /logout` - User logout
- `GET /forgot_password` - Password reset request
- `POST /reset_password/<token>` - Reset password

### Student Routes
- `GET /student/dashboard` - Student dashboard
- `GET /student/mark_attendance` - Mark attendance page
- `POST /mark_attendance` - Submit attendance
- `GET /student/attendance` - View attendance records
- `GET /student/leave_request` - Request leave

### Faculty Routes
- `GET /faculty/dashboard` - Faculty dashboard
- `GET /faculty/manage_courses` - Course management
- `GET /faculty/manage_students` - Student roster
- `POST /faculty/generate_otp` - Generate attendance OTP
- `GET /faculty/attendance_report` - Attendance analytics

## ⚙️ Configuration

### Flask Configuration

Key configurations in `app.py`:

- **Session Secret**: Change `SESSION_SECRET` for production
- **Database Pool**: Connection pooling with 300-second recycle time
- **Login Timeout**: Configure session expiry
- **Mail Settings**: SMTP configuration for notifications

### Production Deployment

For production deployment:

1. Set `FLASK_ENV=production`
2. Use strong `SESSION_SECRET`
3. Configure PostgreSQL database
4. Set up SMTP credentials
5. Use Gunicorn with reverse proxy (Nginx)
6. Enable HTTPS/SSL
7. Configure firewall rules

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Database connection error | Verify `DATABASE_URL` in `.env` |
| Email not sending | Check SMTP credentials and `MAIL_SERVER` |
| Router validation fails | Ensure router MAC address is correctly registered |
| OTP not received | Verify email configuration |
| Migration errors | Delete `__pycache__` and migrations, run `flask db init` |

## 👥 Contributing

Guidelines for contributing to this project:

1. Create a feature branch
2. Commit changes with clear messages
3. Submit a pull request
4. Ensure all tests pass

## 📞 Support

For support or inquiries, contact the development team or system administrator.

## 🔄 Version History

- **v1.0** - Initial release with core features
  - User authentication system
  - Router-based location detection
  - Basic attendance tracking
  - Leave management

---

**Last Updated**: May 2026  
**Maintainer**: Danush
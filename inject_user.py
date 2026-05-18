from app import app, db  # Import your Flask app and db instance from app.py
from models import User, Student, Faculty  # Import your models (assuming they're in models.py)
from werkzeug.security import generate_password_hash  # For hashing the password

def add_user(first_name, last_name, email, password, role, student_id=None, faculty_id=None, department=None, year=None, designation=None, phone=None):
    # Check if the user already exists
    if User.query.filter_by(email=email).first():
        print(f"User with email {email} already exists!")
        return

    # Create a new user with pbkdf2:sha256 hashing method
    new_user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=generate_password_hash(password, method='pbkdf2:sha256'),
        role=role
    )
    
    # Add the user to the session
    db.session.add(new_user)
    db.session.flush()  # Flush to get the user ID before committing

    # If the role is 'student', create a Student record
    if role == 'student':
        if not student_id or not department or not year:
            print("Student ID, department, and year are required for a student!")
            db.session.rollback()
            return
        
        new_student = Student(
            user_id=new_user.id,
            student_id=student_id,
            department=department,
            year=year,
            phone=phone
        )
        db.session.add(new_student)

    # If the role is 'faculty', create a Faculty record
    elif role == 'faculty':
        if not faculty_id or not department:
            print("Faculty ID and department are required for a faculty member!")
            db.session.rollback()
            return
        
        new_faculty = Faculty(
            user_id=new_user.id,
            faculty_id=faculty_id,
            department=department,
            designation=designation,
            phone=phone
        )
        db.session.add(new_faculty)

    # Commit the transaction
    try:
        db.session.commit()
        print(f"User {email} added successfully as a {role}!")
    except Exception as e:
        db.session.rollback()
        print(f"Error adding user: {str(e)}")

# Example usage
if __name__ == "__main__":
    with app.app_context():  # Ensure the script runs within the Flask app context
        # Print all table names to confirm database setup
        print("Database tables created:", db.Model.metadata.tables.keys())
        
        # Add a student
        add_user(
            first_name="sugith",
            last_name="Marini",
            email="sugith@gmail.com",
            password="123456789",
            role="student",
            student_id="STU005",
            department="Computer Science",
            year=2,
            phone="6380164344"
        )

        # # Add a faculty member
        # add_user(
        #     first_name="vishnu",
        #     last_name="vineeth",
        #     email="vishnu@gmail.com",
        #     password="123456789",
        #     role="faculty",
        #     faculty_id="FAC004",
        #     department="Mathematics",
        #     designation="Professor",
        #     phone="9994307887"
        # )

        
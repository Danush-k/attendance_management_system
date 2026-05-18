import socket
from database import db
from models import Router

def get_current_ip_address():
    """Retrieve the IP address of the currently connected network."""
    try:
        # Create a socket and connect to a public server to get the local IP address
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
        return ip_address
    except Exception as e:
        return "Unknown"  # Fallback if unable to retrieve IP address

def get_current_gateway_ip():
    """
    Attempt to get the default gateway IP address of the currently connected Wi-Fi.
    This works on Linux/macOS. For Windows, you may need to use a different method.
    """
    import os
    import platform
    import re

    system = platform.system()
    gateway_ip = None

    if system == "Linux" or system == "Darwin":
        try:
            # Use netstat to get the default gateway
            output = os.popen("netstat -rn | grep default").read()
            match = re.search(r'default\s+([\d\.]+)', output)
            if match:
                gateway_ip = match.group(1)
        except Exception:
            pass
    elif system == "Windows":
        try:
            output = os.popen("ipconfig").read()
            match = re.search(r"Default Gateway[ .:]*([\d\.]+)", output)
            if match:
                gateway_ip = match.group(1)
        except Exception:
            pass

    return gateway_ip or "Unknown"

def add_router(name, location, ip_address=None):
    """Add a router to the database with the given name and location."""
    # Check if the router already exists by name
    if Router.query.filter_by(name=name).first():
        return False, f"Router with name '{name}' already exists!"

    # Use the provided IP address (or MAC address) as entered in the form
    new_router = Router(
        name=name,
        location=location,
        mac_address=ip_address
    )

    # Add to the session and commit
    try:
        db.session.add(new_router)
        db.session.flush()  # Flush to get the router ID before committing
        router_id = new_router.id  # Retrieve the assigned router ID
        db.session.commit()
        return True, f"Router '{name}' at '{location}' added successfully with ID {router_id}!"
    except Exception as e:
        db.session.rollback()
        return False, f"Error adding router: {str(e)}"
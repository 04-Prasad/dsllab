import sys
import getpass
from pathlib import Path

# Add root project directory to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.db.database import SessionLocal, engine, Base
from backend.app.models.models import User
from backend.app.core.security import get_password_hash

def main():
    print("GraphGuard Admin User Bootstrap")
    print("-" * 30)
    
    # Ensure tables are created
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        email = input("Admin Email: ").strip()
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"Error: User with email {email} already exists!")
            sys.exit(1)
            
        full_name = input("Admin Full Name: ").strip()
        
        while True:
            password = getpass.getpass("Password: ")
            confirm = getpass.getpass("Confirm Password: ")
            if password == confirm and len(password) >= 8:
                break
            print("Passwords do not match or are too short (min 8 chars). Try again.")
            
        new_admin = User(
            email=email,
            full_name=full_name,
            password_hash=get_password_hash(password),
            role="ADMIN",
            is_active=1
        )
        
        db.add(new_admin)
        db.commit()
        print("\nSuccess! Admin user created securely.")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()

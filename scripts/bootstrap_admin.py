import asyncio
import argparse
import getpass
import sys
import uuid
from datetime import datetime, timezone

# Add parent directory to path so we can import gateway modules
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "gateway")))

from utils.db import init_db, PrimarySession
from models import User
from middleware.security.auth import get_password_hash
from sqlalchemy import select

async def main():
    parser = argparse.ArgumentParser(description="Bootstrap the initial Argus admin user.")
    parser.add_argument("--username", required=True, help="Admin username")
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--force", action="store_true", help="Create even if admins exist")
    
    args = parser.parse_args()
    
    await init_db()
    
    async with PrimarySession() as session:
        # Check if an admin already exists
        if not args.force:
            stmt = select(User).where(User.role == "admin")
            res = await session.execute(stmt)
            existing_admin = res.scalars().first()
            if existing_admin:
                print(f"Error: An admin user ({existing_admin.username}) already exists.")
                print("Use --force to create another admin.")
                sys.exit(1)
        
        # Check if username or email is already taken
        stmt = select(User).where((User.username == args.username) | (User.email == args.email))
        res = await session.execute(stmt)
        if res.scalars().first():
            print(f"Error: User with username '{args.username}' or email '{args.email}' already exists.")
            sys.exit(1)
            
        password = getpass.getpass(prompt=f"Enter password for admin {args.username}: ")
        confirm = getpass.getpass(prompt="Confirm password: ")
        
        if password != confirm:
            print("Error: Passwords do not match.")
            sys.exit(1)
            
        if len(password) < 12:
            print("Warning: Password should ideally be at least 12 characters long.")
            
        hashed_pw = get_password_hash(password)
        
        admin_user = User(
            id=uuid.uuid4(),
            username=args.username,
            email=args.email,
            hashed_password=hashed_pw,
            role="admin",
            is_active=True,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        
        session.add(admin_user)
        await session.commit()
        
        print(f"\nSuccess! Admin user '{args.username}' has been bootstrapped.")
        print("You can now log in to the Argus Gateway with these credentials.")

if __name__ == "__main__":
    asyncio.run(main())

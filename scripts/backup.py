import os
import subprocess
import datetime
import sys

def main():
    print("Argus Backup Utility")
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL environment variable is required.")
        sys.exit(1)
        
    # Replace asyncpg dialect with standard postgresql for pg_dump
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"argus_backup_{timestamp}.sql"
    
    print(f"Starting backup of Argus database to {backup_file}...")
    
    try:
        # We use pg_dump which needs to be installed on the system running this script
        cmd = ["pg_dump", "--dbname", db_url, "-F", "c", "-f", backup_file]
        subprocess.run(cmd, check=True)
        print(f"✅ Backup successfully written to {backup_file}")
    except FileNotFoundError:
        print("❌ Error: pg_dump utility not found. Please install PostgreSQL client tools.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"❌ Backup failed with error code {e.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    main()

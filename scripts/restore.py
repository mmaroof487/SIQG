import os
import subprocess
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Argus Restore Utility")
    parser.add_argument("backup_file", help="Path to the backup file (.sql custom format)")
    parser.add_argument("--clean", action="store_true", help="Clean (drop) database objects before recreating")
    args = parser.parse_args()
    
    print("Argus Restore Utility")
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL environment variable is required.")
        sys.exit(1)
        
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        
    if not os.path.exists(args.backup_file):
        print(f"Error: Backup file {args.backup_file} not found.")
        sys.exit(1)
        
    print(f"Restoring Argus database from {args.backup_file}...")
    print("⚠️ WARNING: This may overwrite existing data!")
    confirm = input("Are you sure you want to proceed? (y/N): ")
    if confirm.lower() != 'y':
        print("Restore cancelled.")
        sys.exit(0)
    
    try:
        cmd = ["pg_restore", "--dbname", db_url]
        if args.clean:
            cmd.append("--clean")
        cmd.append(args.backup_file)
        
        subprocess.run(cmd, check=True)
        print(f"✅ Restore successfully completed.")
    except FileNotFoundError:
        print("❌ Error: pg_restore utility not found. Please install PostgreSQL client tools.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"❌ Restore failed with error code {e.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    main()

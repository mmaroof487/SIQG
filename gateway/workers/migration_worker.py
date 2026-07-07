import asyncio
import traceback
from sqlalchemy import select
from utils.db import PrimarySession
from models.migration_job import MigrationJob
from models.user_database import UserDatabase
from models.dek_history import DEKHistory
from utils.connection_manager import get_connection_column_map
from middleware.security.encryption import decrypt_value
import asyncpg
from middleware.security.key_manager import key_manager
from middleware.security.query_encryptor import _aes_decrypt, _aes_encrypt
from utils.logger import get_logger

logger = get_logger(__name__)


async def trigger_reencryption_job(connection_id: str, old_version: int, new_version: int):
    """
    Creates a MigrationJob and spawns a background asyncio task to process it.
    """
    async with PrimarySession() as session:
        job = MigrationJob(
            database_id=connection_id,
            old_key_version=old_version,
            new_key_version=new_version,
            status="pending"
        )
        session.add(job)
        await session.commit()
        job_id = job.id
        
    asyncio.create_task(_process_job(job_id))
    return job_id


async def _process_job(job_id: str):
    logger.info(f"Starting background migration job: {job_id}")
    try:
        async with PrimarySession() as session:
            job = await session.get(MigrationJob, job_id)
            if not job or job.status != "pending":
                return
            
            job.status = "in_progress"
            await session.commit()
            
            conn = await session.get(UserDatabase, job.database_id)
            
            # Fetch new DEK
            new_dek = await key_manager.get_dek(str(conn.id), conn.key_version, conn.encrypted_dek)
            
            # Fetch old DEK from history
            hist_stmt = select(DEKHistory).where(
                DEKHistory.database_id == str(conn.id),
                DEKHistory.key_version == job.old_key_version
            )
            hist_res = await session.execute(hist_stmt)
            history_entry = hist_res.scalars().first()
            if not history_entry:
                raise ValueError(f"Could not find old DEK version {job.old_key_version} in history")
            
            old_dek = await key_manager.get_dek(str(conn.id), history_entry.key_version, history_entry.encrypted_dek)
            
            # Fetch column map
            col_map = await get_connection_column_map(session, str(conn.id))
            
            # Decrypt connection string using new dek (since it was re-encrypted in the rotate_key endpoint)
            plain_conn_str = decrypt_value(conn.conn_str_enc, new_dek)
            
            total_processed = 0
            
            if col_map:
                external_conn = await asyncio.wait_for(asyncpg.connect(plain_conn_str), timeout=10)
                try:
                    for table_name, cols in col_map.items():
                        # Discover Primary Key
                        pk_query = f"""
                        SELECT a.attname
                        FROM   pg_index i
                        JOIN   pg_attribute a ON a.attrelid = i.indrelid
                                            AND a.attnum = ANY(i.indkey)
                        WHERE  i.indrelid = '{table_name}'::regclass
                        AND    i.indisprimary;
                        """
                        try:
                            pk_col = await external_conn.fetchval(pk_query)
                        except Exception:
                            logger.warning(f"Table {table_name} not found or no PK in external DB")
                            continue
                            
                        if not pk_col:
                            logger.warning(f"No primary key found for {table_name}. Skipping re-encryption.")
                            continue
                            
                        cols_str = ", ".join(cols)
                        select_query = f"SELECT {pk_col}, {cols_str} FROM {table_name}"
                        rows = await external_conn.fetch(select_query)
                        
                        for row in rows:
                            pk_val = row[pk_col]
                            update_cols = []
                            update_vals = []
                            for col in cols:
                                val = row[col]
                                if val and isinstance(val, str) and (val.startswith("v1:") or val.startswith("v2:")):
                                    try:
                                        decrypted = _aes_decrypt(val, old_dek)
                                        encrypted = _aes_encrypt(decrypted, new_dek, conn.key_version)
                                        update_cols.append(col)
                                        update_vals.append(encrypted)
                                    except Exception as e:
                                        logger.error(f"Failed to decrypt/encrypt {col} for PK {pk_val}: {e}")
                            
                            if update_cols:
                                set_clause = ", ".join([f"{col} = ${i+1}" for i, col in enumerate(update_cols)])
                                update_query = f"UPDATE {table_name} SET {set_clause} WHERE {pk_col} = ${len(update_cols)+1}"
                                await external_conn.execute(update_query, *update_vals, pk_val)
                                total_processed += 1
                finally:
                    await external_conn.close()
            
            job.status = "completed"
            job.processed_records = total_processed
            await session.commit()
            logger.info(f"Successfully completed background migration job: {job_id}")
            
    except Exception as e:
        logger.error(f"Migration job {job_id} failed: {e}\n{traceback.format_exc()}")
        async with PrimarySession() as session:
            job = await session.get(MigrationJob, job_id)
            if job:
                job.status = "failed"
                job.error_message = str(e)
                await session.commit()

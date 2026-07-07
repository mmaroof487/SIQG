import base64
import os
import sys
sys.path.append("c:\\Users\\mmuaz\\Desktop\\Projects\\siqg\\gateway")

from middleware.security.query_encryptor import QueryEncryptor, _aes_encrypt

dek = os.urandom(32)
enc = QueryEncryptor(dek=dek, key_version=1, encrypted_columns={"clients": {"email"}})
sql = "INSERT INTO clients (name, email) VALUES ('Encryption Test', 'topsecret@email.com');"
print("Original:", sql)
rewritten = enc.encrypt_query(sql)
print("Rewritten:", rewritten)

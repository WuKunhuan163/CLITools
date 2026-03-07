---
name: encryption-hashing
description: Encryption, hashing, and cryptographic best practices. Use when working with encryption hashing concepts or setting up related projects.
---

# Encryption & Hashing

## Key Concepts

### Hashing (One-Way, for passwords/integrity)
```python
import bcrypt

# Hash password
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

# Verify
if bcrypt.checkpw(password.encode(), hashed):
    print("Match!")
```
Use: bcrypt, argon2 for passwords; SHA-256 for integrity checks

### Symmetric Encryption (Same key for encrypt/decrypt)
```python
from cryptography.fernet import Fernet

key = Fernet.generate_key()
cipher = Fernet(key)
encrypted = cipher.encrypt(b"secret data")
decrypted = cipher.decrypt(encrypted)
```
Use: AES-256-GCM for data at rest

### Asymmetric Encryption (Public/Private key pair)
Use: RSA/ECDSA for key exchange, digital signatures, TLS

## Best Practices
- Never roll your own cryptography
- Use bcrypt/argon2 for passwords (not MD5, SHA1, or plain SHA256)
- Generate random keys with `secrets` module (not `random`)
- Rotate encryption keys periodically
- Store keys in secret managers (not in code)
- Use TLS 1.3 for data in transit

## Common Mistakes
- Using ECB mode for AES (use GCM or CBC with HMAC)
- Hardcoding encryption keys in source code
- Using `random` instead of `secrets` for security-sensitive values
- Comparing hashes with `==` instead of constant-time comparison

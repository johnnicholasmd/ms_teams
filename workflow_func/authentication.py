import jwt
from datetime import datetime, timedelta, timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import load_pem_x509_certificate

# --- constants ---
TOKEN_EXPIRE_MINUTES = 30
ALGORITHM = 'RS256'
#-------

def generate_jwt(temp_id):
    now = datetime.now(timezone.utc)
    payload = {
        'sub': temp_id,
        "iat": now,
        "exp": (now + timedelta(minutes=TOKEN_EXPIRE_MINUTES)).timestamp(),
    }

    private_key_text = Path('private_key.pem').read_text()
    private_key = serialization.load_pem_private_key(
        private_key_text.encode(),
        password=None
    )

    return jwt.encode(payload=payload, key=private_key, algorithm=ALGORITHM)


def decode_and_validate_token(token):
    unverified_headers = jwt.get_unverified_header(token)
    x509_certificate = load_pem_x509_certificate(
        Path('public_key.pem').read_text().encode()
    ).public_key()
    return jwt.decode(
        token,
        key=x509_certificate,
        algorithms=unverified_headers["alg"],
    )

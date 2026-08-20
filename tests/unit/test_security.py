import base64
import os

from voice_evals_api.security import SecretCipher, digest_token, hash_password, verify_password


def test_password_hash_and_token_digest_do_not_expose_secret() -> None:
    password = "very-secret-password"
    encoded = hash_password(password)
    assert password not in encoded
    assert verify_password(password, encoded)
    assert not verify_password("wrong-password", encoded)
    assert digest_token(password) != password


def test_secret_cipher_round_trip() -> None:
    key = base64.urlsafe_b64encode(os.urandom(32)).decode()
    cipher = SecretCipher(key)
    ciphertext = cipher.encrypt("provider-key")
    assert "provider-key" not in ciphertext
    assert cipher.decrypt(ciphertext) == "provider-key"

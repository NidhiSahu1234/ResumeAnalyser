import sqlite3
import base64
import hashlib

from config import database
from config.admin_auth import hash_password, verify_password


def test_password_hash_is_salted_and_verifiable():
    first = hash_password("correct horse battery staple")
    second = hash_password("correct horse battery staple")

    assert first.startswith("pbkdf2_sha256$")
    assert first != second
    assert verify_password("correct horse battery staple", first) == (True, False)
    assert verify_password("incorrect", first) == (False, False)


def test_legacy_plaintext_password_is_marked_for_upgrade():
    assert verify_password("legacy-password", "legacy-password") == (True, True)
    assert verify_password("wrong-password", "legacy-password") == (False, True)


def test_malformed_password_hash_fails_closed():
    assert verify_password("password", "pbkdf2_sha256$900000000$bad$bad") == (False, False)


def test_valid_hash_with_an_older_work_factor_requests_upgrade():
    salt = b"test-salt"
    digest = hashlib.pbkdf2_hmac("sha256", b"password", salt, 10_000)
    encode = lambda value: base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
    stored = f"pbkdf2_sha256$10000${encode(salt)}${encode(digest)}"

    assert verify_password("password", stored) == (True, True)


def test_successful_legacy_admin_login_migrates_password(monkeypatch, tmp_path):
    db_path = tmp_path / "admin-test.db"
    connection = sqlite3.connect(db_path)
    connection.execute("CREATE TABLE admin (id INTEGER PRIMARY KEY, email TEXT, password TEXT)")
    connection.execute("INSERT INTO admin (email, password) VALUES (?, ?)",
                       ("admin@example.test", "legacy-password"))
    connection.commit()
    connection.close()
    monkeypatch.setattr(database, "get_database_connection", lambda: sqlite3.connect(db_path))

    assert database.verify_admin("admin@example.test", "legacy-password") is True
    with sqlite3.connect(db_path) as migrated:
        stored = migrated.execute("SELECT password FROM admin WHERE email = ?",
                                  ("admin@example.test",)).fetchone()[0]
    assert stored.startswith("pbkdf2_sha256$")
    assert stored != "legacy-password"


def test_new_admin_password_is_hashed(monkeypatch, tmp_path):
    db_path = tmp_path / "admin-create-test.db"
    connection = sqlite3.connect(db_path)
    connection.execute("CREATE TABLE admin (id INTEGER PRIMARY KEY, email TEXT, password TEXT)")
    connection.commit()
    connection.close()
    monkeypatch.setattr(database, "get_database_connection", lambda: sqlite3.connect(db_path))

    assert database.add_admin("admin@example.test", "new-password") is True
    with sqlite3.connect(db_path) as migrated:
        stored = migrated.execute("SELECT password FROM admin WHERE email = ?",
                                  ("admin@example.test",)).fetchone()[0]
    assert stored.startswith("pbkdf2_sha256$")
    assert stored != "new-password"

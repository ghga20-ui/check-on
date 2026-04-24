import win32crypt

def test_dpapi_roundtrip():
    """DPAPI 암호화 → 복호화 왕복 테스트"""
    original = "test_password_123!@#"
    encrypted = win32crypt.CryptProtectData(original.encode('utf-8'))
    _, decrypted = win32crypt.CryptUnprotectData(encrypted)
    assert decrypted.decode('utf-8') == original

def test_dpapi_empty_password():
    """빈 비밀번호도 정상 처리"""
    original = ""
    encrypted = win32crypt.CryptProtectData(original.encode('utf-8'))
    _, decrypted = win32crypt.CryptUnprotectData(encrypted)
    assert decrypted.decode('utf-8') == original

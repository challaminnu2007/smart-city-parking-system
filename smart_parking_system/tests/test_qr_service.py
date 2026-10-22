from services.qr_service import QRService


def test_generate_verification_token():
    token = QRService.generate_verification_token(
        "BOOK123", "test-secret"
    )

    assert isinstance(token, str)
    assert len(token) == 24


def test_same_booking_same_token():
    token1 = QRService.generate_verification_token(
        "BOOK123", "test-secret"
    )
    token2 = QRService.generate_verification_token(
        "BOOK123", "test-secret"
    )

    assert token1 == token2


def test_different_booking_different_token():
    token1 = QRService.generate_verification_token(
        "BOOK123", "test-secret"
    )
    token2 = QRService.generate_verification_token(
        "BOOK456", "test-secret"
    )

    assert token1 != token2


def test_different_secret_different_token():
    token1 = QRService.generate_verification_token(
        "BOOK123", "secret-one"
    )
    token2 = QRService.generate_verification_token(
        "BOOK123", "secret-two"
    )

    assert token1 != token2
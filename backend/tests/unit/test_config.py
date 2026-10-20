import pytest

from app.core.config import Settings


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        (
            "postgresql://u:p@host/db?sslmode=require",
            "postgresql+psycopg://u:p@host/db?sslmode=require",
        ),
        ("postgres://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
    ],
)
def test_database_url_is_normalised_to_the_psycopg_driver(given, expected):
    assert Settings(database_url=given).database_url == expected


def test_cors_origins_are_split_and_trimmed():
    settings = Settings(
        database_url="postgresql://u:p@h/d",
        cors_origins=" https://a.example , https://b.example ,",
    )
    assert settings.cors_origin_list == ["https://a.example", "https://b.example"]

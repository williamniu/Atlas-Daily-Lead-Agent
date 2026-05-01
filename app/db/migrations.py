"""MVP database migration command."""

from app.db.database import init_db


def main() -> None:
    """Initialize database tables for the MVP."""
    init_db()
    print("Database tables initialized.")


if __name__ == "__main__":
    main()

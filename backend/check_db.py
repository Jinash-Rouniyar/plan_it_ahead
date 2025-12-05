from dotenv import load_dotenv
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, text

load_dotenv()  # loads backend/.env
db_url = os.environ.get('DATABASE_URL')

if not db_url:
    print('DATABASE_URL not set. Check .env file or environment variables.')
else:
    print('Using DB URL (masked):', (db_url[:60] + '...') if len(db_url) > 60 else db_url)
    try:
        engine = create_engine(db_url, future=True)
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema')")).fetchall()
            print('Tables in DB:', [r[0] for r in rows])
    except Exception as e:
        print('Connection error:', e)

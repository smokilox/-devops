from dotenv import load_dotenv

from app.db import Base, engine

def main():
    load_dotenv()
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")

if __name__ == "__main__":
    main()

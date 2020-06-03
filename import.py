import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

# Open CSV
csv_file = open("books.csv")
csv_reader = csv.reader(csv_file)

# Move to second line as first line is unnecessary
next(csv_reader)

# Write each line from CSV into database
for isbn, title, author, year in csv_reader:
    db.execute("""
        INSERT INTO books (isbn, title, author, year) 
        VALUES (:isbn, :title, :author, :year)""", 
        {"isbn": isbn, "title": title, "author": author, "year": year})
db.commit()

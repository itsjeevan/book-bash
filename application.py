import config
import hashlib
import uuid
import os
import requests

from flask import Flask, session, render_template, request, redirect, url_for, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)
key = config.key

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


# Login or Register
@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "GET":
        # Check if a user session exists
        if session.get("user_username") is not None:
            return redirect("/search")
        else:
            return render_template("login.html")

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Redirect if missing fields
        if username == "" or password == "":
            return redirect("/")

        # Get user's data from table
        user = db.execute("""
            SELECT * FROM users WHERE username = :username""",
            {"username": username}).fetchone()

        # If Login button pressed
        if request.form.get("button") == "login":
        
            # If user was found in table, match credentials, else redirect
            if user is not None:
                hashed_password = hashlib.sha256((password + user.salt).encode('utf-8')).hexdigest()
                if hashed_password == user.password:
                    session["user_username"] = user.username
                    return redirect("/search")
            return redirect("/")

        # If Register button pressed
        elif request.form.get("button") == "register":
            
            # Register user if no user was found in table
            if user is None:

                # Create salt, hash password and insert into table
                salt = uuid.uuid4().hex
                hashed_password = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
                db.execute("""
                    INSERT INTO users (username, password, salt) VALUES (:username, :password, :salt)""",
                    {"username": username, "password": hashed_password, "salt": salt})
                db.commit()
                
                # Set user session
                session["user_username"] = username

                return redirect("/search")

            # User already exists
            else:
                return redirect("/")


# Search for a book
@app.route("/search")
def search():

    # User session exists
    if session.get("user_username") is not None:
        
        results = request.args.get("results")

        if results is None:
            books = "Start searching!"
        
        elif not results:
            books = "No results found"

        elif request.args.get("category") == "isbn":
            books = db.execute("""
                SELECT * FROM books WHERE isbn ILIKE '%' || :isbn || '%'""", 
                {"isbn": results}).fetchall()

        elif request.args.get("category") == "author":
            books = db.execute("""
                SELECT * FROM books WHERE author ILIKE '%' || :author || '%'""", 
                {"author": results}).fetchall()


        elif request.args.get("category") == "title":
            books = db.execute("""
                SELECT * FROM books WHERE title ILIKE '%' || :title || '%'""", 
                {"title": results}).fetchall()

        return render_template("search.html", books = books)

    # Redirect if no user session exists
    else:
        return redirect("/")


# View details of a book   
@app.route("/book/<string:isbn>", methods=["GET", "POST"])
def book(isbn):

    # Get JSON from Goodreads
    res = requests.get("""
        https://www.goodreads.com/book/review_counts.json""", 
        params={"key": key, "isbns": isbn})
    
    # Check status code
    if res.status_code != 200:
        return redirect("/")
    
    # Parse JSON and retrieve values
    res = res.json()
    review_count = res["books"][0]["work_ratings_count"]
    average_rating = res["books"][0]["average_rating"]

    # Retrieve book info from ISBN
    book = db.execute("""
        SELECT * FROM books WHERE isbn = :isbn""",
        {"isbn": isbn}).fetchone()

    # Retrieve review info for book
    reviews = db.execute("""
        SELECT * FROM reviews WHERE book_isbn = :book_isbn ORDER BY id DESC""",
        {"book_isbn": book.isbn}).fetchall()


    # If user is logged in
    if session.get("user_username") is not None:

        if request.method == "POST":

            # Check if user has reviewed this book
            if db.execute("""
                SELECT * FROM reviews WHERE book_isbn = :book_isbn AND user_username = :user_username""",
                {"book_isbn": isbn, "user_username": session["user_username"]}).rowcount > 0:
                
                return redirect("/")

            # Store review in table
            review = request.form.get("review")
            rating = request.form.get("rating")
            db.execute("""
                INSERT INTO reviews (book_isbn, user_username, review, rating) 
                VALUES (:book_isbn, :user_username, :review, :rating)""", {
                "book_isbn": book.isbn, 
                "user_username": session["user_username"], 
                "review": review, 
                "rating": rating})
            db.commit()

            # Query for updated reviews
            reviews = db.execute("""
                SELECT * FROM reviews WHERE book_isbn = :book_isbn ORDER BY id DESC""",
                {"book_isbn": book.isbn}).fetchall()

        return render_template("book.html", 
            book = book, 
            reviews = reviews, 
            review_count = review_count, 
            average_rating = average_rating)

    # Redirect if user not logged in
    else:
        return redirect("/")


# API for book with reviews & ratings
@app.route("/api/<string:isbn>")
def api(isbn):

    # Select book using ISBN from table
    book = db.execute("""
        SELECT * FROM books WHERE isbn = :isbn""",
        {"isbn": isbn}).fetchone()
    
    # If no book found, return 404
    if book is None:
        return jsonify({
            "Error": "No book found with that ISBN."
        }), 404

    # Collect reviews for book
    review = db.execute("""
        SELECT COUNT(*), AVG(rating) FROM reviews WHERE book_isbn = :book_isbn""",
        {"book_isbn": isbn}).fetchone()
    
    # Set values for rating and review count
    if review[0] == 0:
        average_rating = "N/A"
        review_count = review[0]
    else:
        average_rating = float(round(review[1], 2))
        review_count = review[0]

    # Return data as JSON
    return jsonify({
        "author": book.author,
        "average_rating": average_rating,
        "isbn": book.isbn,
        "review_count": review_count,
        "title": book.title,
        "year": book.year
    })

# Logout user
@app.route("/logout")
def logout():
    
    # Clear user's session and redirect
    session.clear()
    return redirect("/")

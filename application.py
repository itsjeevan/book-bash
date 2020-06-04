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

@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "GET":
        if session.get("user_username") is not None:
            return redirect("/search")
        else:
            return render_template("login.html")

    if request.method == "POST":
        
        username = request.form.get("username")
        password = request.form.get("password")

        # Redirect if missing fields
        if username == "" or password == "":
            print("Missing fields")
            return redirect("/")

        user = db.execute("""
            SELECT * FROM users WHERE username = :username""",
            {"username": username}).fetchone()

        # If Login button pressed
        if request.form["button"] == "login":

            if user is not None:
                hashed_password = hashlib.sha256((password + user.salt).encode('utf-8')).hexdigest()
                if hashed_password == user.password:
                    session["user_username"] = user.username
                    return redirect("/search")

            print("Username or password incorrect")
            return redirect("/")

        # If Register button pressed
        elif request.form["button"] == "register":
            
            # Register user
            if user is None:

                salt = uuid.uuid4().hex
                hashed_password = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

                db.execute("""
                    INSERT INTO users (username, password, salt) VALUES (:username, :password, :salt)""",
                    {"username": username, "password": hashed_password, "salt": salt})
                db.commit()
                

                user = db.execute("""
                    SELECT id FROM users WHERE username = :username""",
                    {"username": username}).fetchone()

                session["user_username"] = user.username

                print("Registered user")
                return redirect("/search")

            # User already exists
            else:
                print("User already exists")
                return redirect("/")


@app.route("/search")
def search():
    # User successfully logged in
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

        return render_template("search.html", books=books)

    # Accessing a route without login
    else:
        return redirect("/")
    
@app.route("/book/<string:isbn>", methods=["GET", "POST"])
def book(isbn):

    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": key, "isbns": isbn})
    
    if res.status_code != 200:
        return redirect("/search")

    res = res.json()
    review_count = res["books"][0]["work_ratings_count"]
    average_rating = res["books"][0]["average_rating"]

    book = db.execute("""
        SELECT * FROM books WHERE isbn = :isbn""",
        {"isbn": isbn}).fetchone()

    reviews = db.execute("""
        SELECT * FROM reviews WHERE book_isbn = :book_isbn ORDER BY id DESC""",
        {"book_isbn": book.isbn}).fetchall()

    if request.method == "GET" and session.get("user_username") is not None:
        return render_template("book.html", book=book, reviews=reviews, review_count=review_count, average_rating=average_rating)

    elif request.method == "POST" and session.get("user_username") is not None:
        review = request.form.get("review")
        rating = request.form.get("rating")

        db.execute("""
            INSERT INTO reviews (book_isbn, user_username, review, rating) 
            VALUES (:book_isbn, :user_username, :review, :rating)""",
            {"book_isbn": book.isbn, "user_username": session["user_username"], "review": review, "rating": rating})
        db.commit()

        reviews = db.execute("""
            SELECT * FROM reviews WHERE book_isbn = :book_isbn ORDER BY id DESC""",
            {"book_isbn": book.isbn}).fetchall()

        return render_template("book.html", book=book, reviews=reviews, review_count=review_count, average_rating=average_rating)

    else:
        return redirect("/")

@app.route("/api/<string:isbn>")
def api(isbn):

    book = db.execute("""
        SELECT * FROM books WHERE isbn = :isbn""",
        {"isbn": isbn}).fetchone()
    
    if book is None:
        return jsonify({
            "Error": "No book found with that ISBN."
        }), 404

    review = db.execute("""
        SELECT COUNT(*), AVG(rating) FROM reviews WHERE book_isbn = :book_isbn""",
        {"book_isbn": isbn}).fetchone()
    
    if review[0] == 0:
        average_rating = "N/A"
        review_count = review[0]
    else:
        average_rating = float(round(review[1], 2))
        review_count = review[0]

    return jsonify({
        "author": book.author,
        "average_rating": average_rating,
        "isbn": book.isbn,
        "review_count": review_count,
        "title": book.title,
        "year": book.year
    })

@app.route("/logout")
def logout():
    session.clear()
    print("Logged out")
    return redirect("/")

import config
import os
import requests

from flask import Flask, session, render_template, request, redirect, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)
key = config.key
res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": key, "isbns": "9781632168146"})

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

        if session.get("user_id") is not None:
            return redirect("/search")
        else:
            return render_template("login.html")

    if request.method == "POST":
        
        username = request.form.get("username")
        password = request.form.get("password")

        # Redirect if missing fields
        if username == "" or password == "":
            return redirect("/")

        user = db.execute("""
            SELECT * FROM users WHERE username = :username""",
            {"username": username}).fetchone()

        # If Login button pressed
        if request.form["button"] == "login":
            
            if user.rowcount() != 0 and user.password == password:
                session["user_id"] = user.id
                return redirect("/search")
            else:
                print("Username or password incorrect")
                return redirect("/")

        # If Register button pressed
        elif request.form["button"] == "register":
            
            if user.rowcount() == 0:
                db.execute("""
                    INSERT INTO users (username, password) VALUES (:username, :password)""",
                    {"username": username, "password": password})
                db.commit()

                user = db.execute("""
                    SELECT id FROM users WHERE username = :username""",
                    {"username": username}).fetchone()

                session["user_id"] = user.id

                print("Registered user")
                return redirect("/search")

            else:
                print("User already exists")
                return redirect("/")


@app.route("/search", methods=["GET", "POST"])
def search():
    # User successfully logged in
    if request.method == "GET" and session.get("user_id") is not None:
        return render_template("search.html", username=session["user_id"])
    # Accessing a route without login
    else:
        return redirect("/")
    

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

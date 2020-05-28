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




#data = str(res.json()["books"][0]["work_reviews_count"])
#return data

stored_username = "john"
stored_password = "123"


@app.route("/", methods=["GET", "POST"])
def index():

    # Ask user to login if at homepage and have no session
    if request.method == "GET" and session.get("user_id") is None:
        return render_template("login.html")

    # Set session if credentials match database otherwise redirect
    elif request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if stored_username == username and stored_password == password:
            session["user_id"] = username
            print(session["user_id"])
        else:
            # Temporary?
            return redirect("/")

    # A session has been created
    if session.get("user_id") is not None:
        return redirect("/search")


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

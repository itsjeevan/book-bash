from functools import wraps
from flask import request, redirect, session, url_for

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_username") is None:
            # return redirect("/")
            return redirect(url_for('index', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


import os
from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 's3cr3t@123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///audit.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class AuditEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20))
    parameter = db.Column(db.String(100))
    score = db.Column(db.Float)
    percent = db.Column(db.String(10))
    remarks = db.Column(db.Text)
    username = db.Column(db.String(50))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(50))

PARAMETERS = [
    "Temp taken", "Temp", "Mg Scale Calibration", 
    "Mg addition Qty (kg)", "Vessel Temp"
]

@app.before_request
def create_tables():
    try:
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            db.session.add(User(username='admin', password='admin'))
            db.session.commit()
    except Exception as e:
        print("DB Init Error:", e)

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("register") == "1":
            uname = request.form["username"]
            pwd = request.form["password"]
            confirm = request.form["confirm"]
            if pwd != confirm:
                return render_template("login.html", error="Passwords do not match", show_register=True)
            if User.query.filter_by(username=uname).first():
                return render_template("login.html", error="Username already exists", show_register=True)
            db.session.add(User(username=uname, password=pwd))
            db.session.commit()
            return render_template("login.html", success="Registration successful. Please login.", show_register=False)
        else:
            uname = request.form["username"]
            pwd = request.form["password"]
            user = User.query.filter_by(username=uname, password=pwd).first()
            if user:
                session["username"] = uname
                return redirect("/form")
            else:
                return render_template("login.html", error="Invalid credentials", show_register=False)
    elif request.method == "GET":
        if request.args.get("register") == "1":
            return render_template("login.html", show_register=True)
    return render_template("login.html", show_register=False)

@app.route("/form", methods=["GET", "POST"])
def form():
    if "username" not in session:
        return redirect("/")
    if request.method == "POST":
        date = request.form["date"]
        for param in PARAMETERS:
            score = float(request.form.get(f"{param}_score", 0))
            percent = request.form.get(f"{param}_percent", "")
            remarks = request.form.get(f"{param}_remarks", "")
            entry = AuditEntry(
                date=date, parameter=param, score=score, 
                percent=percent, remarks=remarks, 
                username=session["username"]
            )
            db.session.add(entry)
        db.session.commit()
        return render_template("form.html", parameters=PARAMETERS, success="Saved successfully.")
    return render_template("form.html", parameters=PARAMETERS)

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect("/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


from flask import Flask, render_template, request, redirect, session, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = 'secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///audit.db'
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

@app.before_requestt
def create_tables():
    try:
            db.create_all()
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(username='admin', password='admin'))
                    db.session.commit()
    except Exception as e:
        print('Error during DB init:', e)

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if "register" in request.form:
            uname = request.form["username"]
            pwd = request.form["password"]
            confirm = request.form["confirm"]
            if pwd != confirm:
                return render_template("login.html", error="Passwords do not match", show_register=True)
            if User.query.filter_by(username=uname).first():
                return render_template("login.html", error="Username already exists", show_register=True)
            db.session.add(User(username=uname, password=pwd))
                        db.session.commit()
    except Exception as e:
        print('Error during DB init:', e)
            return render_template("login.html", success="Registration successful. Please login.")
        else:
            uname = request.form["username"]
            pwd = request.form["password"]
            user = User.query.filter_by(username=uname, password=pwd).first()
            if user:
                session["username"] = uname
                return redirect("/form")
            else:
                return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/form")
def form():
    if "username" not in session:
        return redirect("/")
    entries = AuditEntry.query.order_by(AuditEntry.date.desc()).all()
    return render_template("form.html", parameters=PARAMETERS, entries=entries, user=session["username"])

@app.route("/submit", methods=["POST"])
def submit():
    if "username" not in session:
        return redirect("/")
    entry = AuditEntry(
        date=request.form["date"],
        parameter=request.form["parameter"],
        score=float(request.form["score"]),
        percent=request.form.get("percent", ""),
        remarks=request.form["remarks"],
        username=session["username"]
    )
    db.session.add(entry)
                db.session.commit()
    except Exception as e:
        print('Error during DB init:', e)
    return redirect("/form")

@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect("/")
    entries = AuditEntry.query.all()
    summary = {}
    for e in entries:
        if e.date not in summary:
            summary[e.date] = {"total": 0, "count": 0}
        summary[e.date]["total"] += e.score
        summary[e.date]["count"] += 1
    for date in summary:
        summary[date]["avg"] = round(summary[date]["total"] / summary[date]["count"], 2)
    return render_template("dashboard.html", summary=summary, user=session["username"])

@app.route("/export")
def export():
    if "username" not in session:
        return redirect("/")
    entries = AuditEntry.query.all()
    data = [{
        "Date": e.date,
        "Parameter": e.parameter,
        "Score": e.score,
        "Percent": e.percent,
        "Remarks": e.remarks,
        "User": e.username
    } for e in entries]
    df = pd.DataFrame(data)
    path = "audit_export.xlsx"
    df.to_excel(path, index=False)
    return send_file(path, as_attachment=True)

@app.route("/cleanup")
def cleanup():
    if "username" not in session:
        return redirect("/")
    cutoff = datetime.now() - timedelta(days=30)
    removed = 0
    for entry in AuditEntry.query.all():
        entry_date = datetime.strptime(entry.date, "%Y-%m-%d")
        if entry_date < cutoff:
            db.session.delete(entry)
            removed += 1
                db.session.commit()
    except Exception as e:
        print('Error during DB init:', e)
    flash(f"Deleted {removed} old entries.")
    return redirect("/form")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    import os
port = int(os.environ.get("PORT", 10000))
app.run(host="0.0.0.0", port=port)

import datetime, os
from flask import Flask, render_template, request, redirect, send_from_directory
from flask_cors import CORS
import sqlite3

#--- sql db init
conn = sqlite3.connect("myDatabase.db")
db = conn.cursor()
#db.execute("DROP TABLE hit")
db.execute("""
CREATE TABLE IF NOT EXISTS hit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL,
    route TEXT NOT NULL,
    referrer TEXT NOT NULL,
    time TIMESTAMP NOT NULL,
    browser TEXT NOT NULL,
    location TEXT NOT NULL,
    device TEXT NOT NULL
)
""") # db structure for each page hit
conn.commit()
conn.close()

#--- functions
def get_db_connection():
    db = sqlite3.connect('myDatabase.db')
    db.row_factory = sqlite3.Row
    return db

def domainAllowed(domain):
    temp = domain.split(".")
    if 'rafis' in temp and "work" in temp:
        return True
    else:
        return False


#--- flask init
app = Flask(__name__)

CORS(app)

#--------- routes

#-- home page
@app.route("/")
def index():
    conn = get_db_connection()
    db = conn.cursor()
    data = db.execute("SELECT DISTINCT(domain) FROM hit").fetchall()
    conn.close()
    #return render_template("index.html", data=data)
    return redirect("/analytics.rafis.work")



#-- analytics of <domain>
@app.route("/<domain>")
def page(domain):
    typ = request.args.get("type")
    value = request.args.get("value")
    dateQuery = ""
    
    if not typ:
        typ = "month" # default type to month
    elif typ not in ["month", "year"]:
        return "NO" # if type is not month or year

    try:
        if typ == "month":
            
                if not value:
                    tmp = datetime.date.today()
                    month = tmp.strftime('%m')
                    dateQuery = f" AND time LIKE '{tmp.year}-{month}%'"
                    value = month
                elif int(value) > 0 or int(value) <= 12:# if injection used will throw value error (only accepts int values)
                    if len(value) == 1:
                        value = f"0{value}"
                    tmp = datetime.date.today()
                    dateQuery = f" AND time LIKE '{tmp.year}-{value}%'"
                else:
                    return "NO"
        elif typ == "year":
            if not value:
                tmp = datetime.date.today()
                dateQuery = f" AND time LIKE  '{tmp.year}%'"
                value = tmp.year
            else:
                value = int(value)
                dateQuery = f" AND time LIKE '{value}%'"
    except ValueError:
        return "NO"
    
    conn = get_db_connection()
    db = conn.cursor()
    
    hits = db.execute("SELECT time FROM hit WHERE domain = ?"+dateQuery, (domain,)).fetchall()
    
    device = db.execute("SELECT COUNT(device), device FROM hit WHERE domain = ?"+dateQuery+" GROUP BY (device)", (domain,)).fetchall()

    browser = db.execute("SELECT COUNT(browser), browser FROM hit WHERE domain = ?"+dateQuery+" GROUP BY (browser)", (domain,)).fetchall()

    location = db.execute("SELECT COUNT(location), location FROM hit WHERE domain = ?"+dateQuery+" GROUP BY (location)", (domain,)).fetchall()

    route = db.execute("SELECT COUNT(route), route FROM hit WHERE domain = ?"+dateQuery+" GROUP BY (route)", (domain,)).fetchall()

    referrer = db.execute("SELECT COUNT(referrer), referrer FROM hit WHERE domain = ?"+dateQuery+" GROUP BY (referrer)", (domain,)).fetchall()


    # data for navbar
    data = db.execute("SELECT DISTINCT(domain) FROM hit").fetchall()
    
    conn.close()
    return render_template("page.html", data=data, domain=domain, hits=hits, device=device, browser=browser, location=location, route=route, referrer=referrer, type=[typ, value])

#-- serves the analytics js file that will send page hits to the server
@app.route("/analytics")
def analytics():
    return send_from_directory('templates', "analytics.js")

#-- page hit route, stores the page view and relevant data
@app.route("/hit", methods=["POST"])
def hit():    
    time = datetime.datetime.now()

    try: # checks that the json post data exists
        domain = request.json["domain"]
        route = request.json["route"]
        referrer = request.json["referrer"]
        browser = request.json["browser"]
        location = request.json["location"]
        device = request.json["device"]
    except KeyError:
        return "NO"

    if not domainAllowed(domain):
        return "NO"

    # inserts data into hits table
    conn = get_db_connection()
    db = conn.cursor()
    db.execute("""
        INSERT INTO hit (
        domain,
        route,
        time,
        referrer,
        browser,
        location,
        device
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        domain,
        route,
        time,
        referrer,
        browser,
        location,
        device
    ))
    conn.commit()
    conn.close()
    
    return "OK"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
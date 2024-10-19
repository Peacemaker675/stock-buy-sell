from cs50 import SQL
from flask import Flask,redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    symbols = db.execute("""
        SELECT symbol,
               SUM(CASE WHEN type = 'BUY' THEN shares ELSE -shares END) AS ttl_shares,
               price,
               SUM(CASE WHEN type = 'BUY' THEN shares ELSE -shares END) * price AS ttl_amt
        FROM transactions
        WHERE buy_id = ?
        GROUP BY symbol
        HAVING SUM(CASE WHEN type = 'BUY' THEN shares ELSE -shares END) > 0
    """, session["user_id"])

    rows = db.execute("SELECT cash FROM users WHERE id = ?",
                      session["user_id"])
    cash = rows[0]["cash"]

    total_shares_value = sum(float(symbol["ttl_amt"]) for symbol in symbols)

    total_portfolio_value = total_shares_value + cash

    return render_template("index.html", symbols=symbols, cash=cash, total=total_portfolio_value)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = lookup(request.form.get("symbol"))
        if not symbol:
            return apology("INVALID SYMBOL", 400)
        shares = request.form.get("shares")
        if shares is None or not shares.isdigit() or int(shares) <= 0:
            return apology("invalid number of shares", 400)
        rows = db.execute("SELECT * FROM users WHERE id = ?;",
                          session["user_id"])
        now = datetime.now()
        if (symbol["price"])*float(shares) <= rows[0]["cash"]:
            db.execute("INSERT INTO transactions(buy_id,symbol,price,shares,ttl_amt,type,transacted) VALUES (?,?,?,?,?,?,?);",
                       rows[0]["id"], symbol["symbol"], symbol["price"], shares, symbol["price"]*float(shares), "BUY", now.strftime('%y-%m-%d %H:%M:%S'))
            db.execute("UPDATE users SET cash = (? - ?) WHERE id = ?;",
                       rows[0]["cash"], symbol["price"]*float(shares), rows[0]["id"])
            return redirect("/")
        else:
            return apology("Insufficeint Balance", 400)
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    symbols = db.execute(
        "SELECT * FROM transactions WHERE buy_id = ?;", session["user_id"])
    return render_template("history.html", symbols=symbols)


@app.route("/login", methods=["GET", "POST"])
def login():

    session.clear()

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 403)

        elif not request.form.get("password"):
            return apology("must provide password", 403)

        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get(
                "username")
        )

        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")
    
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        symbol = lookup(request.form.get("symbol"))
        if symbol:
            return render_template("quoted.html", symbol=symbol)
        return apology("INVALID SYMBOL", 400)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 400)
        elif not request.form.get("password"):
            return apology("must provide password", 400)
        elif not request.form.get("password") == request.form.get("confirmation"):
            return apology("password doesn't match confirmation")

        rows = db.execute(
            "SELECT * FROM users WHERE username = ?;", request.form.get(
                "username")
        )

        # Ensure username exists and password is correct
        if len(rows) == 1:
            return apology("Username already in use")
        db.execute("INSERT INTO users(username,hash) VALUES (?,?);", request.form.get(
            "username"), generate_password_hash(request.form.get("password")))
        rows = db.execute(
            "SELECT id FROM users WHERE username = ?", request.form.get("username"))
        session["user_id"] = rows[0]["id"]
        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        symbol = lookup(request.form.get("symbol"))
        shares = int(request.form.get("shares"))
        user_id = session["user_id"]
        rows = db.execute("""
            SELECT symbol, SUM(CASE WHEN type = 'BUY' THEN shares ELSE -shares END) as net_shares
            FROM transactions
            WHERE buy_id = ? AND symbol = ?
            GROUP BY symbol
        """, user_id, symbol["symbol"])
        if not rows or rows[0]["net_shares"] < shares:
            return apology("not enough shares", 400)
        if symbol is None:
            return apology("not valid symbol")
        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?;",
                   symbol["price"]*shares, user_id)
        db.execute("""
            INSERT INTO transactions (buy_id, symbol, shares, price, type, transacted,ttl_amt)
            VALUES (?, ?, ?, ?, 'SELL',?,?)
        """, user_id, symbol["symbol"], shares, symbol["price"], datetime.now().strftime('%y-%m-%d %H:%M:%S'), shares*symbol["price"])
        return redirect("/")
    else:
        symbols = db.execute("""
            SELECT symbol,
                SUM(CASE WHEN type = 'BUY' THEN shares ELSE -shares END) AS total_shares
            FROM transactions
            WHERE buy_id = ?
            GROUP BY symbol
            HAVING SUM(CASE WHEN type = 'BUY' THEN shares ELSE -shares END) > 0
        """, session["user_id"])
        return render_template("sell.html", symbols=symbols)

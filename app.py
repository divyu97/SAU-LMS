from flask import Flask, render_template, request, redirect, url_for, abort, flash
from flask_bcrypt import Bcrypt
from flask_login import login_user, LoginManager, login_required, logout_user, current_user
import pymysql
from datetime import datetime, timedelta
from functools import wraps

class User:
    def __init__(self, username, user_type, member_id=None):
        self.username = username
        self.user_type = user_type
        self.member_id = member_id
        self.is_authenticated = True

    def get_id(self):
        return self.username

app = Flask(__name__)
app.config["SECRET_KEY"] = "CSE231-SAU-LMS-SECRET-KEY"

bcrypt = Bcrypt(app)

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "southasianuniversitylms",
    "autocommit": False
}

def get_connection():
    return pymysql.connect(**DB_CONFIG)

try:
    connection = get_connection()
    cursor = connection.cursor()
except Exception:
    connection = None
    cursor = None

def ensure_db():
    global connection, cursor
    try:
        if connection is None:
            connection = get_connection()
            cursor = connection.cursor()
        else:
            connection.ping(reconnect=True)
    except Exception:
        connection = get_connection()
        cursor = connection.cursor()
    return connection, cursor

def get_policy(key, default):
    """Fetch dynamic policy configuration (FR-27, FR-28, NFR-09)."""
    try:
        _, cur = ensure_db()
        cur.execute("SELECT Policy_Value FROM POLICY WHERE Policy_Key=%s", (key,))
        row = cur.fetchone()
        if row and row[0]:
            return row[0]
    except Exception:
        pass
    return default

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

def role_required(*allowed_roles):
    """Decorator to enforce strict Role-Based Access Control (RBAC) (NFR-03)."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("login"))
            if current_user.user_type not in allowed_roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403

@login_manager.user_loader
def load_user(user_id):
    _, cur = ensure_db()
    cur.execute("SELECT Type, Member_ID FROM MEMBER WHERE Username=%s", (user_id,))
    row = cur.fetchone()
    if row:
        return User(user_id, row[0].lower(), member_id=row[1])
    return None

# ----------------- PUBLIC AUTH ROUTES ----------------- #

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if current_user.is_authenticated:
            if current_user.user_type == "admin":
                return redirect("/admin")
            else:
                return redirect("/portal")
        return render_template("login.html")
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        user_type = request.form.get("user-type", "").lower()

        conn, cur = ensure_db()
        cur.execute("SELECT Password, Type, Member_ID FROM MEMBER WHERE Username=%s", (username,))
        row = cur.fetchone()

        if row and bcrypt.check_password_hash(row[0], password) and user_type == row[1].lower():
            user = User(username, user_type, member_id=row[2])
            login_user(user, force=True)
            if user_type == "admin":
                return redirect("/admin")
            else:
                return redirect("/portal")
        else:
            return render_template("login.html", error="Invalid username, password, or role selection.")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")
    else:
        fullname = request.form.get("name")
        major = request.form.get("major")
        dept = request.form.get("dept")
        enrolment = request.form.get("enrolment")
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")
        today = datetime.today().strftime('%Y-%m-%d')

        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")

        conn, cur = ensure_db()
        try:
            conn.begin()
            cur.execute("""
                INSERT INTO STUDENT_REQUEST 
                (Name, Major, Department, Enrolment_No, Email, Username, Password, Request_Date) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, [fullname, major, dept, enrolment, email, username, hashed_pw, today])
            conn.commit()
            return redirect(url_for("login"))
        except Exception as e:
            conn.rollback()
            return render_template("signup.html", error=f"Registration failed: {str(e)}")

@app.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    return redirect("/")

# ----------------- MEMBER PORTAL (FR-11, FR-17, FR-18, FR-19) ----------------- #

@app.route("/portal", methods=["GET"])
@login_required
@role_required("student", "faculty")
def member_portal():
    conn, cur = ensure_db()
    active_tab = request.args.get("tab", "search")
    query = request.args.get("q", "").strip()

    books = []
    loans = []
    requests = []
    active_count = 0
    overdue_count = 0
    total_unpaid_fines = 0.0
    daily_fine_rate = float(get_policy("FINE_RATE_PER_DAY", "10.00"))
    today = datetime.today().date()

    if active_tab == "search":
        # FR-11: Catalogue Search with real-time copy availability count
        if query:
            search_pattern = f"%{query}%"
            cur.execute("""
                SELECT 
                    B.ISBN, 
                    B.Title, 
                    COALESCE(GROUP_CONCAT(A.Name ORDER BY BA.Author_Order SEPARATOR ', '), 'Unknown') AS Authors,
                    B.Subject, 
                    B.Pub_Year, 
                    COUNT(C.Copy_ID) AS Total_Copies,
                    SUM(CASE WHEN C.Status = 'Available' THEN 1 ELSE 0 END) AS Available_Copies
                FROM BOOK B
                LEFT JOIN BOOK_AUTHOR BA ON B.ISBN = BA.ISBN
                LEFT JOIN AUTHOR A ON BA.Author_ID = A.Author_ID
                LEFT JOIN COPY C ON B.ISBN = C.ISBN
                WHERE B.Title LIKE %s OR B.Subject LIKE %s OR B.ISBN LIKE %s OR A.Name LIKE %s
                GROUP BY B.ISBN, B.Title, B.Subject, B.Pub_Year
                ORDER BY B.Title ASC
            """, [search_pattern, search_pattern, search_pattern, search_pattern])
        else:
            cur.execute("""
                SELECT 
                    B.ISBN, 
                    B.Title, 
                    COALESCE(GROUP_CONCAT(A.Name ORDER BY BA.Author_Order SEPARATOR ', '), 'Unknown') AS Authors,
                    B.Subject, 
                    B.Pub_Year, 
                    COUNT(C.Copy_ID) AS Total_Copies,
                    SUM(CASE WHEN C.Status = 'Available' THEN 1 ELSE 0 END) AS Available_Copies
                FROM BOOK B
                LEFT JOIN BOOK_AUTHOR BA ON B.ISBN = BA.ISBN
                LEFT JOIN AUTHOR A ON BA.Author_ID = A.Author_ID
                LEFT JOIN COPY C ON B.ISBN = C.ISBN
                GROUP BY B.ISBN, B.Title, B.Subject, B.Pub_Year
                ORDER BY B.Title ASC
            """)
        books = cur.fetchall()

    elif active_tab == "loans":
        # FR-17: Member Active Loans & Overdue Fines
        cur.execute("""
            SELECT 
                BW.Borrow_ID,
                BW.Copy_ID,
                B.Title,
                BW.Issue_Date,
                BW.Due_Date,
                BW.Return_Date,
                BW.Fine_Amount
            FROM BORROWING BW
            JOIN COPY C ON BW.Copy_ID = C.Copy_ID
            JOIN BOOK B ON C.ISBN = B.ISBN
            WHERE BW.Member_ID = %s
            ORDER BY BW.Issue_Date DESC, BW.Borrow_ID DESC
        """, (current_user.member_id,))
        raw_loans = cur.fetchall()

        for loan in raw_loans:
            borrow_id, copy_id, title, issue_date, due_date, return_date, fine_amt = loan
            fine_val = float(fine_amt or 0.0)

            # Check if active loan is overdue
            due_dt = datetime.strptime(str(due_date), "%Y-%m-%d").date() if isinstance(due_date, str) else due_date
            loan_status = "Returned" if return_date else "Active"

            if not return_date:
                active_count += 1
                if today > due_dt:
                    loan_status = "Overdue"
                    overdue_count += 1
                    # Dynamic fine calculation for currently overdue book
                    overdue_days = (today - due_dt).days
                    fine_val = max(fine_val, float(overdue_days * daily_fine_rate))

            total_unpaid_fines += fine_val
            loans.append((borrow_id, copy_id, title, issue_date, due_date, return_date, fine_val, loan_status))

    elif active_tab == "requests":
        # FR-18, FR-19: Book Requests & Decision Note
        cur.execute("""
            SELECT Request_ID, Requested_Title, Author, Request_Type, Request_Date, Status, Decision_Note 
            FROM REQUEST 
            WHERE Requester_ID=%s 
            ORDER BY Request_Date DESC, Request_ID DESC
        """, (current_user.member_id,))
        requests = cur.fetchall()

    return render_template(
        "portal.html",
        username=current_user.username,
        member_id=current_user.member_id,
        user_type=current_user.user_type.capitalize(),
        active_tab=active_tab,
        query=query,
        books=books,
        loans=loans,
        requests=requests,
        active_count=active_count,
        overdue_count=overdue_count,
        total_unpaid_fines=total_unpaid_fines
    )

@app.route("/portal/request", methods=["POST"])
@login_required
@role_required("student", "faculty")
def member_submit_request():
    title = request.form.get("title")
    author = request.form.get("author")
    request_type = request.form.get("request_type")
    today = datetime.today().strftime('%Y-%m-%d')

    conn, cur = ensure_db()
    try:
        conn.begin()
        cur.execute("""
            INSERT INTO REQUEST (Requester_ID, Requested_Title, Author, Request_Date, Request_Type, Status, Decision_Note)
            VALUES (%s, %s, %s, %s, 'Pending', NULL)
        """, [current_user.member_id, title, author, request_type, today])
        conn.commit()
    except Exception as e:
        conn.rollback()

    return redirect("/portal?tab=requests")

@app.route("/student")
@login_required
@role_required("student")
def student_redirect():
    return redirect("/portal")

@app.route("/faculty")
@login_required
@role_required("faculty")
def faculty_redirect():
    return redirect("/portal")

# ----------------- ADMIN DASHBOARD & SECTIONS ----------------- #

@app.route("/admin", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin():
    return redirect("/admin/memreq")

@app.route("/admin/policy", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_policy():
    """FR-27, FR-28, NFR-09: Dynamic Library Policy Configuration."""
    conn, cur = ensure_db()
    message = None

    if request.method == "POST":
        loan_period = request.form.get("LOAN_PERIOD_DAYS", "14")
        fine_rate = request.form.get("FINE_RATE_PER_DAY", "10.00")
        dead_stock_years = request.form.get("DEAD_STOCK_YEARS", "1")
        dead_stock_usage = request.form.get("DEAD_STOCK_USAGE_LIMIT", "2")

        try:
            conn.begin()
            cur.execute("UPDATE POLICY SET Policy_Value=%s WHERE Policy_Key='LOAN_PERIOD_DAYS'", (loan_period,))
            cur.execute("UPDATE POLICY SET Policy_Value=%s WHERE Policy_Key='FINE_RATE_PER_DAY'", (fine_rate,))
            cur.execute("UPDATE POLICY SET Policy_Value=%s WHERE Policy_Key='DEAD_STOCK_YEARS'", (dead_stock_years,))
            cur.execute("UPDATE POLICY SET Policy_Value=%s WHERE Policy_Key='DEAD_STOCK_USAGE_LIMIT'", (dead_stock_usage,))
            conn.commit()
            message = "Policy parameters updated successfully! Subsequent loans and returns will use these updated rules."
        except Exception as e:
            conn.rollback()

    cur.execute("SELECT Policy_Key, Policy_Value FROM POLICY")
    rows = cur.fetchall()
    policies = {row[0]: row[1] for row in rows}

    return render_template(
        "policy.html",
        username=current_user.username,
        user_type=current_user.user_type.capitalize(),
        policies=policies,
        message=message
    )

@app.route("/admin/<section>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_section(section):
    conn, cur = ensure_db()

    if section == "memreq":
        cur.execute("SELECT Request_ID, Name, Major, Department, Enrolment_No, Email, Username, Request_Date FROM STUDENT_REQUEST")
        result = cur.fetchall()
        rows = []
        reqIDS = []
        for row in result:
            rows.append(row[1:])
            reqIDS.append(row[0])
        return render_template(
            section + ".html",
            username=current_user.username,
            user_type=current_user.user_type.capitalize(),
            cols=["Full Name", "Major", "Department", "Enrolment No.", "Email", "Username", "Request Date"],
            rows=rows,
            reqIDS=reqIDS
        )

    elif section == "viewfac":
        # FR-04, FR-05: Faculty Management Table View
        cur.execute("""
            SELECT M.Member_ID, M.Name AS "Full Name", F.Office_No, F.Department, M.Email, M.Username 
            FROM MEMBER M JOIN FACULTY F ON M.Member_ID = F.Member_ID
            ORDER BY M.Member_ID ASC
        """)
        result = cur.fetchall()
        rows = []
        memIDS = []
        for row in result:
            rows.append(row[1:])
            memIDS.append(row[0])
        return render_template(
            section + ".html",
            username=current_user.username,
            user_type=current_user.user_type.capitalize(),
            cols=["Full Name", "Office No.", "Department", "Email", "Username"],
            rows=rows,
            memIDS=memIDS
        )

    elif section == "viewstud":
        cur.execute("""
            SELECT M.Member_ID, M.Name AS "Full Name", S.Major, S.Department, S.Enrolment_No, M.Email, M.Username
            FROM MEMBER M JOIN STUDENT S ON M.Member_ID = S.Member_ID
            ORDER BY M.Member_ID ASC
        """)
        result = cur.fetchall()
        rows = []
        memIDS = []
        for row in result:
            rows.append(row[1:])
            memIDS.append(row[0])
        return render_template(
            section + ".html",
            username=current_user.username,
            user_type=current_user.user_type.capitalize(),
            cols=["Full Name", "Major", "Department", "Enrolment No.", "Email", "Username"],
            rows=rows,
            memIDS=memIDS
        )

    elif section == "viewbooks":
        cur.execute("SELECT * FROM BOOK ORDER BY Title ASC")
        rows = cur.fetchall()
        return render_template(
            section + ".html",
            username=current_user.username,
            user_type=current_user.user_type.capitalize(),
            cols=["ISBN", "Title", "Subject", "Publication Year", "Price", "Publisher ID"],
            rows=rows
        )

    elif section == "viewcopies":
        cur.execute("SELECT * FROM COPY ORDER BY Copy_ID ASC")
        rows = cur.fetchall()
        return render_template(
            section + ".html",
            username=current_user.username,
            user_type=current_user.user_type.capitalize(),
            cols=["Copy ID", "ISBN", "Acquisition Date", "Status"],
            rows=rows
        )

    elif section == "borrowedbooks":
        cur.execute("SELECT Borrow_ID, Copy_ID, Member_ID, Issue_Date, Due_Date, Return_Date, Fine_Amount FROM BORROWING ORDER BY Issue_Date DESC, Borrow_ID DESC")
        rows = cur.fetchall()
        return render_template(
            section + ".html",
            username=current_user.username,
            user_type=current_user.user_type.capitalize(),
            cols=["Borrow ID", "Copy ID", "Member ID", "Borrow Date", "Due Date", "Return Date", "Fine Amount"],
            rows=rows
        )

    elif section == "bookrequests":
        cur.execute("SELECT Request_ID, Requester_ID, Requested_Title, Author, Request_Date, Request_Type, Status, Decision_Note FROM REQUEST ORDER BY Request_Date DESC, Request_ID DESC")
        rows = cur.fetchall()
        return render_template(
            section + ".html",
            username=current_user.username,
            user_type=current_user.user_type.capitalize(),
            cols=["Request ID", "Requester ID", "Requested Title", "Author", "Request Date", "Request Type", "Status", "Decision Note"],
            rows=rows
        )

    elif section == "genrep":
        # Dynamic policy thresholds (FR-27, FR-28)
        dead_years = int(get_policy("DEAD_STOCK_YEARS", "1"))
        usage_limit = int(get_policy("DEAD_STOCK_USAGE_LIMIT", "2"))

        cur.execute("""
            SELECT
                B.ISBN,
                B.Title,
                B.Subject,
                B.Price,
                MIN(C.Acquisition_Date) AS First_Acquisition_Date,
                COUNT(T.Borrow_ID) AS Total_Usage_Count,
                COUNT(C.Copy_ID) AS Total_Copies_Purchased
            FROM
                BOOK B
            JOIN
                COPY C ON B.ISBN = C.ISBN
            LEFT JOIN
                BORROWING T ON C.Copy_ID = T.Copy_ID
            GROUP BY
                B.ISBN, B.Title, B.Subject, B.Price
            HAVING
                MIN(C.Acquisition_Date) < DATE_SUB(CURDATE(), INTERVAL %s YEAR)
                AND COUNT(T.Borrow_ID) < %s
                AND COUNT(T.Borrow_ID) < COUNT(C.Copy_ID)
            ORDER BY
                Total_Usage_Count ASC, First_Acquisition_Date ASC;
        """, (dead_years, usage_limit))
        underutilized = cur.fetchall()

        cur.execute("""
            SELECT
                B.ISBN,
                B.Title,
                COUNT(C.Copy_ID) AS Total_Copies,
                SUM(CASE WHEN C.Status = 'Issued' THEN 1 ELSE 0 END) AS Issued_Copies,
                (
                    SELECT COUNT(*)
                    FROM REQUEST R
                    WHERE R.Requested_Title = B.Title
                    AND R.Request_Type = 'More Copies'
                    AND R.Status = 'Pending'
                ) AS Pending_Requests
            FROM
                BOOK B
            JOIN
                COPY C ON B.ISBN = C.ISBN
            GROUP BY
                B.ISBN, B.Title
            HAVING
                Total_Copies = Issued_Copies
                AND Pending_Requests > 0
            ORDER BY
                Pending_Requests DESC, Total_Copies DESC;
        """)
        highdemand = cur.fetchall()

        return render_template(
            section + ".html",
            username=current_user.username,
            user_type=current_user.user_type.capitalize(),
            cols1=["ISBN", "Title", "Subject", "Price", "First Acquisition Date", "Total Usage Count", "Total Copies Purchased"],
            cols2=["ISBN", "Title", "Total Copies", "Issued Copies", "Pending Requests"],
            borrows=underutilized,
            titles=highdemand
        )

    elif section == "genrep2":
        # FR-24: Usage Pattern (Student vs Faculty Borrowing)
        cur.execute("""
            SELECT
                M.Type AS Member_Type,
                COUNT(DISTINCT B.ISBN) AS Total_Unique_Titles_Borrowed
            FROM
                BORROWING T
            JOIN
                MEMBER M ON T.Member_ID = M.Member_ID
            JOIN
                COPY C ON T.Copy_ID = C.Copy_ID
            JOIN
                BOOK B ON C.ISBN = B.ISBN
            WHERE
                M.Type IN ('Student', 'Faculty')
            GROUP BY
                M.Type
        """)
        usage = cur.fetchall()

        # FR-25: Top Unfulfilled Faculty Requests
        cur.execute("""
            SELECT
                R.Requested_Title,
                R.Author,
                COUNT(R.Request_ID) AS Total_Faculty_Requests
            FROM
                REQUEST R
            JOIN
                MEMBER M ON R.Requester_ID = M.Member_ID
            WHERE
                M.Type = 'Faculty'
                AND R.Status IN ('Pending', 'Rejected')
            GROUP BY
                R.Requested_Title, R.Author
            ORDER BY
                Total_Faculty_Requests DESC
            LIMIT 5
        """)
        requests = cur.fetchall()

        cur.execute("""
            SELECT
                B.Subject,
                COUNT(C.Copy_ID) AS Total_Copies,
                SUM(CASE WHEN C.Status = 'Available' THEN 1 ELSE 0 END) AS Available_Copies_Count
            FROM
                BOOK B
            JOIN
                COPY C ON B.ISBN = C.ISBN
            GROUP BY
                B.Subject
            ORDER BY
                Available_Copies_Count DESC
        """)
        books = cur.fetchall()

        return render_template(
            section + ".html",
            username=current_user.username,
            user_type=current_user.user_type.capitalize(),
            cols1=["Member Type", "Total Unique Titles Borrowed"],
            cols2=["Requested Title", "Author", "Total Faculty Requests"],
            cols3=["Subject", "Total Copies", "Available Copies Count"],
            usage=usage,
            requests=requests,
            books=books
        )

# ----------------- ADMIN ACTIONS & ATOMIC TRANSACTIONS (NFR-05, US-7) ----------------- #

@app.route("/admin/memreq/approve/<id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def mem_req_approve(id):
    conn, cur = ensure_db()
    if request.method == "POST":
        member = request.form.get("member")
        cur.execute("SELECT Name, Email, Major, Department, Enrolment_No, Username, Password FROM STUDENT_REQUEST WHERE Request_ID=%s", (id,))
        result = cur.fetchone()
        if result:
            try:
                conn.begin()
                cur.execute("""
                    INSERT INTO MEMBER (Member_ID, Name, Email, Type, Username, Password) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, [member, result[0], result[1], "Student", result[5], result[6]])
                cur.execute("""
                    INSERT INTO STUDENT (Member_ID, Department, Major, Enrolment_No) 
                    VALUES (%s, %s, %s, %s)
                """, [member, result[3], result[2], result[4]])
                cur.execute("DELETE FROM STUDENT_REQUEST WHERE Request_ID=%s", (id,))
                conn.commit()
            except Exception as e:
                conn.rollback()
                return render_template("memreqapprove.html", id=id, username=current_user.username, user_type=current_user.user_type.capitalize(), error=f"Approval failed: {str(e)}")
        return redirect("/admin/memreq")
    else:
        return render_template("memreqapprove.html", id=id, username=current_user.username, user_type=current_user.user_type.capitalize())

@app.route("/admin/memreq/reject/<id>")
@login_required
@role_required("admin")
def mem_req_reject(id):
    conn, cur = ensure_db()
    try:
        conn.begin()
        cur.execute("DELETE FROM STUDENT_REQUEST WHERE Request_ID=%s", (id,))
        conn.commit()
    except Exception:
        conn.rollback()
    return redirect("/admin/memreq")

@app.route("/admin/viewfac/remove/<id>")
@login_required
@role_required("admin")
def fac_remove(id):
    conn, cur = ensure_db()
    try:
        conn.begin()
        cur.execute("DELETE FROM FACULTY WHERE Member_ID=%s", (id,))
        cur.execute("DELETE FROM BORROWING WHERE Member_ID=%s", (id,))
        cur.execute("DELETE FROM REQUEST WHERE Requester_ID=%s", (id,))
        cur.execute("DELETE FROM MEMBER WHERE Member_ID=%s", (id,))
        conn.commit()
    except Exception:
        conn.rollback()
    return redirect("/admin/viewfac")

@app.route("/admin/viewfac/update/<id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def fac_update(id):
    conn, cur = ensure_db()
    if request.method == "GET":
        cur.execute("""
            SELECT M.Name AS "Full Name", F.Office_No, F.Department, M.Email 
            FROM MEMBER M JOIN FACULTY F ON M.Member_ID = F.Member_ID AND M.Member_ID=%s
        """, (id,))
        result = cur.fetchone()
        return render_template(
            "facupdate.html",
            username=current_user.username,
            user_type=current_user.user_type.capitalize(),
            id=id,
            fullname=result[0],
            office=result[1],
            dept=result[2],
            email=result[3]
        )
    else:
        fullname = request.form.get("name")
        office = request.form.get("office")
        dept = request.form.get("dept")
        email = request.form.get("email")

        try:
            conn.begin()
            cur.execute("UPDATE MEMBER SET Name=%s, Email=%s WHERE Member_ID=%s", [fullname, email, id])
            cur.execute("UPDATE FACULTY SET Office_No=%s, Department=%s WHERE Member_ID=%s", [office, dept, id])
            conn.commit()
        except Exception:
            conn.rollback()
        return redirect("/admin/viewfac")

@app.route("/admin/viewfac/new", methods=["GET", "POST"])
@login_required
@role_required("admin")
def fac_add():
    conn, cur = ensure_db()
    if request.method == "GET":
        return render_template("facadd.html", username=current_user.username, user_type=current_user.user_type.capitalize())
    else:
        id = request.form.get("id")
        fullname = request.form.get("name")
        office = request.form.get("office")
        dept = request.form.get("dept")
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")
        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")

        try:
            conn.begin()
            cur.execute("""
                INSERT INTO MEMBER (Member_ID, Name, Email, Type, Username, Password) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """, [id, fullname, email, "Faculty", username, hashed_pw])
            cur.execute("""
                INSERT INTO FACULTY (Member_ID, Office_No, Department) 
                VALUES (%s, %s, %s)
            """, [id, office, dept])
            conn.commit()
            return redirect("/admin/viewfac")
        except Exception as e:
            conn.rollback()
            return render_template("facadd.html", username=current_user.username, user_type=current_user.user_type.capitalize(), error=f"Failed to add faculty: {str(e)}")

@app.route("/admin/viewstud/remove/<id>")
@login_required
@role_required("admin")
def stud_remove(id):
    conn, cur = ensure_db()
    try:
        conn.begin()
        cur.execute("DELETE FROM STUDENT WHERE Member_ID=%s", (id,))
        cur.execute("DELETE FROM BORROWING WHERE Member_ID=%s", (id,))
        cur.execute("DELETE FROM REQUEST WHERE Requester_ID=%s", (id,))
        cur.execute("DELETE FROM MEMBER WHERE Member_ID=%s", (id,))
        conn.commit()
    except Exception:
        conn.rollback()
    return redirect("/admin/viewstud")

@app.route("/admin/viewstud/update/<id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def stud_update(id):
    conn, cur = ensure_db()
    if request.method == "GET":
        cur.execute("""
            SELECT M.Name AS "Full Name", S.Major, S.Department, S.Enrolment_No, M.Email
            FROM MEMBER M JOIN STUDENT S ON M.Member_ID = S.Member_ID AND M.Member_ID=%s
        """, (id,))
        result = cur.fetchone()
        return render_template(
            "studupdate.html",
            username=current_user.username,
            user_type=current_user.user_type.capitalize(),
            id=id,
            fullname=result[0],
            major=result[1],
            dept=result[2],
            enrolment=result[3],
            email=result[4]
        )
    else:
        fullname = request.form.get("name")
        major = request.form.get("major")
        dept = request.form.get("dept")
        enrolment = request.form.get("enrolment")
        email = request.form.get("email")

        try:
            conn.begin()
            cur.execute("UPDATE MEMBER SET Name=%s, Email=%s WHERE Member_ID=%s", [fullname, email, id])
            cur.execute("UPDATE STUDENT SET Major=%s, Department=%s, Enrolment_No=%s WHERE Member_ID=%s", [major, dept, enrolment, id])
            conn.commit()
        except Exception:
            conn.rollback()
        return redirect("/admin/viewstud")

@app.route("/admin/viewbooks/remove/<isbn>")
@login_required
@role_required("admin")
def books_remove(isbn):
    conn, cur = ensure_db()
    try:
        conn.begin()
        cur.execute("DELETE FROM COPY WHERE ISBN=%s", (isbn,))
        cur.execute("DELETE FROM BOOK_AUTHOR WHERE ISBN=%s", (isbn,))
        cur.execute("DELETE FROM BOOK WHERE ISBN=%s", (isbn,))
        conn.commit()
    except Exception:
        conn.rollback()
    return redirect("/admin/viewbooks")

@app.route("/admin/viewbooks/new", methods=["GET", "POST"])
@login_required
@role_required("admin")
def books_add():
    conn, cur = ensure_db()
    if request.method == "GET":
        return render_template("booksadd.html", username=current_user.username, user_type=current_user.user_type.capitalize())
    else:
        isbn = request.form.get("isbn")
        title = request.form.get("title")
        authors = request.form.get("authors")
        subject = request.form.get("subject")
        year = request.form.get("year")
        price = request.form.get("price")
        publisher = request.form.get("publisher")

        try:
            conn.begin()
            cur.execute("INSERT INTO BOOK (ISBN, Title, Subject, Pub_Year, Price, Pub_ID) VALUES (%s, %s, %s, %s, %s, %s)", [isbn, title, subject, year, price, publisher])
            authors_list = authors.split(",")
            for index, author in enumerate(authors_list, start=1):
                author = author.strip()
                cur.execute("SELECT Author_ID FROM AUTHOR WHERE Name=%s", (author,))
                row = cur.fetchone()
                if not row:
                    cur.execute("INSERT INTO AUTHOR (Name) VALUES (%s)", (author,))
                    cur.execute("SELECT Author_ID FROM AUTHOR WHERE Name=%s", (author,))
                    row = cur.fetchone()
                author_id = row[0]
                cur.execute("INSERT INTO BOOK_AUTHOR (ISBN, Author_ID, Author_Order) VALUES (%s, %s, %s)", [isbn, author_id, index])
            conn.commit()
            return redirect("/admin/viewbooks")
        except Exception as e:
            conn.rollback()
            return render_template("booksadd.html", username=current_user.username, user_type=current_user.user_type.capitalize(), error=f"Error adding book: {str(e)}")

@app.route("/admin/viewbooks/addcopy/<isbn>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def bookcopy_add(isbn):
    conn, cur = ensure_db()
    if request.method == "GET":
        return render_template("bookcopyadd.html", username=current_user.username, user_type=current_user.user_type.capitalize(), isbn=isbn)
    else:
        copy = request.form.get("copy")
        adate = request.form.get("adate")
        status = request.form.get("status")
        try:
            conn.begin()
            cur.execute("INSERT INTO COPY (Copy_ID, ISBN, Acquisition_Date, Status) VALUES (%s, %s, %s, %s)", [copy, isbn, adate, status])
            conn.commit()
            return redirect("/admin/viewbooks")
        except Exception as e:
            conn.rollback()
            return render_template("bookcopyadd.html", username=current_user.username, user_type=current_user.user_type.capitalize(), isbn=isbn, error=str(e))

@app.route("/admin/viewcopies/remove/<id>")
@login_required
@role_required("admin")
def copies_remove(id):
    conn, cur = ensure_db()
    try:
        conn.begin()
        cur.execute("DELETE FROM BORROWING WHERE Copy_ID=%s", (id,))
        cur.execute("DELETE FROM COPY WHERE Copy_ID=%s", (id,))
        conn.commit()
    except Exception:
        conn.rollback()
    return redirect("/admin/viewcopies")

@app.route("/admin/viewcopies/update/<id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def copies_update(id):
    conn, cur = ensure_db()
    if request.method == "GET":
        cur.execute("SELECT Status FROM COPY WHERE Copy_ID=%s", (id,))
        status = cur.fetchone()[0]
        return render_template("copiesupdate.html", username=current_user.username, user_type=current_user.user_type.capitalize(), id=id, status=status)
    else:
        status = request.form.get("status")
        try:
            conn.begin()
            cur.execute("UPDATE COPY SET Status=%s WHERE Copy_ID=%s", [status, id])
            conn.commit()
        except Exception:
            conn.rollback()
        return redirect("/admin/viewcopies")

@app.route("/admin/borrowedbooks/remove/<id>")
@login_required
@role_required("admin")
def borrowedbooks_remove(id):
    conn, cur = ensure_db()
    try:
        conn.begin()
        cur.execute("DELETE FROM BORROWING WHERE Borrow_ID=%s", (id,))
        conn.commit()
    except Exception:
        conn.rollback()
    return redirect("/admin/borrowedbooks")

# ----------------- BOOK ISSUE & RETURN WITH DYNAMIC POLICY (NFR-05, US-2, US-7) ----------------- #

@app.route("/admin/borrowedbooks/new", methods=["GET", "POST"])
@login_required
@role_required("admin")
def borrowedbooks_add():
    conn, cur = ensure_db()
    today_str = datetime.today().strftime('%Y-%m-%d')
    
    # FR-27, US-7: Calculate default Due Date dynamically using configured LOAN_PERIOD_DAYS policy
    loan_days = int(get_policy("LOAN_PERIOD_DAYS", "14"))
    due_str = (datetime.today() + timedelta(days=loan_days)).strftime('%Y-%m-%d')

    if request.method == "GET":
        return render_template(
            "borrowedbooksadd.html",
            username=current_user.username,
            user_type=current_user.user_type.capitalize(),
            bdate=today_str,
            ddate=due_str
        )
    else:
        copy = request.form.get("copy")
        member = request.form.get("member")
        bdate = request.form.get("bdate")
        ddate = request.form.get("ddate")
        rdate = request.form.get("rdate")
        fine = request.form.get("fine")

        # Step 1: Validate Copy existence and status (US-2: issuing an already Issued copy must fail)
        cur.execute("SELECT Status FROM COPY WHERE Copy_ID=%s", (copy,))
        copy_res = cur.fetchone()
        if not copy_res:
            return render_template(
                "borrowedbooksadd.html",
                username=current_user.username,
                user_type=current_user.user_type.capitalize(),
                error=f"Copy ID '{copy}' does not exist.",
                copy=copy, member=member, bdate=bdate, ddate=ddate, rdate=rdate, fine=fine
            )

        if copy_res[0] != "Available":
            return render_template(
                "borrowedbooksadd.html",
                username=current_user.username,
                user_type=current_user.user_type.capitalize(),
                error=f"Cannot issue copy '{copy}': Current status is '{copy_res[0]}'. Only 'Available' copies can be issued.",
                copy=copy, member=member, bdate=bdate, ddate=ddate, rdate=rdate, fine=fine
            )

        # Step 2: Validate Member existence
        cur.execute("SELECT Member_ID FROM MEMBER WHERE Member_ID=%s", (member,))
        if not cur.fetchone():
            return render_template(
                "borrowedbooksadd.html",
                username=current_user.username,
                user_type=current_user.user_type.capitalize(),
                error=f"Member ID '{member}' does not exist.",
                copy=copy, member=member, bdate=bdate, ddate=ddate, rdate=rdate, fine=fine
            )

        # Step 3: Wrap Book Issue in atomic transaction (NFR-05)
        try:
            conn.begin()
            cur.execute("""
                INSERT INTO BORROWING (Copy_ID, Member_ID, Issue_Date, Due_Date, Return_Date, Fine_Amount) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """, [copy, member, bdate, ddate, rdate if rdate else None, fine if fine else 0.00])
            cur.execute("UPDATE COPY SET Status='Issued' WHERE Copy_ID=%s", (copy,))
            conn.commit()
            return redirect("/admin/borrowedbooks")
        except Exception as e:
            conn.rollback()
            return render_template(
                "borrowedbooksadd.html",
                username=current_user.username,
                user_type=current_user.user_type.capitalize(),
                error=f"Transaction failed and was rolled back: {str(e)}",
                copy=copy, member=member, bdate=bdate, ddate=ddate, rdate=rdate, fine=fine
            )

@app.route("/admin/borrowedbooks/update/<id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def borrowedbooks_update(id):
    conn, cur = ensure_db()
    if request.method == "GET":
        cur.execute("SELECT Issue_Date, Due_Date, Return_Date, Fine_Amount FROM BORROWING WHERE Borrow_ID=%s", (id,))
        result = cur.fetchone()
        return render_template(
            "borrowedbooksupdate.html",
            username=current_user.username,
            user_type=current_user.user_type.capitalize(),
            id=id,
            bdate=result[0],
            ddate=result[1],
            rdate=result[2],
            fine=result[3]
        )
    else:
        bdate = request.form.get("bdate")
        ddate = request.form.get("ddate")
        rdate = request.form.get("rdate")
        fine = request.form.get("fine")

        # Dynamic fine rate policy
        daily_fine_rate = float(get_policy("FINE_RATE_PER_DAY", "10.00"))

        try:
            conn.begin()
            cur.execute("SELECT Copy_ID FROM BORROWING WHERE Borrow_ID=%s", (id,))
            b_row = cur.fetchone()
            copy_id = b_row[0] if b_row else None

            fine_val = fine if fine else 0.00
            if rdate and ddate:
                r_dt = datetime.strptime(str(rdate), "%Y-%m-%d").date()
                d_dt = datetime.strptime(str(ddate), "%Y-%m-%d").date()
                if r_dt > d_dt:
                    fine_val = float((r_dt - d_dt).days * daily_fine_rate)

            cur.execute("""
                UPDATE BORROWING 
                SET Issue_Date=%s, Due_Date=%s, Return_Date=%s, Fine_Amount=%s 
                WHERE Borrow_ID=%s
            """, [bdate, ddate, rdate if rdate else None, fine_val, id])

            if copy_id:
                new_status = "Available" if rdate else "Issued"
                cur.execute("UPDATE COPY SET Status=%s WHERE Copy_ID=%s", [new_status, copy_id])

            conn.commit()
            return redirect("/admin/borrowedbooks")
        except Exception as e:
            conn.rollback()
            return render_template(
                "borrowedbooksupdate.html",
                username=current_user.username,
                user_type=current_user.user_type.capitalize(),
                id=id,
                bdate=bdate,
                ddate=ddate,
                rdate=rdate,
                fine=fine,
                error=f"Transaction failed and was rolled back: {str(e)}"
            )

@app.route("/admin/borrowedbooks/return/<id>")
@login_required
@role_required("admin")
def borrowedbooks_quick_return(id):
    """Atomic quick-return endpoint with dynamic policy fine calculation (NFR-05, US-2, US-7)."""
    conn, cur = ensure_db()
    today_str = datetime.today().strftime('%Y-%m-%d')
    today_dt = datetime.today().date()
    daily_fine_rate = float(get_policy("FINE_RATE_PER_DAY", "10.00"))

    try:
        conn.begin()
        cur.execute("SELECT Copy_ID, Due_Date FROM BORROWING WHERE Borrow_ID=%s", (id,))
        row = cur.fetchone()
        if row:
            copy_id, due_date = row[0], row[1]
            fine = 0.00
            if isinstance(due_date, str):
                due_dt = datetime.strptime(due_date, "%Y-%m-%d").date()
            else:
                due_dt = due_date

            if today_dt > due_dt:
                fine = float((today_dt - due_dt).days * daily_fine_rate)

            cur.execute("UPDATE BORROWING SET Return_Date=%s, Fine_Amount=%s WHERE Borrow_ID=%s", [today_str, fine, id])
            if copy_id:
                cur.execute("UPDATE COPY SET Status='Available' WHERE Copy_ID=%s", (copy_id,))
        conn.commit()
    except Exception:
        conn.rollback()

    return redirect("/admin/borrowedbooks")

# ----------------- ADMIN BOOK REQUEST DECISIONS (FR-20, FR-21) ----------------- #

@app.route("/admin/bookrequests/remove/<id>")
@login_required
@role_required("admin")
def bookrequests_remove(id):
    conn, cur = ensure_db()
    try:
        conn.begin()
        cur.execute("DELETE FROM REQUEST WHERE Request_ID=%s", (id,))
        conn.commit()
    except Exception:
        conn.rollback()
    return redirect("/admin/bookrequests")

@app.route("/admin/bookrequests/update/<id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def bookrequests_update(id):
    conn, cur = ensure_db()
    if request.method == "GET":
        cur.execute("""
            SELECT Status, Decision_Note, Requested_Title, Requester_ID, Request_Type 
            FROM REQUEST WHERE Request_ID=%s
        """, (id,))
        result = cur.fetchone()
        return render_template(
            "bookrequestsupdate.html",
            username=current_user.username,
            user_type=current_user.user_type.capitalize(),
            id=id,
            status=result[0] if result else "Pending",
            decision_note=result[1] if (result and result[1]) else "",
            title=result[2] if result else "",
            requester=result[3] if result else "",
            req_type=result[4] if result else ""
        )
    else:
        status = request.form.get("status")
        decision_note = request.form.get("decision_note")

        try:
            conn.begin()
            cur.execute("""
                UPDATE REQUEST 
                SET Status=%s, Decision_Note=%s 
                WHERE Request_ID=%s
            """, [status, decision_note, id])
            conn.commit()
            return redirect("/admin/bookrequests")
        except Exception:
            conn.rollback()
            return redirect("/admin/bookrequests")

if __name__ == "__main__":
    app.run(debug=True)

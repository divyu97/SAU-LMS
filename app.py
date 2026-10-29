from flask import Flask, render_template, request, redirect
from flask_bcrypt import Bcrypt
from flask_login import login_user, LoginManager, login_required, logout_user, current_user
import pymysql
from datetime import datetime

class User:
    def __init__(self, username, user_type):
        self.username = username
        self.user_type = user_type
        self.is_authenticated = True

    def get_id(self):
        return self.username
        

app = Flask(__name__)
app.config["SECRET_KEY"] = "CSE231"

bcrypt = Bcrypt(app)

connection = pymysql.connect(host="localhost", user="root", password="root", database="southasianuniversitylms")
cursor = connection.cursor()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    cursor.execute("SELECT Type FROM MEMBER WHERE Username=%s", user_id)
    user_type = cursor.fetchone()[0]
    return User(user_id, user_type.lower())

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        # cursor.execute("INSERT INTO MEMBER (Member_ID, Name, Email, Type, Username, Password) VALUES (%s, %s, %s, %s, %s, %s)", ["A777", "Divyendu", "abc@gmail.com", "Admin", "root", bcrypt.generate_password_hash("root").decode("utf-8")])
        # connection.commit()
        return render_template("login.html")
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        user_type = request.form.get("user-type")

        cursor.execute("SELECT Password, Type FROM MEMBER WHERE Username=%s", username)
        row = cursor.fetchone()

        if bcrypt.check_password_hash(row[0], password) and user_type == row[1].lower():
            user = User(username, user_type)
            login_user(user, force=True)
            if user_type == "admin":
                return redirect("/admin")
            elif user_type == "faculty":
                return redirect("/faculty")
            return redirect("/student") 

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

        cursor.execute("INSERT INTO STUDENT_REQUEST (Name, Major, Department, Enrolment_No, Email, Username, Password, Request_Date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", [fullname, major, dept, enrolment, email, username, password, today])
        connection.commit()

        return redirect("/signup")

@app.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    return redirect("/")

@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    if current_user.user_type == "admin":
        return redirect("/admin/memreq")

@app.route("/admin/<section>", methods=["GET", "POST"])
@login_required
def admin_section(section):
    if current_user.user_type == "admin":
        if section == "memreq":
            cursor.execute("SELECT * FROM STUDENT_REQUEST")
            result = cursor.fetchall()
            rows = []
            reqIDS = []
            for row in result:
                rows.append(row[1:])
                reqIDS.append(row[0])
            return render_template(section + ".html", username=current_user.username, user_type=current_user.user_type.capitalize(), cols=["Full Name", "Major", "Deparment", "Enrolment No.", "Email", "Username", "Password", "Request Date"], rows=rows, reqIDS=reqIDS)
        elif section == "viewfac":
            cursor.execute("""SELECT M.Member_ID, M.Name AS "Full Name", F.Office_No, F.Department,
                            M.Email, M.Username, M.Password FROM MEMBER M JOIN
                            FACULTY F ON M.Member_ID = F.Member_ID
                           """)
            result = cursor.fetchall()
            rows = []
            memIDS = []
            for row in result:
                rows.append(row[1:])
                memIDS.append(row[0])
            return render_template(section + ".html", username=current_user.username, user_type=current_user.user_type.capitalize(), cols=["Full Name", "Office No.", "Department", "Email", "Username", "Password"], rows=rows, memIDS=memIDS)
        elif section == "viewstud":
            cursor.execute("""SELECT M.Member_ID, M.Name AS "Full Name", S.Major,
                            S.Department, S.Enrolment_No, M.Email, M.Username, M.Password
                            FROM MEMBER M JOIN STUDENT S ON M.Member_ID =
                            S.Member_ID;
                        """)
            result = cursor.fetchall()
            rows = []
            memIDS = []
            for row in result:
                rows.append(row[1:])
                memIDS.append(row[0])
            return render_template(section + ".html", username=current_user.username, user_type=current_user.user_type.capitalize(), cols=["Full Name", "Major", "Deparment", "Enrolment No.", "Email", "Username", "Password"], rows=rows, memIDS=memIDS)
        elif section == "viewbooks":
            cursor.execute("SELECT * FROM BOOK")
            rows = cursor.fetchall()
            return render_template(section + ".html", username=current_user.username, user_type=current_user.user_type.capitalize(), cols=["ISBN", "Title", "Subject", "Publication Year", "Price", "Publisher ID"], rows=rows)
        elif section == "viewcopies":
            cursor.execute("SELECT * FROM COPY")
            rows = cursor.fetchall()
            return render_template(section + ".html", username=current_user.username, user_type=current_user.user_type.capitalize(), cols=["Copy ID", "ISBN", "Acquisition Date", "Status"], rows=rows)
        elif section == "borrowedbooks":
            cursor.execute("SELECT * FROM BORROWING")
            rows = cursor.fetchall()
            return render_template(section + ".html", username=current_user.username, user_type=current_user.user_type.capitalize(), cols=["Borrow ID", "Copy ID", "Member ID", "Borrow Date", "Due Date", "Return Date", "Fine Amount"], rows=rows)
        elif section == "bookrequests":
            cursor.execute("SELECT * FROM REQUEST")
            rows = cursor.fetchall()
            return render_template(section + ".html", username=current_user.username, user_type=current_user.user_type.capitalize(), cols=["Request ID", "Member ID", "Requested Item Identifier", "Author", "Request Date", "Request Type", "Status"], rows=rows)
        elif section == "genrep":
            cursor.execute("""SELECT
                        B.ISBN,
                        B.Title,
                        B.Subject,
                        B.Price,
                        MIN(C.Acquisition_Date) AS First_Acquisition_Date,
                        COUNT(T.Borrow_ID) AS Total_Usage_Count,
                        COUNT(C.Copy_ID) AS Total_Copies_Purchased -- CRITICAL FOR COMPARISON
                        FROM
                        BOOK B
                        JOIN
                        COPY C ON B.ISBN = C.ISBN
                        LEFT JOIN
                        BORROWING T ON C.Copy_ID = T.Copy_ID
                        GROUP BY
                        B.ISBN, B.Title, B.Subject, B.Price
                        HAVING
                        -- 1. Must be old (> 1 year)
                        MIN(C.Acquisition_Date) < DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
                        -- 2. Total usage is low (borrowed less than 2 times overall)
                        AND COUNT(T.Borrow_ID) < 2
                        -- 3. Total usage is less than the number of copies
                        AND COUNT(T.Borrow_ID) < COUNT(C.Copy_ID)
                        ORDER BY
                        Total_Usage_Count ASC, First_Acquisition_Date ASC;
                    """)
            underutilized = cursor.fetchall()
            cursor.execute("""SELECT
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
                        -- Condition 1: All copies are currently issued
                        Total_Copies = Issued_Copies
                        -- Condition 2: There is active demand (pending requests for more copies)
                        AND Pending_Requests > 0
                        ORDER BY
                        Pending_Requests DESC, Total_Copies DESC;
                    """)
            highdemand = cursor.fetchall()
            return render_template(section + ".html", username=current_user.username, user_type=current_user.user_type.capitalize(), cols1=["ISBN", "Title", "Subject", "Price", "First Acquisition Date", "Total Usage Count", "Total Copies Purchased"], cols2=["ISBN", "Title", "Total Copies", "Issued Copies", "Pending Requests"], borrows=underutilized, titles=highdemand)
        elif section == "genrep2":
            cursor.execute("""SELECT
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
            usage = cursor.fetchall()
            cursor.execute("""SELECT
                            R.Requested_Title,
                            R.Author,
                            COUNT(R.Request_ID) AS Total_Faculty_Requests
                        FROM
                            REQUEST R
                        JOIN
                            MEMBER M ON R.Requester_ID = M.Member_ID
                        WHERE
                            M.Type = 'Faculty'
                            AND R.Status IN ('Pending', 'Rejected') -- Not yet successfully fulfilled
                        GROUP BY
                            R.Requested_Title, R.Author
                        ORDER BY
                            Total_Faculty_Requests DESC
                        LIMIT 5
                    """)
            requests = cursor.fetchall()
            cursor.execute("""SELECT
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
            books = cursor.fetchall()
            return render_template(section + ".html", username=current_user.username, user_type=current_user.user_type.capitalize(), cols1=["Member Type", "Total Unique Titles Borrowed"], cols2=["Requested Title", "Author", "Total Faculty Requests"], cols3=["Subject", "Total Copies", "Available Copies Count"], usage=usage, requests=requests, books=books)

@app.route("/admin/memreq/approve/<id>", methods=["GET", "POST"])
@login_required
def mem_req_approve(id):
    if current_user.user_type == "admin":
        if request.method == "POST":
            member = request.form.get("member")
            cursor.execute("SELECT * FROM STUDENT_REQUEST WHERE Request_ID=%s", id)
            result = cursor.fetchone()
            cursor.execute("INSERT INTO MEMBER (Member_ID, Name, Email, Type, Username, Password) VALUES (%s, %s, %s, %s, %s, %s)", [member, result[1], result[5], "Student", result[6], bcrypt.generate_password_hash(result[7]).decode("utf-8")])
            cursor.execute("INSERT INTO STUDENT (Member_ID, Department, Major, Enrolment_No) VALUES (%s, %s, %s, %s)", [member, result[3], result[2], result[4]])
            cursor.execute("DELETE FROM STUDENT_REQUEST WHERE Request_ID=%s", id)
            connection.commit()
            return redirect("/admin/memreq")
        else:
            return render_template("memreqapprove.html", id=id, username=current_user.username, user_type=current_user.user_type.capitalize())

@app.route("/admin/memreq/reject/<id>")
@login_required
def mem_req_reject(id):
    if current_user.user_type == "admin":
        cursor.execute("DELETE FROM STUDENT_REQUEST WHERE Request_ID=%s", id)
        connection.commit()
        return redirect("/admin/memreq")
    
@app.route("/admin/viewfac/remove/<id>")
@login_required
def fac_remove(id):
    if current_user.user_type == "admin":
        cursor.execute("DELETE FROM FACULTY WHERE Member_ID=%s", id)
        cursor.execute("DELETE FROM BORROWING WHERE Member_ID=%s", id)
        cursor.execute("DELETE FROM REQUEST WHERE Requester_ID=%s", id)
        cursor.execute("DELETE FROM MEMBER WHERE Member_ID=%s", id)
        connection.commit()

        return redirect("/admin/viewfac")

@app.route("/admin/viewfac/update/<id>", methods=["GET", "POST"])
@login_required
def fac_update(id):
    if current_user.user_type == "admin":
        if request.method == "GET":
            cursor.execute("""SELECT M.Name AS "Full Name", F.Office_No, F.Department,
                            M.Email FROM MEMBER M JOIN
                            FACULTY F ON M.Member_ID = F.Member_ID AND M.Member_ID=%s
                           """, id)
            
            result = cursor.fetchone()

            return render_template("facupdate.html", username=current_user.username, user_type=current_user.user_type.capitalize(), id=id, fullname=result[0], office=result[1], dept=result[2], email=result[3])
        else:
            fullname = request.form.get("name")
            office = request.form.get("office")
            dept = request.form.get("dept")
            email = request.form.get("email")
            
            cursor.execute("UPDATE MEMBER SET Name=%s, Email=%s WHERE Member_ID=%s", [fullname, email, id])
            cursor.execute("UPDATE FACULTY SET Office_No=%s, Department=%s WHERE Member_ID=%s", [office, dept, id])
            connection.commit()

            return redirect("/admin/viewfac")

@app.route("/admin/viewfac/new", methods=["GET", "POST"])
@login_required
def fac_add():
    if current_user.user_type == "admin":
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
            hashed_pw = bcrypt.generate_password_hash(password)
            
            cursor.execute("""INSERT INTO MEMBER (Member_ID, Name, Email, Type, Username,
                        Password) VALUES (%s, %s, %s, %s, %s, %s)
                           """, [id, fullname, email, "Faculty", username, hashed_pw])
            cursor.execute("""INSERT INTO FACULTY (Member_ID,
                        Office_No, Department) VALUES (%s, %s, %s)
                           """, [id, office, dept])
            connection.commit()

            return redirect("/admin/viewfac")

@app.route("/admin/viewstud/remove/<id>")
@login_required
def stud_remove(id):
    if current_user.user_type == "admin":
        cursor.execute("DELETE FROM STUDENT WHERE Member_ID=%s", id)
        cursor.execute("DELETE FROM BORROWING WHERE Member_ID=%s", id)
        cursor.execute("DELETE FROM REQUEST WHERE Requester_ID=%s", id)
        cursor.execute("DELETE FROM MEMBER WHERE Member_ID=%s", id)
        connection.commit()

        return redirect("/admin/viewstud")

@app.route("/admin/viewstud/update/<id>", methods=["GET", "POST"])
@login_required
def stud_update(id):
    if current_user.user_type == "admin":
        if request.method == "GET":
            cursor.execute("""SELECT M.Name AS "Full Name", S.Major,
                            S.Department, S.Enrolment_No, M.Email
                            FROM MEMBER M JOIN STUDENT S ON M.Member_ID =
                            S.Member_ID AND M.Member_ID=%s
                        """, id)
            
            result = cursor.fetchone()

            return render_template("studupdate.html", username=current_user.username, user_type=current_user.user_type.capitalize(), id=id, fullname=result[0], major=result[1], dept=result[2], enrolment=result[3], email=result[4])
        else:
            fullname = request.form.get("name")
            major = request.form.get("major")
            dept = request.form.get("dept")
            enrolment = request.form.get("enrolment")
            email = request.form.get("email")

            cursor.execute("UPDATE MEMBER SET Name=%s, Email=%s WHERE Member_ID=%s", [fullname, email, id])
            cursor.execute("UPDATE STUDENT SET Major=%s, Department=%s, Enrolment_No=%s WHERE Member_ID=%s", [major, dept, enrolment, id])
            connection.commit()

            return redirect("/admin/viewstud")
        
@app.route("/admin/viewbooks/remove/<isbn>")
@login_required
def books_remove(isbn):
    if current_user.user_type == "admin":
        cursor.execute("DELETE FROM COPY WHERE ISBN=%s", isbn)
        cursor.execute("DELETE FROM BOOK_AUTHOR WHERE ISBN=%s", isbn)
        cursor.execute("DELETE FROM BOOK WHERE ISBN=%s", isbn)
        connection.commit()
        return redirect("/admin/viewbooks")

@app.route("/admin/viewbooks/new", methods=["GET", "POST"])
@login_required
def books_add():
    if current_user.user_type == "admin":
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
            cursor.execute("INSERT INTO BOOK (ISBN, Title, Subject, Pub_Year, Price, Pub_ID) VALUES (%s, %s, %s, %s, %s, %s)", [isbn, title, subject, year, price, publisher])
            authors = authors.split(",")
            for index, author in enumerate(authors, start=1):
                cursor.execute("SELECT * FROM AUTHOR WHERE Name=%s", author)
                row = cursor.fetchall()
                if len(row) == 0:
                    cursor.execute("INSERT INTO AUTHOR (Name) VALUES (%s)", author)
                cursor.execute("SELECT Author_ID FROM AUTHOR WHERE Name=%s", author)
                id = cursor.fetchone()[0]
                cursor.execute("INSERT INTO BOOK_AUTHOR (ISBN, Author_ID, Author_Order) VALUES (%s, %s, %s)", [isbn, id, index])   
            connection.commit()
            return redirect("/admin/viewbooks")

@app.route("/admin/viewbooks/addcopy/<isbn>", methods=["GET", "POST"])
@login_required
def bookcopy_add(isbn):
    if current_user.user_type == "admin":
        if request.method == "GET":
            return render_template("bookcopyadd.html", username=current_user.username, user_type=current_user.user_type.capitalize(), isbn=isbn)
        else:
            copy = request.form.get("copy")
            adate = request.form.get("adate")
            status = request.form.get("status")
            cursor.execute("INSERT INTO COPY (Copy_ID, ISBN, Acquisition_Date, Status) VALUES (%s, %s, %s, %s)", [copy, isbn, adate, status])
            connection.commit()
            return redirect("/admin/viewbooks")

@app.route("/admin/viewcopies/remove/<id>")
@login_required
def copies_remove(id):
    if current_user.user_type == "admin":
        cursor.execute("DELETE FROM BORROWING WHERE Copy_ID=%s", id)
        cursor.execute("DELETE FROM COPY WHERE Copy_ID=%s", id)
        connection.commit()
        return redirect("/admin/viewcopies")

@app.route("/admin/viewcopies/update/<id>", methods=["GET", "POST"])
@login_required
def copies_update(id):
    if current_user.user_type == "admin":
        if request.method == "GET":
            cursor.execute("SELECT Status FROM COPY WHERE Copy_ID=%s", id)
            status = cursor.fetchone()[0]
            return render_template("copiesupdate.html", username=current_user.username, user_type=current_user.user_type.capitalize(), id=id, status=status)
        else:
            status = request.form.get("status")
            cursor.execute("UPDATE COPY SET Status=%s WHERE Copy_ID=%s", [status, id])
            connection.commit()
            return redirect("/admin/viewcopies")
        
@app.route("/admin/borrowedbooks/remove/<id>")
@login_required
def borrowedbooks_remove(id):
    if current_user.user_type == "admin":
        cursor.execute("DELETE FROM BORROWING WHERE Borrow_ID=%s", id)
        connection.commit()
        return redirect("/admin/borrowedbooks")
    
@app.route("/admin/borrowedbooks/update/<id>", methods=["GET", "POST"])
@login_required
def borrowedbooks_update(id):
    if current_user.user_type == "admin":
        if request.method == "GET":
            cursor.execute("SELECT Issue_Date, Due_Date, Return_Date, Fine_Amount FROM BORROWING WHERE Borrow_ID=%s", id)
            result = cursor.fetchone()
            return render_template("borrowedbooksupdate.html", username=current_user.username, user_type=current_user.user_type.capitalize(), id=id, bdate=result[0], ddate=result[1], rdate=result[2], fine=result[3])
        else:
            bdate = request.form.get("bdate")
            ddate = request.form.get("ddate")
            rdate = request.form.get("rdate")
            fine = request.form.get("fine")
            cursor.execute("UPDATE BORROWING SET Issue_Date=%s, Due_Date=%s, Return_Date=%s, Fine_Amount=%s WHERE Borrow_ID=%s", [bdate, ddate, rdate, fine, id])
            connection.commit()
            return redirect("/admin/borrowedbooks")

@app.route("/admin/borrowedbooks/new", methods=["GET", "POST"])
@login_required
def borrowedbooks_add():
    if current_user.user_type == "admin":
        if request.method == "GET":
            return render_template("borrowedbooksadd.html", username=current_user.username, user_type=current_user.user_type.capitalize())
        else:
            copy = request.form.get("copy")
            member = request.form.get("member")
            bdate = request.form.get("bdate")
            ddate = request.form.get("ddate")
            rdate = request.form.get("rdate")
            fine = request.form.get("fine")
            cursor.execute("INSERT INTO BORROWING (Copy_ID, Member_ID, Issue_Date, Due_Date, Return_Date, Fine_Amount) VALUES (%s, %s, %s, %s, %s, %s)", [copy, member, bdate, ddate, rdate, fine])
            cursor.execute("UPDATE COPY SET Status=%s WHERE Copy_ID=%s", ["Issued", copy])
            connection.commit()
            return redirect("/admin/borrowedbooks")

@app.route("/admin/bookrequests/remove/<id>")
@login_required
def bookrequests_remove(id):
    if current_user.user_type == "admin":
        cursor.execute("DELETE FROM REQUEST WHERE Request_ID=%s", id)
        connection.commit()
        return redirect("/admin/bookrequests")

@app.route("/admin/bookrequests/update/<id>", methods=["GET", "POST"])
@login_required
def bookrequests_update(id):
    if current_user.user_type == "admin":
        if request.method == "GET":
            cursor.execute("SELECT Status FROM REQUEST WHERE Request_ID=%s", id)
            status = cursor.fetchone()[0]
            return render_template("bookrequestsupdate.html", username=current_user.username, user_type=current_user.user_type.capitalize(), id=id, status=status)
        else:
            status = request.form.get("status")
            cursor.execute("UPDATE REQUEST SET Status=%s WHERE Request_ID=%s", [status, id])
            connection.commit()
            return redirect("/admin/bookrequests")
        
if __name__ == "__main__":
    app.run(debug=True)
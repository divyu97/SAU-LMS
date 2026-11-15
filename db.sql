DROP DATABASE IF EXISTS SouthAsianUniversityLMS;

CREATE DATABASE SouthAsianUniversityLMS;
-- Select the database for use
USE SouthAsianUniversityLMS;

-- A. Core Entities
CREATE TABLE PUBLISHER (
Pub_ID INT AUTO_INCREMENT PRIMARY KEY,
Name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE AUTHOR (
Author_ID INT AUTO_INCREMENT PRIMARY KEY,
Name VARCHAR(100) NOT NULL
);

CREATE TABLE BOOK (
ISBN VARCHAR(20) PRIMARY KEY,
Title VARCHAR(200) NOT NULL,
Subject VARCHAR(50) NOT NULL,
Pub_Year YEAR,
Price DECIMAL(8,2) NOT NULL,
Pub_ID INT,
FOREIGN KEY (Pub_ID) REFERENCES PUBLISHER(Pub_ID)
);

CREATE TABLE BOOK_AUTHOR (
ISBN VARCHAR(20),
Author_ID INT,
Author_Order INT,
PRIMARY KEY (ISBN, Author_ID),
FOREIGN KEY (ISBN) REFERENCES BOOK(ISBN),
FOREIGN KEY (Author_ID) REFERENCES AUTHOR(Author_ID)
);

-- B. User Hierarchy and Request Tables
CREATE TABLE MEMBER (
Member_ID VARCHAR(10) PRIMARY KEY,
Name VARCHAR(100) NOT NULL,
Email VARCHAR(100) UNIQUE,
Type VARCHAR(20) NOT NULL,
Username VARCHAR(50) UNIQUE NOT NULL, -- NEW: For Login
Password VARCHAR(255) NOT NULL, -- Hashed with bcrypt
CHECK (Type IN ('Student', 'Faculty', 'Admin'))
);

CREATE TABLE STUDENT (
Member_ID VARCHAR(10) PRIMARY KEY,
Department VARCHAR(50) NOT NULL,
Major VARCHAR(50),
Enrolment_No VARCHAR(30) UNIQUE NOT NULL,
FOREIGN KEY (Member_ID) REFERENCES MEMBER(Member_ID)
);

CREATE TABLE FACULTY (
Member_ID VARCHAR(10) PRIMARY KEY,
Office_No VARCHAR(10),
Department VARCHAR(50) NOT NULL,
FOREIGN KEY (Member_ID) REFERENCES MEMBER(Member_ID)
);

-- STUDENT_REQUEST (Password is bcrypt-hashed)
CREATE TABLE STUDENT_REQUEST (
Request_ID INT AUTO_INCREMENT PRIMARY KEY,
Name VARCHAR(100) NOT NULL,
Major VARCHAR(50) NOT NULL,
Department VARCHAR(50) NOT NULL,
Enrolment_No VARCHAR(30) UNIQUE NOT NULL,
Email VARCHAR(100) UNIQUE NOT NULL,
Username VARCHAR(50) UNIQUE NOT NULL, -- Must also be unique here
Password VARCHAR(255) NOT NULL, -- Hashed with bcrypt
Request_Date DATE NOT NULL
);

-- C. Transactional Entities
CREATE TABLE COPY (
Copy_ID VARCHAR(15) PRIMARY KEY,
ISBN VARCHAR(20),
Acquisition_Date DATE NOT NULL,
Status VARCHAR(20) NOT NULL,
CHECK (Status IN ('Available', 'Issued', 'Lost')),
FOREIGN KEY (ISBN) REFERENCES BOOK(ISBN)
);

CREATE TABLE BORROWING (
Borrow_ID INT AUTO_INCREMENT PRIMARY KEY,
Copy_ID VARCHAR(15),
Member_ID VARCHAR(10),
Issue_Date DATE NOT NULL,
Due_Date DATE NOT NULL,
Return_Date DATE,
Fine_Amount DECIMAL(6,2) DEFAULT 0.00,
FOREIGN KEY (Copy_ID) REFERENCES COPY(Copy_ID),
FOREIGN KEY (Member_ID) REFERENCES MEMBER(Member_ID)
);

CREATE TABLE REQUEST (
Request_ID INT AUTO_INCREMENT PRIMARY KEY,
Requester_ID VARCHAR(10),
Requested_Title VARCHAR(200) NOT NULL,
Author VARCHAR(100),
Request_Date DATE NOT NULL,
Request_Type VARCHAR(20) NOT NULL,
Status VARCHAR(20) DEFAULT 'Pending',
Decision_Note TEXT,
CHECK (Request_Type IN ('New Title', 'More Copies')),
CHECK (Status IN ('Pending', 'Acquired', 'Rejected')),
FOREIGN KEY (Requester_ID) REFERENCES MEMBER(Member_ID)
);

-- D. Configuration & System Policies (FR-27, FR-28, NFR-09)
CREATE TABLE POLICY (
Policy_Key VARCHAR(50) PRIMARY KEY,
Policy_Name VARCHAR(100) NOT NULL,
Policy_Value VARCHAR(100) NOT NULL,
Description VARCHAR(255)
);

INSERT INTO POLICY (Policy_Key, Policy_Name, Policy_Value, Description) VALUES
('LOAN_PERIOD_DAYS', 'Standard Loan Period (Days)', '14', 'Number of days allowed before a borrowed copy becomes overdue'),
('FINE_RATE_PER_DAY', 'Daily Overdue Fine Rate (INR)', '10.00', 'Fine charged per overdue day upon return'),
('DEAD_STOCK_YEARS', 'Dead Stock Age Threshold (Years)', '1', 'Acquisition age threshold to consider a title for underutilization evaluation'),
('DEAD_STOCK_USAGE_LIMIT', 'Dead Stock Usage Limit', '2', 'Maximum borrowing count threshold for dead stock classification');

-- A. Core Entities Seed Data (Publishers, Authors, and Books for all departments)
INSERT INTO PUBLISHER (Pub_ID, Name) VALUES
(101, 'Tech Books Inc.'), (102, 'Academic Press'), (103, 'Global Texts'),
(104, 'Pearson Education'), (105, 'McGraw Hill');

INSERT INTO AUTHOR (Author_ID, Name) VALUES
(201, 'Alice Smith'), (202, 'Bob Johnson'), (203, 'Charles Lee'), (204, 'Thomas Cormen'),
(205, 'Abraham Silberschatz'), (206, 'William Strunk Jr.'), (207, 'Shigley'), (208, 'J. R. R. Tolkien');

INSERT INTO BOOK (ISBN, Title, Subject, Pub_Year, Price, Pub_ID) VALUES
('978-0262033848', 'Introduction to Algorithms', 'Algorithms', 2009, 85.00, 102),
('978-0072958869', 'Database System Concepts', 'DBMS', 2020, 75.00, 105),
('978-1234567890', 'DBMS Handbook', 'DBMS', 2022, 50.00, 101),
('978-0987654321', 'Advanced Algorithms', 'Algorithms', 2020, 45.50, 102),
('978-5555555555', 'Introductory Poetry', 'Literature', 2018, 25.00, 103),
('978-1111111111', 'Foundations of AI', 'AI', 2023, 60.00, 101),
('978-0205830917', 'The Elements of Style', 'Writing', 2011, 15.00, 104),
('978-0073398204', 'Shigley Mechanical Engineering Design', 'Mechanical', 2015, 95.00, 105),
('978-0618526543', 'The Lord of the Rings', 'Fiction', 1954, 30.00, 103);

INSERT INTO BOOK_AUTHOR (ISBN, Author_ID, Author_Order) VALUES
('978-0262033848', 204, 1), ('978-0072958869', 205, 1), ('978-1234567890', 201, 1),
('978-0987654321', 202, 1), ('978-5555555555', 203, 1), ('978-1111111111', 201, 1),
('978-1111111111', 202, 2), ('978-0205830917', 206, 1), ('978-0073398204', 207, 1),
('978-0618526543', 208, 1);

-- B. User Hierarchy (All default passwords 'pass123' hashed with bcrypt)
INSERT INTO MEMBER (Member_ID, Name, Email, Type, Username, Password) VALUES
('S1001', 'Aarav Sharma', 'aarav@sau.edu', 'Student', 'aaravs', '$2b$12$qCUn94o0rHEx2wP1dczuY.3WSGBqb17l5mllxOxI1nHOf1qgC4akm'),
('S1002', 'Bhavna Reddy', 'bhavna@sau.edu', 'Student', 'bhavnar', '$2b$12$qCUn94o0rHEx2wP1dczuY.3WSGBqb17l5mllxOxI1nHOf1qgC4akm'),
('S1003', 'Chirag Desai', 'chirag@sau.edu', 'Student', 'chiragd', '$2b$12$qCUn94o0rHEx2wP1dczuY.3WSGBqb17l5mllxOxI1nHOf1qgC4akm'),
('F5001', 'Dr. Priya Das', 'priya.d@sau.edu', 'Faculty', 'priyad', '$2b$12$qCUn94o0rHEx2wP1dczuY.3WSGBqb17l5mllxOxI1nHOf1qgC4akm'),
('A9999', 'Admin User', 'admin@sau.edu', 'Admin', 'admin', '$2b$12$qCUn94o0rHEx2wP1dczuY.3WSGBqb17l5mllxOxI1nHOf1qgC4akm');

INSERT INTO STUDENT (Member_ID, Department, Major, Enrolment_No) VALUES
('S1001', 'Computer Science', 'Data Science', 'SAU/CS/BTECH/2024/001'),
('S1002', 'Computer Science', 'Cyber Security', 'SAU/CS/BTECH/2024/002'),
('S1003', 'Arts', 'English Literature', 'SAU/ARTS/MA/2023/005');

INSERT INTO FACULTY (Member_ID, Office_No, Department) VALUES
('F5001', 'E205', 'Computer Science');

-- C. Transactional Entities and Demand
INSERT INTO COPY (Copy_ID, ISBN, Acquisition_Date, Status) VALUES
('C001', '978-1234567890', '2023-01-15', 'Issued'),
('C002', '978-1234567890', '2023-01-15', 'Issued'),
('C003', '978-1234567890', '2024-05-01', 'Available'),
('C004', '978-0987654321', '2020-11-10', 'Available'),
('C005', '978-5555555555', '2018-07-01', 'Available'),
('C006', '978-1111111111', '2024-01-01', 'Issued'),
('C007', '978-1111111111', '2024-01-01', 'Available'),
('C008', '978-0262033848', '2023-10-01', 'Available'),
('C009', '978-0072958869', '2023-10-01', 'Issued'),
('C010', '978-0072958869', '2023-10-01', 'Available'),
('C011', '978-0205830917', '2024-03-01', 'Available'),
('C012', '978-0073398204', '2023-05-01', 'Available');

INSERT INTO BORROWING (Copy_ID, Member_ID, Issue_Date, Due_Date, Return_Date, Fine_Amount) VALUES
('C001', 'S1001', '2025-10-01', '2025-10-15', '2025-10-14', 0.00),
('C002', 'S1002', '2025-11-01', '2025-11-15', NULL, 0.00),
('C006', 'S1001', '2025-11-15', '2025-11-30', NULL, 0.00),
('C005', 'S1003', '2025-01-01', '2025-01-15', '2025-01-15', 0.00),
('C009', 'F5001', '2025-11-10', '2025-11-25', NULL, 0.00),
('C001', 'F5001', '2025-11-10', '2025-11-25', NULL, 0.00);

INSERT INTO REQUEST (Requester_ID, Requested_Title, Author, Request_Date, Request_Type, Status, Decision_Note) VALUES
('S1002', 'Foundations of AI', 'Alice Smith', '2025-09-01', 'More Copies', 'Pending', NULL),
('S1001', 'Foundations of AI', 'Alice Smith', '2025-09-10', 'More Copies', 'Pending', NULL),
('F5001', 'New Quantum Computing Text', 'Various', '2025-10-20', 'New Title', 'Pending', NULL);

DELIMITER //
CREATE PROCEDURE Approve_Student_Membership (
IN request_id_param INT,
IN new_member_id_param VARCHAR(10) -- Admin provides a new unique Member_ID
)
BEGIN
-- Declare variables to hold request data
DECLARE req_name VARCHAR(100);
DECLARE req_email VARCHAR(100);
DECLARE req_major VARCHAR(50);
DECLARE req_dept VARCHAR(50);
DECLARE req_enrolment_no VARCHAR(30);
DECLARE req_username VARCHAR(50);
DECLARE req_password VARCHAR(255);
-- Start the transaction
START TRANSACTION;
-- 1. Retrieve the data from the request table
SELECT
Name, Email, Major, Department, Enrolment_No, Username, Password
INTO
req_name, req_email, req_major, req_dept, req_enrolment_no, req_username,
req_password
FROM
STUDENT_REQUEST
WHERE
Request_ID = request_id_param;
-- Check if the request exists
IF req_name IS NOT NULL THEN
-- 2. Insert into the MEMBER superclass table (req_password is already bcrypt-hashed)
INSERT INTO MEMBER (
Member_ID, Name, Email, Type, Username, Password
)
VALUES (
new_member_id_param, req_name, req_email, 'Student', req_username, req_password
);
-- 3. Insert into the STUDENT subclass table
INSERT INTO STUDENT (
Member_ID, Department, Major, Enrolment_No
)
VALUES (
new_member_id_param, req_dept, req_major, req_enrolment_no
);
-- 4. Delete the successful request from the request table
DELETE FROM STUDENT_REQUEST
WHERE Request_ID = request_id_param;
-- Commit the transaction if all steps succeeded
COMMIT;
ELSE
-- Rollback if the request_id was not found
ROLLBACK;
END IF;
END //
DELIMITER ;

-- Simulation of student registration and approval:
INSERT INTO STUDENT_REQUEST (Name, Major, Department, Enrolment_No, Email,
Username, Password, Request_Date)
VALUES ('Kavita Singh', 'Civil Engineering', 'Engineering', 'SAU/CIV/BTECH/2025/010',
'kavita@example.com', 'kavitas', '$2b$12$qCUn94o0rHEx2wP1dczuY.3WSGBqb17l5mllxOxI1nHOf1qgC4akm', CURDATE());
CALL Approve_Student_Membership(1, 'S1004');

-- Return Trigger with Dynamic Policy Fine Calculation (Reads from POLICY table, fallback 10.00/day)
DROP TRIGGER IF EXISTS Calculate_Fine_On_Return;
DELIMITER //
CREATE TRIGGER Calculate_Fine_On_Return
BEFORE UPDATE ON BORROWING
FOR EACH ROW
BEGIN
-- Declare a variable for the number of overdue days
DECLARE overdue_days INT;
DECLARE daily_fine DECIMAL(6,2) DEFAULT 10.00;
DECLARE policy_fine VARCHAR(100);

-- Query configured dynamic fine rate from POLICY table
SELECT Policy_Value INTO policy_fine FROM POLICY WHERE Policy_Key = 'FINE_RATE_PER_DAY' LIMIT 1;
IF policy_fine IS NOT NULL THEN
    SET daily_fine = CAST(policy_fine AS DECIMAL(6,2));
END IF;

-- Check if the Return_Date is being set and if overdue
IF NEW.Return_Date IS NOT NULL AND NEW.Return_Date > OLD.Due_Date THEN
    SET overdue_days = DATEDIFF(NEW.Return_Date, OLD.Due_Date);
    SET NEW.Fine_Amount = overdue_days * daily_fine;
ELSEIF NEW.Return_Date IS NOT NULL AND NEW.Return_Date <= OLD.Due_Date THEN
    SET NEW.Fine_Amount = 0.00;
END IF;
END //
DELIMITER ;

-- Verify Trigger Fine Calculation
UPDATE BORROWING
SET Return_Date = NULL, Fine_Amount = 0.00
WHERE Borrow_ID = 2;

UPDATE BORROWING
SET Return_Date = '2025-11-25'
WHERE Borrow_ID = 2;

-- SQL Query for Underutilized Books (Report 1)
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
MIN(C.Acquisition_Date) < DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
AND COUNT(T.Borrow_ID) < 2
AND COUNT(T.Borrow_ID) < COUNT(C.Copy_ID)
ORDER BY
Total_Usage_Count ASC, First_Acquisition_Date ASC;

-- Update one copy of Foundations of AI to Issued so Total_Copies = Issued_Copies for Report 1 demo
UPDATE COPY SET Status = 'Issued' WHERE Copy_ID = 'C007';

-- SQL Query for High-Demand Books (Report 1)
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

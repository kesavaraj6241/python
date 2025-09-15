import random
from contextlib import asynccontextmanager

import app
from dotenv import load_dotenv
from fastapi import FastAPI, Form, File, UploadFile, HTTPException,Request,Response
from datetime import datetime, timedelta
import smtplib
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import secrets
from pydantic import BaseModel
import os,json
# Allow all origins (for testing)

# ==============================
# Email Configuration
# ==============================
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

if not all([SMTP_SERVER, SMTP_PORT, USERNAME, PASSWORD]):
    raise ValueError("SMTP credentials are not set!")



load_dotenv()  # load .env file

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

creds_json = os.getenv("GOOGLE_CREDS")
if not creds_json:
    raise ValueError("GOOGLE_CREDS environment variable not set!")

creds_dict = json.loads(creds_json)
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

service = build("sheets", "v4", credentials=creds)

SPREADSHEET_ID = "1EiIjWBXG01SHMnz8aXechn95OJisLaNDhm2SN2nYYQ0"
SHEET_NAME = "loginhistroy"


CONTACTUSSPREADSHEET_ID = "17njC7fjtpRrsNiW9th8yD3pFzVWs2-X6UnnEO4S7vv0"
CONTACTUSSHEET_NAME = "contactus"


JOBSPREADSHEET_ID = "1rYIQ-A6V2MMRyLJVr6zgXfzXGeH8OtZr_rOYtniKyr4"
JOBSHEET_NAME = "newrecurits"


REGISTER_SPREADSHEET_ID = "1vtCR6BCljotft5pD1bIDITY0tOLf9DFORxTBCq1mw2U"
REGISTER_SHEET_NAME = "register"

PAYMENT_EXCEL_ID="1PAAj8FyA3nKaSgeb07zDN0TBPPp0vCXTXLoaB1p1gdU"
PAYMENT_EXCEL_NAME="payment"



# ==============================
# FastAPI Setup
# ==============================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # setup_sheet()              # loginhistroy headers
    contactus_setup_sheet()    # contactus headers
    setup_sheet()
    jobs_setup_sheet()
    register_setup_sheet()
    setup_payment_sheet()
    yield

app = FastAPI(title="Zoona Portal API",lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow your HTML file origin if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ==============================
# Google Sheets Helpers
# ==============================

def setup_sheet():
    """Ensure headers exist in Google Sheet"""
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A1:F1"
        ).execute()

        if 'values' not in result or len(result['values']) == 0:
            headers = [["S.No", "Username", "Email", "LoginTime", "LogoutTime", "HoursSpent"]]
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{SHEET_NAME}!A1:F1",
                valueInputOption="RAW",
                body={"values": headers}
            ).execute()
            print("✅ Headers created successfully.")
    except Exception as e:
        print("⚠️ Error setting up headers:", e)



# Setup sheet headers at startup


def contactus_setup_sheet():
    """Ensure headers exist in ContactUs Google Sheet"""
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=CONTACTUSSPREADSHEET_ID,
            range=f"{CONTACTUSSHEET_NAME}!A1:G1"
        ).execute()

        if "values" not in result or len(result["values"]) == 0:
            headers = [["S.No", "Name", "Phone", "Email", "ProjectType", "ProjectDescription", "SubmittedAt"]]
            service.spreadsheets().values().update(
                spreadsheetId=CONTACTUSSPREADSHEET_ID,
                range=f"{CONTACTUSSHEET_NAME}!A1:G1",
                valueInputOption="RAW",
                body={"values": headers}
            ).execute()
            print("✅ ContactUs headers created successfully.")
        else:
            print("ℹ️ ContactUs headers already exist.")
    except Exception as e:
        print("⚠️ Error setting up ContactUs headers:", e)


def jobs_setup_sheet():
    """Ensure headers exist in Job Applications Google Sheet"""
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=JOBSPREADSHEET_ID,
            range=f"{JOBSHEET_NAME}!A1:E1"
        ).execute()

        if "values" not in result or len(result["values"]) == 0:
            headers = [["S.No", "Name", "Email", "KeySkills", "JoinUs", "ResumeLink", "SubmittedAt"]]
            service.spreadsheets().values().update(
                spreadsheetId=JOBSPREADSHEET_ID,
                range=f"{JOBSHEET_NAME}!A1:G1",
                valueInputOption="RAW",
                body={"values": headers}
            ).execute()
            print("✅ Jobs headers created successfully.")
        else:
            print("ℹ️ Jobs headers already exist.")
    except Exception as e:
        print("⚠️ Error setting up Jobs headers:", e)


# ==============================
# Email Helpers
# ==============================
def send_thankyou_email(to_email: str, name: str, project_type: str):
    """Send thank-you email to user"""
    try:
        subject = "Thank You for Registering"
        body = f"""
        <html>
        <body>
            <p>Hi {name},</p>
            <p>Thank you for reaching out to Zoona Technologies. ✨</p>
            <p>We’ve received your project request regarding: <b>{project_type}</b>.</p>
            <p>Our team will review the details and connect with you within 24 hours.</p>
            <br>
            <p>Best regards,<br>Team Zoona Technologies</p>
        </body>
        </html>
        """

        msg = MIMEMultipart()
        msg["From"] = USERNAME
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(USERNAME, PASSWORD)
            server.sendmail(USERNAME, to_email, msg.as_string())

        return True
    except Exception as e:
        print("Email Error (User):", e)
        return False


def send_admin_notification(name: str, phone: str, email: str, project_type: str, project_description: str):
    """Send project details to admin"""
    try:
        subject = "📩 New Contact Request"
        body = f"""
        <html>
        <body>
            <p><b>📩 New Contact Request</b></p>
            <p><b>Name:</b> {name}</p>
            <p><b>Email:</b> {email}</p>
            <p><b>Phone:</b> {phone}</p>
            <p><b>Service:</b> {project_type}</p>
            <p><b>Message:</b> {project_description}</p>
            <br>
            <p>Regards,<br>Zoona Portal</p>
        </body>
        </html>
        """

        msg = MIMEMultipart()
        msg["From"] = USERNAME
        msg["To"] = USERNAME
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(USERNAME, PASSWORD)
            server.sendmail(USERNAME, USERNAME, msg.as_string())

        return True
    except Exception as e:
        print("Email Error (Admin):", e)
        return False


def send_resume_email(name: str, email: str, keyskills: str, join_us: str, resume: UploadFile):
    """Send job application + resume to admin"""
    try:
        subject = "📄 New Job Application"
        body = f"""
        <html>
        <body>
            <p><b>📩 New Job Application Received</b></p>
            <p><b>Name:</b> {name}</p>
            <p><b>Email:</b> {email}</p>
            <p><b>Key Skills:</b> {keyskills}</p>
            <p><b>Join Us?:</b> {join_us}</p>
            <br>
            <p>Resume is attached with this email.</p>
            <br>
            <p>Regards,<br>Zoona Careers Portal</p>
        </body>
        </html>
        """

        msg = MIMEMultipart()
        msg["From"] = USERNAME
        msg["To"] = USERNAME
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        # Attach resume file
        file_content = resume.file.read()
        part = MIMEApplication(file_content, Name=resume.filename)
        part["Content-Disposition"] = f'attachment; filename="{resume.filename}"'
        msg.attach(part)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(USERNAME, PASSWORD)
            server.sendmail(USERNAME, USERNAME, msg.as_string())

        return True
    except Exception as e:
        print("Email Error (Resume):", e)
        return False


def send_thankyou_resume(name: str, email: str):
    """Send thank-you email to applicant"""
    try:
        msg = EmailMessage()
        msg["Subject"] = "Thank You for Applying"
        msg["From"] = USERNAME
        msg["To"] = email

        msg.set_content(f"""
        Dear {name},

        Thank you for applying to our company. 
        Our HR team will review your resume and get back to you if shortlisted.

        Best Regards,
        HR Team
        """)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(USERNAME, PASSWORD)
            server.send_message(msg)

        return True
    except Exception as e:
        print("Error sending thank-you email:", e)
        return False


# ==============================
# API Endpoints
# ==============================




def append_user_details(name: str, phone: str, email: str, project_type: str, project_description: str):
    """Append user details into Google Sheet with auto incremented S.No"""
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=CONTACTUSSPREADSHEET_ID,
            range=f"{CONTACTUSSHEET_NAME}!A:A"
        ).execute()

        num_rows = len(result.get("values", []))
        serial_no = num_rows  # header included

        submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        values = [[serial_no, name, phone, email, project_type, project_description, submitted_at]]
        service.spreadsheets().values().append(
            spreadsheetId=CONTACTUSSPREADSHEET_ID,
            range=f"{CONTACTUSSHEET_NAME}!A:G",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": values}
        ).execute()

        return True
    except Exception as e:
        print("Google Sheets Error:", e)
        return False



@app.post("/contactus")
def submit_user(
    name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    project_type: str = Form(...),
    project_description: str = Form(...)
):

    sheet_status = append_user_details(name, phone, email, project_type, project_description)
    # Send thank you email to user
    email_status_user = send_thankyou_email(email, name, project_type)

    # Send project details to admin
    email_status_admin = send_admin_notification(name, phone, email, project_type, project_description)

    if not (email_status_user and email_status_admin and sheet_status):
        raise HTTPException(status_code=500, detail="Failed to send one or more emails")

    return {"message": "User details received successfully!"}

@app.post("/apply")
async def apply_job(
    name: str = Form(...),
    email: str = Form(...),
    keyskills: str = Form(...),
    join_us: str = Form(...),
    resume: UploadFile = File(...)
):
    if not resume.filename.lower().endswith((".pdf", ".doc", ".docx")):
        raise HTTPException(status_code=400, detail="Only PDF, DOC, DOCX files are allowed")

    # Send emails
    if not send_resume_email(name, email, keyskills, join_us, resume):
        raise HTTPException(status_code=500, detail="Failed to send job application email")

    if not send_thankyou_resume(name, email):
        raise HTTPException(status_code=500, detail="Failed to send thank-you email to applicant")

    # ==============================
    # Save details in Google Sheet
    # ==============================
    try:
        # Get existing rows to calculate S.No
        result = service.spreadsheets().values().get(
            spreadsheetId=JOBSPREADSHEET_ID,
            range=f"{JOBSHEET_NAME}!A:A"
        ).execute()

        rows = result.get("values", [])
        sno = len(rows)  # auto increment based on row count

        submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Create a clickable link formula
        resume_link = f'=HYPERLINK("https://drive.google.com/your_resume_folder/{resume.filename}", "View Resume")'

        new_row = [sno, name, email, keyskills, join_us, resume_link, submitted_at]

        service.spreadsheets().values().append(
            spreadsheetId=JOBSPREADSHEET_ID,
            range=f"{JOBSHEET_NAME}!A:G",
            valueInputOption="USER_ENTERED",
            body={"values": [new_row]}
        ).execute()

        print("✅ Job application stored in Google Sheets.")

    except Exception as e:
        print("⚠️ Error storing job application:", e)

    return {"message": "Job application submitted successfully!", "resume_filename": resume.filename}

sessions = {}

def create_session(username: str, email: str):
    session_id = secrets.token_hex(16)
    sessions[session_id] = {
        "username": username,
        "email": email,
        "login_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return session_id

def get_current_user(request: Request) -> Optional[dict]:
    session_id = request.cookies.get("session_id")
    if session_id and session_id in sessions:
        return sessions[session_id]
    return None


# ------------------ EXISTING LOGIN ------------------
def append_login_history(username: str, email: str, login_time: str):
    """Append a new row with auto-incremented S.No"""
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A:A"
        ).execute()

        num_rows = len(result.get('values', []))
        serial_no = num_rows  # Row count includes header

        # Append row with empty LogoutTime & HoursSpent
        values = [[serial_no, username, email, login_time, "", ""]]

        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A:F",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": values}
        ).execute()

        return True
    except Exception as e:
        print("Google Sheets Error:", e)
        return False


@app.post("/login")
def login_user(email: str = Form(...), password: str = Form(...), response: Response = Response()):
    try:
        # 1. Fetch registered users from register sheet
        result = service.spreadsheets().values().get(
            spreadsheetId=REGISTER_SPREADSHEET_ID,
            range=f"{REGISTER_SHEET_NAME}!A1:F"
        ).execute()

        rows = result.get("values", [])[1:]  # Skip header row

        # 2. Find matching user
        matched_user = None
        for row in rows:
            if len(row) >= 4 and row[2] == email and row[3] == password:
                matched_user = row
                break

        if not matched_user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        username = matched_user[1]

        # 3. Record login history
        login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not append_login_history(username, email, login_time):
            raise HTTPException(status_code=500, detail="Failed to store login history")

        # ✅ 4. Create session and set cookie
        session_id = create_session(username, email)
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            samesite="Lax"
        )

        return {
            "message": "Login successful!",
            "username": username,
            "email": email,
            "login_time": login_time
        }

    except Exception as e:
        print("Error during login:", e)
        raise HTTPException(status_code=500, detail="Login process failed email or password must not be correct")


# ------------------ EXISTING LOGOUT ------------------
def update_logout_history(username: str, email: str, logout_time: str):
    """Update the latest login row of a user with logout time and hours spent"""
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A:F"
        ).execute()

        values = result.get("values", [])
        if not values or len(values) <= 1:
            return False

        # Search from bottom to find last login for email
        for row_idx in range(len(values) - 1, 0, -1):
            row = values[row_idx]
            if len(row) >= 3 and row[2] == email:  # email matches
                if len(row) < 5 or row[4] == "":   # no logout yet
                    login_time_str = row[3]
                    login_dt = datetime.strptime(login_time_str, "%Y-%m-%d %H:%M:%S")
                    logout_dt = datetime.strptime(logout_time, "%Y-%m-%d %H:%M:%S")
                    time_diff = logout_dt - login_dt
                    hours_spent = str(time_diff)   # Store as HH:MM:SS

                    update_range = f"{SHEET_NAME}!E{row_idx+1}:F{row_idx+1}"
                    service.spreadsheets().values().update(
                        spreadsheetId=SPREADSHEET_ID,
                        range=update_range,
                        valueInputOption="RAW",
                        body={"values": [[logout_time, hours_spent]]}
                    ).execute()

                    return True
        return False
    except Exception as e:
        print("Google Sheets Error:", e)
        return False


@app.post("/logout")
def logout_user(request: Request, response: Response):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")

    username = user["username"]
    email = user["email"]
    logout_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not update_logout_history(username, email, logout_time):
        raise HTTPException(status_code=500, detail="Failed to update logout history")

    # ✅ remove session
    session_id = request.cookies.get("session_id")
    if session_id in sessions:
        del sessions[session_id]

    response.delete_cookie("session_id")

    return {"message": "Logout successful!", "username": username, "email": email, "logout_time": logout_time}


# ------------------ NEW API: Who is logged in ------------------
@app.get("/me")
def get_me(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    return user

# def append_login_history(username: str, email: str, login_time: str):
#     """Append a new row with auto-incremented S.No"""
#     try:
#         result = service.spreadsheets().values().get(
#             spreadsheetId=SPREADSHEET_ID,
#             range=f"{SHEET_NAME}!A:A"
#         ).execute()
#
#         num_rows = len(result.get('values', []))
#         serial_no = num_rows  # Row count includes header
#
#         # Append row with empty LogoutTime & HoursSpent
#         values = [[serial_no, username, email, login_time, "", ""]]
#         service.spreadsheets().values().append(
#             spreadsheetId=SPREADSHEET_ID,
#             range=f"{SHEET_NAME}!A:F",
#             valueInputOption="RAW",
#             insertDataOption="INSERT_ROWS",
#             body={"values": values}
#         ).execute()
#
#         return True
#     except Exception as e:
#         print("Google Sheets Error:", e)
#         return False
#
#
#
# @app.post("/login")
# def login_user(email: str = Form(...), password: str = Form(...)):
#     try:
#         # 1. Fetch registered users from the "register" sheet
#         result = service.spreadsheets().values().get(
#             spreadsheetId=REGISTER_SPREADSHEET_ID,
#             range=f"{REGISTER_SHEET_NAME}!A1:F"   # ✅ Correct lowercase tab name
#         ).execute()
#
#         rows = result.get("values", [])[1:]  # Skip header row
#
#         # 2. Find matching user (email & password must match)
#         matched_user = None
#         for row in rows:
#             if len(row) >= 4 and row[2] == email and row[3] == password:
#                 matched_user = row
#                 break
#
#         if not matched_user:
#             raise HTTPException(status_code=401, detail="Invalid email or password")
#
#         # ✅ Username is taken directly from Register sheet (col B)
#         username = matched_user[1]
#
#         # 3. Record login history
#         login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         if not append_login_history(username, email, login_time):
#             raise HTTPException(status_code=500, detail="Failed to store login history")
#
#         # 4. Success response
#         return {
#             "message": "Login successful!",
#             "username": username,
#             "email": email,
#             "login_time": login_time
#         }
#
#     except Exception as e:
#         print("Error during login:", e)
#         raise HTTPException(status_code=500, detail="Login process failed email or password must not be correct")
#
#
#
#
#
#
#
#
#
# from datetime import datetime
#
# def update_logout_history(username: str, email: str, logout_time: str):
#     """Update the latest login row of a user with logout time and hours spent (HH:MM:SS format)"""
#     try:
#         result = service.spreadsheets().values().get(
#             spreadsheetId=SPREADSHEET_ID,
#             range=f"{SHEET_NAME}!A:F"
#         ).execute()
#
#         values = result.get("values", [])
#         if not values or len(values) <= 1:
#             return False
#
#         # Search from bottom to find last login for email
#         for row_idx in range(len(values) - 1, 0, -1):
#             row = values[row_idx]
#             if len(row) >= 3 and row[2] == email:  # email matches
#                 if len(row) < 5 or row[4] == "":   # no logout yet
#                     login_time_str = row[3]
#                     login_dt = datetime.strptime(login_time_str, "%Y-%m-%d %H:%M:%S")
#                     logout_dt = datetime.strptime(logout_time, "%Y-%m-%d %H:%M:%S")
#                     time_diff = logout_dt - login_dt
#                     hours_spent = str(time_diff)   # Store as HH:MM:SS
#
#                     update_range = f"{SHEET_NAME}!E{row_idx+1}:F{row_idx+1}"
#                     service.spreadsheets().values().update(
#                         spreadsheetId=SPREADSHEET_ID,
#                         range=update_range,
#                         valueInputOption="RAW",
#                         body={"values": [[logout_time, hours_spent]]}
#                     ).execute()
#
#                     return True
#         return False
#     except Exception as e:
#         print("Google Sheets Error:", e)
#         return False
#
# @app.post("/logout")
# def logout_user(username: str = Form(...), email: str = Form(...)):
#     logout_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     if not update_logout_history(username, email, logout_time):
#         raise HTTPException(status_code=500, detail="Failed to update logout history")
#     return {"message": "Logout successful!", "username": username, "email": email, "logout_time": logout_time}



def register_setup_sheet():
    """Ensure headers exist in Register Google Sheet"""
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=REGISTER_SPREADSHEET_ID,
            range=f"{REGISTER_SHEET_NAME}!A1:F1"
        ).execute()

        if "values" not in result or len(result["values"]) == 0:
            headers = [["S.No", "Username", "Email", "Password","mobile number", "Registered Time"]]
            service.spreadsheets().values().update(
                spreadsheetId=REGISTER_SPREADSHEET_ID,
                range=f"{REGISTER_SHEET_NAME}!A1:F1",
                valueInputOption="RAW",
                body={"values": headers}
            ).execute()
            print("✅ Register headers created successfully.")
        else:
            print("ℹ️ Register headers already exist.")
    except Exception as e:
        print("⚠️ Error setting up Register headers:", e)


def check_email_exists(email: str) -> bool:
    """Check if email already exists in Register Google Sheet"""
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=REGISTER_SPREADSHEET_ID,
            range=f"{REGISTER_SHEET_NAME}!C2:C"
        ).execute()
        existing_emails = result.get("values", [])
        return any(email.lower() == row[0].lower() for row in existing_emails)
    except Exception as e:
        print("⚠️ Error checking email:", e)
        return False


def get_next_sno() -> int:
    """Get next serial number based on existing rows"""
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=REGISTER_SPREADSHEET_ID,
            range=f"{REGISTER_SHEET_NAME}!A2:A"
        ).execute()
        rows = result.get("values", [])
        return len(rows) + 1
    except Exception as e:
        print("⚠️ Error getting next S.No:", e)
        return 1


def add_register_data(username: str, email: str, password: str,mobile_number: str):
    """Append a new registration record to Google Sheet"""
    sno = get_next_sno()
    registered_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    values = [[sno, username, email, password,mobile_number, registered_time]]

    service.spreadsheets().values().append(
        spreadsheetId=REGISTER_SPREADSHEET_ID,
        range=f"{REGISTER_SHEET_NAME}!A:F",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": values}
    ).execute()
    print(f"✅ Registered {email} added.")


def send_thankyou_mail(email, username):
    try:
        subject = "Registration Successful"
        body = f"""
        Hello {username},

        ✅ Thank you for registering with us!
        We're excited to have you on board.

        Regards,
        Zoona Portal Team
        """

        msg = MIMEMultipart()
        msg["From"] = USERNAME
        msg["To"] = email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(USERNAME, PASSWORD)
        server.send_message(msg)
        server.quit()

        print(f"📧 Thank-you email sent to {email}")
        return True
    except Exception as e:
        print("❌ Error sending email:", e)
        return False


# ==============================
# Register API (Modified)
# ==============================
@app.post("/register")
async def register_user(
    email: str = Form(...),
    moblie_number: str = Form(...),
    password: str = Form(...),
    retype_password: str = Form(...),
    response: Response = None
):
    # Validate passwords
    if password != retype_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    # Extract username from email
    username = email.split("@")[0]

    # Check if email already exists
    if check_email_exists(email):
        raise HTTPException(status_code=400, detail="You are already registered with us, please log in")

    # Add data into Google Sheet (existing code)
    add_register_data(username, email, password, moblie_number)

    # Send thank you email (existing code)
    send_thankyou_mail(email, username)

    # ------------------- NEW ADDITION -------------------
    # Record login history automatically after registration
    login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    append_login_history(username, email, login_time)  # existing function

    # Create session for the new user automatically
    session_id = create_session(username, email)  # existing function

    # ✅ Set cookie so /me can detect user
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="Lax"
    )

    # Return response including session (so frontend can set cookie)
    return {
        "message": "Registration successful & logged in",
        "username": username,
        "email": email,
        "login_time": login_time,
        "session_id": session_id
    }


# # ==============================
# # Register API
# # ==============================
# @app.post("/register")
# async def register_user(
#     email: str = Form(...),
#     moblie_number: str=Form(...),
#     password: str = Form(...),
#     retype_password: str = Form(...)
# ):
#     # Ensure headers exist
#     # register_setup_sheet()
#
#     # Validate passwords
#     if password != retype_password:
#         raise HTTPException(status_code=400, detail="Passwords do not match")
#
#     # Extract username from email
#     username = email.split("@")[0]
#
#     # Check if email already exists
#     if check_email_exists(email):
#         raise HTTPException(status_code=400, detail="You are already registered with us, please log in")
#
#     # Add data into Google Sheet
#     add_register_data(username, email,password,moblie_number)
#
#     # (Optional) Send thank you email
#     send_thankyou_mail(email, username)
#
#     return {"message": "Registration successful", "username": username, "email": email}


def setup_payment_sheet():
    """Ensure headers exist in Payment Google Sheet"""
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=PAYMENT_EXCEL_ID,
            range=f"{PAYMENT_EXCEL_NAME}!A1:E1"
        ).execute()

        if 'values' not in result or len(result['values']) == 0:
            headers = [["S.No", "MailId", "SelectedProject", "Amount", "PaymentTime"]]
            service.spreadsheets().values().update(
                spreadsheetId=PAYMENT_EXCEL_ID,
                range=f"{PAYMENT_EXCEL_NAME}!A1:E1",
                valueInputOption="RAW",
                body={"values": headers}
            ).execute()
            print("✅ Payment sheet headers created successfully.")
        else:
            print("payment headers are already created")
    except Exception as e:
        print("⚠️ Error setting up payment headers:", e)

# ---------- Input Model ----------
class PaymentRequest(BaseModel):
    SelectedProject: str
    Amount: float




# ---------- Helper: Send Email ----------
def send_email(to_email, subject, body):


    msg = MIMEMultipart()
    msg["From"] = f"Zoona Technologies <{USERNAME}>"
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "html"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(USERNAME, PASSWORD)
        server.sendmail(msg["From"], [to_email], msg.as_string())
        server.quit()
        print(f"📧 Mail sent to {to_email}")
    except Exception as e:
        print("⚠️ Mail error:", e)

# ---------- Payment API ----------
@app.post("/pay")
def make_payment(request: Request, data: PaymentRequest):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="User not logged in")

    email = user["email"]
    project = data.SelectedProject
    amount = data.Amount
    payment_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Fetch existing rows to calculate S.No
    sheet_data = service.spreadsheets().values().get(
        spreadsheetId=PAYMENT_EXCEL_ID,
        range=f"{PAYMENT_EXCEL_NAME}!A2:A"
    ).execute()

    sno = len(sheet_data.get("values", [])) + 1

    # Append new payment record
    new_row = [[sno, email, project, amount, payment_time]]
    service.spreadsheets().values().append(
        spreadsheetId=PAYMENT_EXCEL_ID,
        range=PAYMENT_EXCEL_NAME,
        valueInputOption="USER_ENTERED",
        body={"values": new_row}
    ).execute()

    # --------- Admin Mail ---------
    admin_body = f"""
    <html>
    <body>
        <h2>Zoona Technologies - New Payment Received</h2>
        <p><b>Payment Details:</b></p>
        <table border="1" cellspacing="0" cellpadding="5">
            <tr><td><b>Email</b></td><td>{email}</td></tr>
            <tr><td><b>Project</b></td><td>{project}</td></tr>
            <tr><td><b>Amount</b></td><td>{amount}</td></tr>
            <tr><td><b>Payment Time</b></td><td>{payment_time}</td></tr>
        </table>
        <p>--<br/>Zoona Technologies Payment System</p>
    </body>
    </html>
    """
    send_email(USERNAME, "🔔 New Payment Notification - Zoona Technologies", admin_body)

    # --------- Thank-you Mail to User ---------
    user_body = f"""
    <html>
    <body>
        <h2>Thank You for Your Payment!</h2>
        <p>Dear {email},</p>
        <p>We have successfully received your payment for the project <b>{project}</b>.</p>
        <p><b>Amount Paid:</b> {amount}<br/>
        <b>Payment Time:</b> {payment_time}</p>
        <p>We sincerely appreciate your trust in <b>Zoona Technologies</b>.</p>
        <br/>
        <p>Best Regards,<br/>Finance Team<br/>Zoona Technologies</p>
    </body>
    </html>
    """
    send_email(email, "✅ Payment Confirmation - Zoona Technologies", user_body)

    return {"status": "success", "message": "Payment recorded and emails sent."}












otp_store = {}  # {email: {otp, expires, verified}}

# ------------------ STEP 1: REQUEST OTP -------------------
@app.post("/forgot-password")
async def forgot_password(request: Request):
    """Request OTP for password reset"""
    # Get form data safely
    form = await request.form()
    email = form.get("email")
    if not email:
        return {"status": "error", "message": "Email is required"}

    # Check email exists in register sheet
    result = service.spreadsheets().values().get(
        spreadsheetId=REGISTER_SPREADSHEET_ID,
        range=f"{REGISTER_SHEET_NAME}!A2:F"
    ).execute()
    rows = result.get("values", [])

    email_found = any(len(row) > 2 and row[2] == email for row in rows)
    if not email_found:
        return {"status": "error", "message": "Email not registered"}

    # Generate OTP
    otp = str(random.randint(100000, 999999))
    expiry_time = datetime.now() + timedelta(minutes=2)
    otp_store[email] = {"otp": otp, "expires": expiry_time, "verified": False}

    if send_otp_email(email, otp):
        return {"status": "success", "message": f"OTP sent to {email}"}
    else:
        return {"status": "error", "message": "Failed to send OTP"}


# ------------------ STEP 2: VERIFY OTP -------------------
@app.post("/verify-forgot-password")
async def verify_forgot_password(request: Request):
    """Verify OTP before allowing password reset"""
    form = await request.form()
    otp = form.get("otp")
    if not otp:
        return {"status": "error", "message": "OTP is required"}

    # Find which email this OTP belongs to
    email = None
    for e, data in otp_store.items():
        if data["otp"] == otp:
            email = e
            break

    if not email:
        return {"status": "error", "message": "Invalid OTP or no request found"}

    stored_data = otp_store[email]
    if datetime.now() > stored_data["expires"]:
        del otp_store[email]
        return {"status": "error", "message": "OTP expired. Please request again."}

    # Mark email as verified
    otp_store[email]["verified"] = True
    return {"status": "success", "message": f"OTP verified for {email}. You can now reset password.", "email": email}


# ------------------ STEP 3: RESET PASSWORD -------------------
@app.post("/reset-password")
async def reset_password(request: Request):
    """Update password in Google Sheet after OTP verified"""
    form = await request.form()
    new_password = form.get("new_password")
    if not new_password:
        return {"status": "error", "message": "New password is required"}

    # Find verified email
    email = None
    for e, data in otp_store.items():
        if data.get("verified"):
            email = e
            break

    if not email:
        return {"status": "error", "message": "No verified email found. Verify OTP first."}

    try:
        # Get all rows
        result = service.spreadsheets().values().get(
            spreadsheetId=REGISTER_SPREADSHEET_ID,
            range=f"{REGISTER_SHEET_NAME}!A2:F"
        ).execute()
        rows = result.get("values", [])

        row_index = 2
        email_found = False
        for row in rows:
            if len(row) > 2 and row[2] == email:
                email_found = True
                break
            row_index += 1

        if not email_found:
            return {"status": "error", "message": "Email not registered"}

        # Update password (Column D)
        service.spreadsheets().values().update(
            spreadsheetId=REGISTER_SPREADSHEET_ID,
            range=f"{REGISTER_SHEET_NAME}!D{row_index}",
            valueInputOption="RAW",
            body={"values": [[new_password]]}
        ).execute()

        # Clean up OTP store
        del otp_store[email]
        return {"status": "success", "message": "Password reset successful"}

    except Exception as e:
        return {"status": "error", "message": f"Error updating Google Sheet: {e}"}





def send_otp_email(email: str, otp: str):
    try:
        subject = "Your OTP for Password Reset"
        body = f"Hello,\n\nYour OTP is: {otp}\nIt is valid for 2 minutes.\n\nRegards,\nTeam"

        msg = MIMEMultipart()
        msg["From"] = USERNAME
        msg["To"] = email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(USERNAME, PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print("Error sending OTP email:", e)
        return False


















if __name__ == "__main__":
    import uvicorn
    uvicorn.run("mail:app", host="127.0.0.1", port=8000, reload=True)

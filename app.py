from flask import Flask, render_template, request
import pandas as pd
import os
from google.oauth2.credentials import Credentials
import gspread
from google.auth.transport.requests import Request
import googlemaps
from dotenv import load_dotenv
from googleapiclient.discovery import build
import base64
from email.mime.text import MIMEText
import json
from flask import session
from io import StringIO
import re
import requests
from math import radians, sin, cos, sqrt, atan2

# Load environment variables from .env file
load_dotenv()
print("GOOGLE_MAPS_API_KEY:", os.environ.get("GOOGLE_MAPS_API_KEY"))

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY')  # <-- Add this line


SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive',
         'https://www.googleapis.com/auth/gmail.send']
gmaps = googlemaps.Client(key=os.environ.get("GOOGLE_MAPS_API_KEY"))

def authenticate_google():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds
def get_gmail_service():
    creds = authenticate_google()
    return build('gmail', 'v1', credentials=creds)

def create_message(to, subject, body_text):
    message = MIMEText(body_text, 'html')
    message['to'] = to
    message['subject'] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes())
    return {'raw': raw.decode()}

def send_email(service, to, subject, body):
    message = create_message(to, subject, body)
    
    send_args = {
        'userId': 'me',
        'body': message
    }

    sent = service.users().messages().send(**send_args).execute()
    return sent

def send_text(phone_num, message, first_name):
    url = "https://api.openphone.com/v1/messages"
    headers={
        "Authorization": os.environ.get("AUTHORIZATION"),
        "Content-Type":"application/json"
    }
    first_name = first_name.title()
    if first_name =='Charlie':
        payload = {
            "content": message,
            "from": "PNvnUZwoP3",
            "to":[phone_num],
            "userId":"USMZbFI72a"
        }
    elif first_name == 'Mahmoud':
        payload = {
        "content": message,
        "from": "PNaOHVFQas",
        "to":[phone_num],
        "userId":"UStOusLc0x"
    }
    elif first_name == 'Ahmed':
        payload = {
        "content": message,
        "from":  'PNVYQxBEmb',
        "to":[phone_num],
        "userId":'USNNA3aaH3'
    }
    elif first_name == 'Mohamed':
        payload = {
        "content": message,
        "from":  'PNecGwld3E',
        "to":[phone_num],
        "userId":'USkdRcH9dR'
    }
    response = requests.post(url,headers=headers, json = payload)
    return response

def extract_10_digit_number(phone_str):
    # Find all digits
    digits = re.findall(r'\d', phone_str)
    # Join and extract the last 10 digits (in case it includes country code)
    return '+1' + ''.join(digits)[-10:]


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", filters=json.dumps({}), phone_status_html=None, email_status_html=None)




@app.route('/send_messages', methods=['POST'])
def send_messages():
    filters = json.loads(request.form['filters'])

    category = request.form.get('category')
    ll_name = str(request.form['ll_name'])
    ll_email = str(request.form['ll_email'])
    ll_pn = extract_10_digit_number(str(request.form['ll_phone']))
    t_name = str(request.form['t_name'])
    t_pn = extract_10_digit_number(str(request.form['t_phone']))
    address = str(request.form['address'])
    check_out_date = str(request.form['date'])
    relo_company = str(request.form['relo_company'])
    num_days  = int(request.form['num_days'])
    first_name = str(request.form['first_name'])

    ll_ntv_phone_template = (
        f"Hi {ll_name}! I hope you’re doing well. I just emailed you a Notice to Vacate "
        f"for the property at {address} for {t_name}. Please reply to the email to "
        f"confirm receipt. Thank you!"
    )

    t_ntv_phone_template = (
        f"Hi {t_name}! I hope you’re doing well. I just wanted to follow up with you that we are about {num_days} "
        f"days out from your lease termination date and received a notice to vacate from {relo_company}. "
        f"We just want to ensure this is still the case and that you will not need the rental beyond {check_out_date}. Thank you!"
    )
    ll_ntv_email_template = (
        "Dear {ll_name},<br><br>"
        "Please accept this 30-day notice that {t_name} has asked us to "
        "communicate their intent to vacate the premises located at {address} on {check_out_date}. "
        "After the family vacates and a walk-through is completed, please return the security deposit "
        "via Zelle to info@paradisepointhousing.com.<br><br>"
        
        "If there are any deductions from the deposit, please provide an itemized list of all charges, "
        "including damages, along with receipts for any repairs and photos of damages as soon as possible.\n\n"
        
        "We are not requesting exact quotes at this time — only immediate notification of any potential "
        "repair or cleaning expenses within 24 hours of move-out so we may document our file and notify our vendors.<br><br>"
        
        "Please acknowledge receipt and acceptance by responding to this email. "
        
        "Thank you for the opportunity to do business with you!<br><br>"
        
        "Sincerely,<br>"
        "Paradise Point Housing"
    )
    ll_extension_phone_template = (
        f"Hi {ll_name}! I hope you’re doing well. I just emailed you an extension notice for the property at {address} "
        f"for {t_name} until {check_out_date}. Please note this is not a notice to vacate. "
        f"Thank you for understanding and flexibility with our client. Please email us an acknoledgement email, thank you!"
    )
    t_extension_phone_template = (
        f"Hi {t_name}! I hope you’re doing well. I just wanted to follow up with you that we received an extension request "
        f" from {relo_company} for your stay until {check_out_date}. "
    )
    ll_extension_email_template = (
        "Dear {ll_name},<br><br>"
        "Please accept this letter as notification that the {t_name} family has requested an extension of their lease at {address} "
        "to {check_out_date}. Please note this is not a notice to vacate.<br><br>"
        "Thank you for your understanding and flexibility with the {t_name} family. Please email us an acknoledgement email, "
        "thank you!<br><br>"
        
        "Sincerely,<br>"
        "Paradise Point Housing"
    )
    ll_withdrawal_phone_template = (
        f"Hi {ll_name}! I hope you’re doing well. I just emailed you a move out withdrawal notice and extension request "
        f"for the property at {address} for {t_name} until {check_out_date}."
        f" Please email us an acknowledgement email, thank you!"
    )
    t_withdrawal_phone_template = (
        f"Hi {t_name}! I hope you’re doing well. I just wanted to follow up with you that we received a move out withdrawal "
        f" notice and extension request from {relo_company} for your stay until {check_out_date}. "
    )
    ll_withdrawal_email_template = (
        "Dear {ll_name},<br><br>"
        "Please accept this letter as notification that the {t_name} family has requested to withdraw their move out notice "
        "and extend their lease at {address} to {check_out_date}. This comes as a result of more time request by the {t_name} family's "
        "insurance adjuster to complete the necessary repairs to their damaged residence. Please note this is not a notice to vacate.<br><br>"
        "Thank you for your understanding and flexibility with the {t_name} family. Please email us an acknowledgment email!<br><br>"
        "Sincerely,<br>"
        "Paradise Point Housing"
    )
    results = []  # this will feed your table
    submitted_data = {
        "Category": category,
        "Landlord Name": ll_name,
        "Landlord Email": ll_email,
        "Landlord Phone #": ll_pn,
        "Tenant Name": t_name,
        "Tenant Phone #": t_pn,
        "Address": address,
        "Check Out Date": check_out_date,
        "Relocation Company": relo_company,
        "Days from Checkout": num_days,
        "Your First Name": first_name,
    }

    if category == 'NTV':
        # 1) landlord text
        try:
            ntv_ll_text = send_text(ll_pn, ll_ntv_phone_template, first_name)
            results.append({
                "channel": "OpenPhone SMS",
                "recipient": f"{ll_name} ({ll_pn})",
                "status":  ntv_ll_text.text})
        except Exception as e:
            results.append({
                "channel": "OpenPhone SMS",
                "recipient": f"{ll_name} ({ll_pn})",
                "status": "ERROR"})

        # 2) tenant text
        try:
            ntv_t_text = send_text(t_pn, t_ntv_phone_template, first_name)
            results.append({
                "channel": "OpenPhone SMS",
                "recipient": f"{t_name} ({t_pn})",
                "status": ntv_t_text.text
            })
        except Exception as e:
            results.append({
                "channel": "OpenPhone SMS",
                "recipient": f"{t_name} ({t_pn})",
                "status": "ERROR",
            })

        # 3) gmail email
        try:
            gmail_service = get_gmail_service()
            ntv_email = send_email(
                gmail_service,
                to=ll_email,  # <-- FIXED (was "email")
                subject=f'Notice to Vacate: {address}/{t_name} Family',
                body=ll_ntv_email_template.format(
                    ll_name=ll_name,
                    t_name=t_name,
                    address=address,
                    check_out_date=check_out_date
                )
            )
            results.append({
                "channel": "Gmail",
                "recipient": f"{ll_name} ({ll_email})",
                "status": ntv_email['labelIds']
            })
        except Exception as e:
            results.append({
                "channel": "Gmail",
                "recipient": f"{ll_name} ({ll_email})",
                "status": "ERROR"
            })
    if category == 'Extension Request':
        # 1) landlord text
        try:
            ext_ll_text = send_text(ll_pn, ll_extension_phone_template, first_name)
            results.append({
                "channel": "OpenPhone SMS",
                "recipient": f"{ll_name} ({ll_pn})",
                "status":  ext_ll_text.text})
        except Exception as e:
            results.append({
                "channel": "OpenPhone SMS",
                "recipient": f"{ll_name} ({ll_pn})",
                "status": "ERROR"})

        # 2) tenant text
        try:
            ext_t_text = send_text(t_pn, t_extension_phone_template, first_name)
            results.append({
                "channel": "OpenPhone SMS",
                "recipient": f"{t_name} ({t_pn})",
                "status": ext_t_text.text
            })
        except Exception as e:
            results.append({
                "channel": "OpenPhone SMS",
                "recipient": f"{t_name} ({t_pn})",
                "status": "ERROR",
            })

        # 3) gmail email
        try:
            gmail_service = get_gmail_service()
            ext_email = send_email(
                gmail_service,
                to=ll_email,  # <-- FIXED (was "email")
                subject=f'Extension Request: {address}/{t_name} Family',
                body=ll_extension_email_template.format(
                    ll_name=ll_name,
                    t_name=t_name,
                    address=address,
                    check_out_date=check_out_date
                )
            )
            results.append({
                "channel": "Gmail",
                "recipient": f"{ll_name} ({ll_email})",
                "status": ext_email['labelIds']
            })
        except Exception as e:
            results.append({
                "channel": "Gmail",
                "recipient": f"{ll_name} ({ll_email})",
                "status": "ERROR"
            })
    if category == 'Move Out Withdrawal':
        # 1) landlord text
        try:
            wd_ll_text = send_text(ll_pn, ll_withdrawal_phone_template, first_name)
            results.append({
                "channel": "OpenPhone SMS",
                "recipient": f"{ll_name} ({ll_pn})",
                "status":  wd_ll_text.text})
        except Exception as e:
            results.append({
                "channel": "OpenPhone SMS",
                "recipient": f"{ll_name} ({ll_pn})",
                "status": "ERROR"})

        # 2) tenant text
        try:
            wd_t_text = send_text(t_pn, t_withdrawal_phone_template, first_name)
            results.append({
                "channel": "OpenPhone SMS",
                "recipient": f"{t_name} ({t_pn})",
                "status": wd_t_text.text
            })
        except Exception as e:
            results.append({
                "channel": "OpenPhone SMS",
                "recipient": f"{t_name} ({t_pn})",
                "status": "ERROR",
            })

        # 3) gmail email
        try:
            gmail_service = get_gmail_service()
            wd_email = send_email(
                gmail_service,
                to=ll_email,  # <-- FIXED (was "email")
                subject=f'Move-Out Withdrawal Notice: {address}/{t_name} Family',
                body=ll_withdrawal_email_template.format(
                    ll_name=ll_name,
                    t_name=t_name,
                    address=address,
                    check_out_date=check_out_date
                )
            )
            results.append({
                "channel": "Gmail",
                "recipient": f"{ll_name} ({ll_email})",
                "status": wd_email['labelIds']
            })
        except Exception as e:
            results.append({
                "channel": "Gmail",
                "recipient": f"{ll_name} ({ll_email})",
                "status": "ERROR"
            })



    # Convert results to HTML table
    results_df = pd.DataFrame(results)
    results_html = results_df.to_html(classes="table table-bordered table-striped", index=False) if results else None

    return render_template(
        "index.html",
        filters=json.dumps(filters),
        submitted_data=submitted_data,
        results_html=results_html
    )
    

   





if __name__ == '__main__':
    # app.run(debug=True)
    # Use the PORT environment variable or default to 5000 for local testing
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
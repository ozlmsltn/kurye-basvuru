from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import os
import json
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

SPREADSHEET_ID = "1fsnR1I8Axq8VxIkJgoAPAjpoS8fLlOdePIKB9w4fR2A"
DRIVE_FOLDER_ID = "1dSHpJcu9rpMwlUfuDpnm6jNHJrhh9bu7"

def get_credentials():
    service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
    creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    return creds

def get_or_create_drive_folder(drive_service, folder_name):
    results = drive_service.files().list(
        q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)"
    ).execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]
    file_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder"
    }
    folder = drive_service.files().create(body=file_metadata, fields="id").execute()
    return folder["id"]

def upload_to_drive(drive_service, folder_id, file_bytes, filename, mimetype):
    file_metadata = {"name": filename, "parents": [folder_id]}
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mimetype)
    uploaded = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink"
    ).execute()
    drive_service.permissions().create(
        fileId=uploaded["id"],
        body={"type": "anyone", "role": "reader"}
    ).execute()
    return uploaded["webViewLink"]

@app.post("/basvuru")
async def basvuru(
    adsoyad: str = Form(...),
    tcno: str = Form(...),
    plaka: str = Form(...),
    telefon: str = Form(...),
    gorsel1: UploadFile = File(...),
    gorsel2: UploadFile = File(...)
):
    try:
        creds = get_credentials()
        gc = gspread.authorize(creds)
        drive_service = build("drive", "v3", credentials=creds)

        folder_id = DRIVE_FOLDER_ID

        g1_bytes = await gorsel1.read()
        g2_bytes = await gorsel2.read()

        tarih = datetime.now().strftime("%d.%m.%Y %H:%M")
        g1_link = upload_to_drive(drive_service, folder_id, g1_bytes, f"{tcno}_gorsel1_{tarih.replace(' ','_').replace(':','-')}.jpg", gorsel1.content_type)
        g2_link = upload_to_drive(drive_service, folder_id, g2_bytes, f"{tcno}_gorsel2_{tarih.replace(' ','_').replace(':','-')}.jpg", gorsel2.content_type)

        sh = gc.open_by_key(SPREADSHEET_ID)
        ws = sh.sheet1
        ws.append_row([tarih, adsoyad, tcno, plaka, telefon, g1_link, g2_link])

        return JSONResponse({"success": True, "message": "Başvuru alındı!"})

    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)

app.mount("/", StaticFiles(directory="static", html=True), name="static")

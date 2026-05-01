from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import gspread
from google.oauth2.service_account import Credentials
import cloudinary
import cloudinary.uploader
import os
import json
from datetime import datetime

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = "1fsnR1I8Axq8VxIkJgoAPAjpoS8fLlOdePIKB9w4fR2A"

def get_credentials():
    info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
    return Credentials.from_service_account_info(info, scopes=SCOPES)

def setup_cloudinary():
    cloudinary.config(
        cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
        api_key=os.environ["CLOUDINARY_API_KEY"],
        api_secret=os.environ["CLOUDINARY_API_SECRET"],
        secure=True
    )

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
        setup_cloudinary()
        g1 = await gorsel1.read()
        g2 = await gorsel2.read()
        tarih = datetime.now().strftime("%d.%m.%Y %H:%M")
        klasor = "kurye-basvuru/" + tcno
        r1 = cloudinary.uploader.upload(g1, folder=klasor, public_id="gorsel1", resource_type="image")
        r2 = cloudinary.uploader.upload(g2, folder=klasor, public_id="gorsel2", resource_type="image")
        gc = gspread.authorize(get_credentials())
        ws = gc.open_by_key(SPREADSHEET_ID).sheet1
        ws.append_row([tarih, adsoyad, tcno, plaka, telefon, r1["secure_url"], r2["secure_url"]])
        return JSONResponse({"success": True, "message": "Basvuru alindi!"})
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)

app.mount("/", StaticFiles(directory="static", html=True), name="static")

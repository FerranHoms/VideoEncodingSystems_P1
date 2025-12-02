# api/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException
import shutil
import os
import requests
from pydantic import BaseModel
import seminar1_adapted_code

app = FastAPI()

# folder to share files with the ffmpeg container
SHARED_FOLDER = "/shared"

translator = seminar1_adapted_code.ColorTranslator()
jpeg_manager = seminar1_adapted_code.JPEGFileManager()
rle_encoder = seminar1_adapted_code.RunLengthEncoder()

# endpoint for color conversion
class ColorInput(BaseModel):
    r: float
    g: float
    b: float

@app.post("/rgb-to-yuv")
def convert_color(data: ColorInput):

    y, u, v = translator.rgb_to_yuv(data.r, data.g, data.b)
    return {
        "original_rgb": {"r": data.r, "g": data.g, "b": data.b},
        "converted_yuv": {"y": y, "u": u, "v": v}
    }

# endpoint for serpentine + rle
@app.post("/analyze-jpeg-block")
def analyze_block(file: UploadFile = File(...)):

    file_location = f"{SHARED_FOLDER}/{file.filename}"
    
    # save file to shared folder
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # serpentine scan
    scan_result = jpeg_manager.serpentine(file_location)
    
    if not scan_result:
        return {"error": "File too small or not found"}
        
    # apply rle
    rle_result = rle_encoder.encode(scan_result)
    
    return {
        "filename": file.filename,
        "serpentine_scan": scan_result,
        "rle_encoded": rle_result
    }

# endpoint for image resizing via ffmpeg container
@app.post("/resize-image")
def resize_image_remote(file: UploadFile = File(...), width: int = 640, height: int = 480):

    filename = file.filename
    input_path = f"{SHARED_FOLDER}/{filename}"
    output_filename = f"resized_{filename}"
    output_path = f"{SHARED_FOLDER}/{output_filename}"

    # save input file to shared folder
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    ffmpeg_url = "http://ffmpeg_worker:8001/ffmpeg-execute"
    
    payload = {
        "command": "scale",
        "input_file": filename,
        "output_file": output_filename,
        "width": width,
        "height": height
    }

    try:
        response = requests.post(ffmpeg_url, json=payload)
        return {
            "status": "Job sent to FFmpeg container",
            "ffmpeg_response": response.json(),
            "download_link": f"File saved at {output_path} (in container)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
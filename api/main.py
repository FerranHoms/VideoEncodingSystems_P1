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
BBB_FILENAME = "big_buck_bunny.mp4"

# low resolution fragment of Big Buck Bunny for testing
BBB_URL = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"

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


# helper to send jobs to the ffmpeg worker and detect errors
def send_to_worker(payload):
    ffmpeg_url = "http://ffmpeg_worker:8001/ffmpeg-execute"
    try:
        response = requests.post(ffmpeg_url, json=payload)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Worker Error: {str(e)}")

# seminar 2 part 1, download video
@app.post("/download-bbb")
def download_bbb_video():

    file_path = f"{SHARED_FOLDER}/{BBB_FILENAME}"
    
    if os.path.exists(file_path):
        return {"message": "Video already exists!", "path": file_path}
    
    print(f"Downloading BBB from {BBB_URL}...")
    try:
        with requests.get(BBB_URL, stream=True) as r:
            r.raise_for_status()
            with open(file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return {"message": "Download successful", "path": file_path}
    except Exception as e:
        return {"error": str(e)}

# seminar 2 part 1, change resolution
class ResolutionInput(BaseModel):
    width: int
    height: int

@app.post("/s2/change-resolution")
def change_resolution(params: ResolutionInput):

    input_video = BBB_FILENAME
    output_video = f"bbb_{params.width}x{params.height}.mp4"
    
    # check if we have the video
    if not os.path.exists(f"{SHARED_FOLDER}/{input_video}"):
        return {"error": "Please run /download-bbb first!"}

    payload = {
        "command": "change_resolution",
        "input_file": input_video,
        "output_file": output_video,
        "width": params.width,
        "height": params.height
    }
    
    worker_resp = send_to_worker(payload)
    return {
        "status": "Resolution change requested",
        "worker_response": worker_resp,
        "output_file": output_video
    }

# seminar 2 part 1, change chroma subsampling
class ChromaInput(BaseModel):
    chroma_mode: str

@app.post("/s2/change-chroma")
def change_chroma(params: ChromaInput):
    
    input_video = BBB_FILENAME
    output_video = f"bbb_{params.chroma_mode}.mp4"

    if not os.path.exists(f"{SHARED_FOLDER}/{input_video}"):
        return {"error": "Please run /download-bbb first!"}

    payload = {
        "command": "change_chroma",
        "input_file": input_video,
        "output_file": output_video,
        "chroma_subsampling": params.chroma_mode
    }

    worker_resp = send_to_worker(payload)
    return {
        "status": "Chroma change requested",
        "worker_response": worker_resp,
        "output_file": output_video
    }

# seminar 2 part 3, get video info 
@app.post("/s2/video-info")
def get_video_info():

    if not os.path.exists(f"{SHARED_FOLDER}/{BBB_FILENAME}"):
        return {"error": "Please run /download-bbb first!"}

    payload = {
        "command": "get_info",
        "input_file": BBB_FILENAME
    }
    
    worker_resp = send_to_worker(payload)
    
    if not worker_resp.get("success"):
        return {"error": "Failed to retrieve info", "details": worker_resp}

    # extract 5 relevant data points
    data = worker_resp["data"]
    try:
        format_info = data.get("format", {})
        video_stream = next((s for s in data.get("streams", []) if s["codec_type"] == "video"), {})
        
        relevant_data = {
            "1_filename": format_info.get("filename"),
            "2_duration_sec": format_info.get("duration"),
            "3_bitrate": format_info.get("bit_rate"),
            "4_video_codec": video_stream.get("codec_name"),
            "5_resolution": f"{video_stream.get('width')}x{video_stream.get('height')}"
        }
        return {"relevant_info": relevant_data, "full_probe_dump": data}
    except Exception as e:
        return {"error": "Could not parse specific fields", "details": str(e)}

# seminar 2 part 4, create multi-audio container
@app.post("/s2/create-bbb-container")
def create_bbb_container():

    if not os.path.exists(f"{SHARED_FOLDER}/{BBB_FILENAME}"):
        return {"error": "Please run /download-bbb first!"}

    output_filename = "bbb_20s_multiaudio.mp4"

    payload = {
        "command": "process_bbb_container",
        "input_file": BBB_FILENAME,
        "output_file": output_filename
    }

    worker_resp = send_to_worker(payload)
    
    return {
        "status": "Container processing requested",
        "worker_response": worker_resp,
        "output_file": output_filename
    }

# seminar 2 part 5, count tracks in container
@app.post("/s2/count-tracks")
def count_tracks(filename: str = "bbb_20s_multiaudio.mp4"):

    target_file = filename
    if not os.path.exists(f"{SHARED_FOLDER}/{target_file}"):
        target_file = BBB_FILENAME
        if not os.path.exists(f"{SHARED_FOLDER}/{target_file}"):
             return {"error": "File not found. Please run /download-bbb or /create-bbb-container first."}

    # use the get_info command (from exercise 3) to inspect tracks
    payload = {"command": "get_info", "input_file": target_file}
    worker_resp = send_to_worker(payload)

    if not worker_resp.get("success"):
        return {"error": "Failed to inspect file"}

    streams = worker_resp["data"].get("streams", [])
    
    # count tracks by type
    audio_count = sum(1 for s in streams if s["codec_type"] == "audio")
    video_count = sum(1 for s in streams if s["codec_type"] == "video")
    total_count = len(streams)

    return {
        "file_inspected": target_file,
        "total_tracks": total_count,
        "breakdown": {
            "audio_tracks": audio_count,
            "video_tracks": video_count,
            "other_tracks": total_count - (audio_count + video_count)
        }
    }

# seminar 2 part 6, macroblocks and motion vectors
@app.post("/s2/visualize-vectors")
def visualize_vectors():

    input_file = "bbb_20s_multiaudio.mp4"
    
    if not os.path.exists(f"{SHARED_FOLDER}/{input_file}"):
        if os.path.exists(f"{SHARED_FOLDER}/{BBB_FILENAME}"):
             input_file = BBB_FILENAME
        else:
             return {"error": "No video found. Run /download-bbb first."}

    output_file = f"vectors_{input_file}"
    
    payload = {
        "command": "visualize_vectors",
        "input_file": input_file,
        "output_file": output_file
    }
    
    return send_to_worker(payload)

# seminar 2 part 7, YUV histogram
@app.post("/s2/yuv-histogram")
def yuv_histogram():

    input_file = "bbb_20s_multiaudio.mp4"
    
    if not os.path.exists(f"{SHARED_FOLDER}/{input_file}"):
        if os.path.exists(f"{SHARED_FOLDER}/{BBB_FILENAME}"):
             input_file = BBB_FILENAME
        else:
             return {"error": "No video found. Run /download-bbb first."}

    output_file = f"histogram_{input_file}"
    
    payload = {
        "command": "yuv_histogram",
        "input_file": input_file,
        "output_file": output_file
    }
    
    return send_to_worker(payload)

# practice 2 part 1, convert video
class ConvertInput(BaseModel):
    codec: str

@app.post("/p2/convert")
def convert_video(params: ConvertInput):
    input_video = "bbb_20s_multiaudio.mp4"
    
    if not os.path.exists(f"{SHARED_FOLDER}/{input_video}"):
        input_video = BBB_FILENAME
        if not os.path.exists(f"{SHARED_FOLDER}/{input_video}"):
             return {"error": "Video not found. Please run /download-bbb first."}

    # determine extension based on codec
    extension = "mp4"
    if params.codec in ["vp8", "vp9"]:
        extension = "webm"
    elif params.codec == "av1":
        extension = "mkv"
    
    output_video = f"bbb_{params.codec}.{extension}"

    payload = {
        "command": "convert_codec",
        "input_file": input_video,
        "output_file": output_video,
        "codec": params.codec
    }
    
    return send_to_worker(payload)
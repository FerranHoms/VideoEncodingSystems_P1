import subprocess
import os
import json
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

SHARED_FOLDER = "/shared"

class FFmpegJob(BaseModel):
    command: str
    input_file: str
    output_file: str = ""
    width: int = 0
    height: int = 0
    chroma_subsampling: str = ""

@app.post("/ffmpeg-execute")
def run_ffmpeg(job: FFmpegJob):
    
    input_full_path = os.path.join(SHARED_FOLDER, job.input_file)
    output_full_path = os.path.join(SHARED_FOLDER, job.output_file)

    # resize
    if job.command == "scale":
        cmd = [
            "ffmpeg", 
            "-i", input_full_path, 
            "-vf", f"scale={job.width}:{job.height}", 
            "-y", 
            output_full_path
        ]
        return run_subprocess(cmd)

    # video resolution, separate from scale for clarity
    if job.command == "change_resolution":
        print(f"Changing resolution of {job.input_file} to {job.width}x{job.height}")
        cmd = [
            "ffmpeg", 
            "-i", input_full_path, 
            "-vf", f"scale={job.width}:{job.height}",
            "-c:a", "copy", 
            "-y", 
            output_full_path
        ]
        return run_subprocess(cmd)

    # chroma subsampling
    if job.command == "change_chroma":
        print(f"Changing chroma to {job.chroma_subsampling}")
        cmd = [
            "ffmpeg",
            "-i", input_full_path,
            "-vf", f"format={job.chroma_subsampling}",
            "-c:a", "copy",
            "-y",
            output_full_path
        ]
        return run_subprocess(cmd)

    # get video info
    if job.command == "get_info":
        # use ffprobe to return json data
        cmd = [
            "ffprobe", 
            "-v", "quiet", 
            "-print_format", "json", 
            "-show_format", 
            "-show_streams", 
            input_full_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            probe_data = json.loads(result.stdout)
            return {"success": True, "data": probe_data}
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": e.stderr}
        except json.JSONDecodeError:
            return {"success": False, "error": "Could not parse ffprobe output"}

    # cut and package audio
    if job.command == "process_bbb_container":
        
        print(f"Processing multi-audio container for {job.input_file}...")
        cmd = [
            "ffmpeg",
            "-i", input_full_path,
            "-t", "20",                  # cut duration
            "-map", "0:v",               # map video from input 0
            "-map", "0:a",               # map audio from input 0 (for track 1)
            "-map", "0:a",               # map audio from input 0 (for track 2)
            "-map", "0:a",               # map audio from input 0 (for track 3)
            "-c:v", "copy",              # copy video stream (fast)
            "-c:a:0", "aac", "-ac:a:0", "1",
            "-c:a:1", "libmp3lame", "-b:a:1", "128k", "-ac:a:1", "2",
            "-c:a:2", "ac3",
            "-y",
            output_full_path
        ]
        return run_subprocess(cmd)
    
    if job.command == "visualize_vectors":
        print(f"Generating motion vector video for {job.input_file}...")
        cmd = [
            "ffmpeg",
            "-flags2", "+export_mvs",
            "-i", input_full_path,
            "-vf", "codecview=mv=pf+bf+bb",
            "-y",
            output_full_path
        ]
        return run_subprocess(cmd)

    return {"success": False, "error": "Unknown command"}

# helper function to detect errors with the proccess
def run_subprocess(cmd):
    try:
        print("Running command:", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return {"success": True, "message": "Operation successful"}
    except subprocess.CalledProcessError as e:
        print("Error output:", e.stderr)
        return {"success": False, "error": e.stderr}
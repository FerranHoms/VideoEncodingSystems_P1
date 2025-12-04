import subprocess
import os
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

SHARED_FOLDER = "/shared"

class FFmpegJob(BaseModel):
    command: str
    input_file: str
    output_file: str
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
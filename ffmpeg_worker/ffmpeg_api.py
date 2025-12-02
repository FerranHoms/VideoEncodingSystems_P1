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

@app.post("/ffmpeg-execute")
def run_ffmpeg(job: FFmpegJob):
    
    input_full_path = os.path.join(SHARED_FOLDER, job.input_file)
    output_full_path = os.path.join(SHARED_FOLDER, job.output_file)

    if job.command == "scale":
        # exercise 3 logic recreated via api call
        cmd = [
            "ffmpeg", 
            "-i", input_full_path, 
            "-vf", f"scale={job.width}:{job.height}", 
            "-y", 
            output_full_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return {"success": True, "message": "Resizing complete"}
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": e.stderr}
            
    return {"success": False, "error": "Unknown command"}
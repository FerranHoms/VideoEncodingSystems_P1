import subprocess
import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Callable, Any

app = FastAPI()
SHARED_FOLDER = "/shared"

class FFmpegJob(BaseModel):
    command: str
    input_file: str
    output_file: str = ""
    width: int = 0
    height: int = 0
    chroma_subsampling: str = ""
    codec: str = ""

def get_path(filename: str) -> str:
    return os.path.join(SHARED_FOLDER, filename)

def run_cmd(cmd: list) -> dict:
    print(f"Executing: {' '.join(cmd)}")
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return {"success": True, "stdout": res.stdout}
    except subprocess.CalledProcessError as e:
        return {"success": False, "error": e.stderr}

# --- Command Handlers ---

def handle_scale(job: FFmpegJob):
    return run_cmd([
        "ffmpeg", "-i", get_path(job.input_file),
        "-vf", f"scale={job.width}:{job.height}",
        "-y", get_path(job.output_file)
    ])

def handle_resolution(job: FFmpegJob):
    return run_cmd([
        "ffmpeg", "-i", get_path(job.input_file),
        "-vf", f"scale={job.width}:{job.height}", "-c:a", "copy",
        "-y", get_path(job.output_file)
    ])

def handle_chroma(job: FFmpegJob):
    return run_cmd([
        "ffmpeg", "-i", get_path(job.input_file),
        "-vf", f"format={job.chroma_subsampling}", "-c:a", "copy",
        "-y", get_path(job.output_file)
    ])

def handle_info(job: FFmpegJob):
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", get_path(job.input_file)]
    res = run_cmd(cmd)
    return {"success": True, "data": json.loads(res["stdout"])} if res["success"] else res

def handle_process_container(job: FFmpegJob):
    return run_cmd([
        "ffmpeg", "-i", get_path(job.input_file), "-t", "20",
        "-map", "0:v", "-map", "0:a", "-map", "0:a", "-map", "0:a",
        "-c:v", "copy",
        "-c:a:0", "aac", "-ac:a:0", "1",
        "-c:a:1", "libmp3lame", "-b:a:1", "128k", "-ac:a:1", "2",
        "-c:a:2", "ac3",
        "-y", get_path(job.output_file)
    ])

def handle_visualize(job: FFmpegJob):
    return run_cmd([
        "ffmpeg", "-flags2", "+export_mvs", "-i", get_path(job.input_file),
        "-vf", "codecview=mv=pf+bf+bb", "-y", get_path(job.output_file)
    ])

def handle_histogram(job: FFmpegJob):
    return run_cmd([
        "ffmpeg", "-i", get_path(job.input_file),
        "-vf", "split=2[a][b],[b]histogram,format=yuva444p[hh],[a][hh]overlay",
        "-c:a", "copy", "-y", get_path(job.output_file)
    ])

def handle_convert(job: FFmpegJob):
    codecs = {
        "vp8": ("libvpx", "libvorbis"), "vp9": ("libvpx-vp9", "libvorbis"),
        "h265": ("libx265", "aac"), "av1": ("libaom-av1", "aac")
    }
    v_codec, a_codec = codecs.get(job.codec, ("libx264", "aac"))
    cmd = ["ffmpeg", "-i", get_path(job.input_file), "-c:v", v_codec, "-c:a", a_codec, "-cpu-used", "4", "-y", get_path(job.output_file)]
    if job.codec == "av1": cmd.extend(["-crf", "30", "-b:v", "0"])
    return run_cmd(cmd)

def handle_ladder(job: FFmpegJob):
    results = []
    tiers = [(1280, 720, "720p"), (640, 480, "480p")]
    base, ext = os.path.splitext(job.output_file)
    
    for w, h, label in tiers:
        tier_out = f"{base}_{label}{ext or '.mp4'}"
        job.output_file = tier_out
        job.width, job.height = w, h
        if handle_scale(job)["success"]:
            results.append(tier_out)
            
    return {"success": True, "files_created": results} if results else {"success": False, "error": "Ladder failed"}

# Dispatcher Dictionary
HANDLERS: Dict[str, Callable] = {
    "scale": handle_scale,
    "change_resolution": handle_resolution,
    "change_chroma": handle_chroma,
    "get_info": handle_info,
    "process_bbb_container": handle_process_container,
    "visualize_vectors": handle_visualize,
    "yuv_histogram": handle_histogram,
    "convert_codec": handle_convert,
    "encoding_ladder": handle_ladder,
}

@app.post("/ffmpeg-execute")
def run_ffmpeg(job: FFmpegJob):
    handler = HANDLERS.get(job.command)
    if not handler:
        return {"success": False, "error": f"Unknown command: {job.command}"}
    return handler(job)
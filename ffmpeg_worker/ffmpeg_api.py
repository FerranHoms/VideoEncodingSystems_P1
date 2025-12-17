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
    codec: str = "" 

class BaseVideoHandler:
    def build_scale_command(self, input_path, output_path, width, height):
        return [
            "ffmpeg", 
            "-i", input_full_path(input_path), 
            "-vf", f"scale={width}:{height}", 
            "-c:a", "copy",
            "-y", 
            output_full_path(output_path)
        ]

class LadderHandler(BaseVideoHandler):
    def generate_ladder(self, input_file, output_base_name):
        # define our ladder tiers (resolutions)
        tiers = [
            (1280, 720, "720p"),
            (640, 480, "480p")
        ]
        
        results = []
        
        for width, height, label in tiers:

            filename_no_ext = os.path.splitext(output_base_name)[0]
            ext = os.path.splitext(output_base_name)[1]
            if not ext: ext = ".mp4"
            
            tier_output = f"{filename_no_ext}_{label}{ext}"
            
            cmd = self.build_scale_command(input_file, tier_output, width, height)
            
            print(f"Ladder: Generating {label}...")
            try:
                subprocess.run(cmd, capture_output=True, text=True, check=True)
                results.append(tier_output)
            except subprocess.CalledProcessError as e:
                print(f"Error generating {label}: {e.stderr}")
                
        return results

def input_full_path(filename):
    return os.path.join(SHARED_FOLDER, filename)

def output_full_path(filename):
    if not filename: return ""
    return os.path.join(SHARED_FOLDER, filename)

@app.post("/ffmpeg-execute")
def run_ffmpeg(job: FFmpegJob):

    # resize
    if job.command == "scale":
        cmd = [
            "ffmpeg", 
            "-i", input_full_path(job.input_file), 
            "-vf", f"scale={job.width}:{job.height}", 
            "-y", 
            output_full_path(job.output_file)
        ]
        return run_subprocess(cmd)

    # video resolution, separate from scale for clarity
    if job.command == "change_resolution":
        print(f"Changing resolution of {job.input_file} to {job.width}x{job.height}")
        cmd = [
            "ffmpeg", 
            "-i", input_full_path(job.input_file), 
            "-vf", f"scale={job.width}:{job.height}",
            "-c:a", "copy", 
            "-y", 
            output_full_path(job.output_file)
        ]
        return run_subprocess(cmd)

    # chroma subsampling
    if job.command == "change_chroma":
        print(f"Changing chroma to {job.chroma_subsampling}")
        cmd = [
            "ffmpeg",
            "-i", input_full_path(job.input_file),
            "-vf", f"format={job.chroma_subsampling}",
            "-c:a", "copy",
            "-y",
            output_full_path(job.output_file)
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
            input_full_path(job.input_file)
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
            "-i", input_full_path(job.input_file),
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
            "-i", input_full_path(job.input_file),
            "-vf", "codecview=mv=pf+bf+bb",
            "-y",
            output_full_path(job.output_file)
        ]
        return run_subprocess(cmd)

    if job.command == "yuv_histogram":
        print(f"Generating YUV histogram video for {job.input_file}...")

        cmd = [
            "ffmpeg",
            "-i", input_full_path(job.input_file),
            "-vf", "split=2[a][b],[b]histogram,format=yuva444p[hh],[a][hh]overlay",
            "-c:a", "copy",
            "-y",
            output_full_path(job.output_file)
        ]
        return run_subprocess(cmd)
    
    if job.command == "convert_codec":
        print(f"Transcoding {job.input_file} to {job.codec}...")
        
        # default settings
        video_codec_lib = "libx264" # fallback
        audio_codec = "aac"
        
        if job.codec == "vp8":
            video_codec_lib = "libvpx"
            audio_codec = "libvorbis"
        elif job.codec == "vp9":
            video_codec_lib = "libvpx-vp9"
            audio_codec = "libvorbis"
        elif job.codec == "h265":
            video_codec_lib = "libx265"
            audio_codec = "aac"
        elif job.codec == "av1":
            video_codec_lib = "libaom-av1"
            audio_codec = "aac"
        
        cmd = [
            "ffmpeg",
            "-i", input_full_path(job.input_file),
            "-c:v", video_codec_lib,
            "-c:a", audio_codec,
            "-cpu-used", "4", 
            "-y",
            output_full_path(job.output_file)
        ]
        
        # special handling for av1 to not be super slow (crf 30 is lower quality but faster)
        if job.codec == "av1":
            cmd.extend(["-crf", "30", "-b:v", "0"])

        return run_subprocess(cmd)
    
    if job.command == "encoding_ladder":
        print(f"Starting encoding ladder for {job.input_file}")
        
        ladder_runner = LadderHandler()
        
        created_files = ladder_runner.generate_ladder(job.input_file, job.output_file)
        
        if created_files:
            return {
                "success": True, 
                "message": "Ladder creation complete", 
                "files_created": created_files
            }
        else:
            return {"success": False, "error": "Failed to create any ladder versions"}

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
import ffmpeg
import os

def render_video(scene_files: list, output_path: str, session_dir: str):
    try:
        ffmpeg_cmd = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bin', 'ffmpeg-master-latest-win64-gpl', 'bin', 'ffmpeg.exe'))
        ffprobe_cmd = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bin', 'ffmpeg-master-latest-win64-gpl', 'bin', 'ffprobe.exe'))
        if not os.path.exists(ffmpeg_cmd):
            ffmpeg_cmd = 'ffmpeg'
            ffprobe_cmd = 'ffprobe'
            
        clip_paths = []
        
        # Render each scene clip
        for i, scene in enumerate(scene_files):
            clip_path = os.path.join(session_dir, f"clip_{i}.mp4")
            
            # Get precise audio duration to prevent ffmpeg infinite loop hang with zoompan
            try:
                probe = ffmpeg.probe(scene['audio'], cmd=ffprobe_cmd)
                duration = float(probe['format']['duration'])
                # add a tiny buffer (0.1s) to ensure audio is not cut off abruptly
                duration += 0.1
            except Exception:
                duration = 3.0 # Fallback
            
            # Check if image is missing (BLACK)
            if scene['image'] == "BLACK":
                image = ffmpeg.input('color=c=black:s=1280x720:r=1', f='lavfi')
                video_stream = image.filter('format', 'yuv420p').filter('setsar', 1)
            else:
                # Do NOT use stream_loop=-1 with zoompan, it causes ffmpeg to drop to 0.3fps!
                image = ffmpeg.input(scene['image'])
                # zoompan automatically takes 1 frame and generates d frames
                fps = 25
                frames = int(duration * fps) + 25 # add 1s buffer
                video_stream = (
                    image
                    .filter('scale', 1280, 720, force_original_aspect_ratio='decrease')
                    .filter('pad', 1280, 720, '(ow-iw)/2', '(oh-ih)/2')
                    .filter('zoompan', z='min(zoom+0.001,1.15)', d=frames, x='iw/2-(iw/zoom/2)', y='ih/2-(ih/zoom/2)', s='1280x720', fps=fps)
                    .filter('format', 'yuv420p')
                    .filter('setsar', 1)
                )
                
            audio = ffmpeg.input(scene['audio'])
            
            # Pass explicit duration via `t` parameter instead of `shortest=None`
            video = ffmpeg.output(video_stream, audio, clip_path, vcodec='libx264', acodec='aac', t=duration, pix_fmt='yuv420p', video_track_timescale=90000)
            ffmpeg.run(video, overwrite_output=True, cmd=ffmpeg_cmd, capture_stderr=True, capture_stdout=True)
            clip_paths.append(clip_path)
            
        # Concat demuxer
        concat_file_path = os.path.join(session_dir, "concat.txt")
        with open(concat_file_path, "w", encoding="utf-8") as f:
            for clip in clip_paths:
                # ffmpeg concat format requires safe paths or relative paths. We use absolute.
                safe_path = os.path.abspath(clip).replace('\\', '/')
                f.write(f"file '{safe_path}'\n")
                
        # Run ffmpeg concat
        concat_cmd = [
            ffmpeg_cmd, '-y', '-f', 'concat', '-safe', '0', 
            '-i', concat_file_path, '-c', 'copy', output_path
        ]
        
        import subprocess
        result = subprocess.run(concat_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return {"error": f"Lỗi FFmpeg Concat: {result.stderr}"}
            
        return output_path
        
    except ffmpeg.Error as e:
        stderr_out = e.stderr.decode('utf-8', errors='ignore') if e.stderr else str(e)
        return {"error": f"Lỗi FFmpeg: {stderr_out}"}
    except Exception as e:
        return {"error": str(e)}

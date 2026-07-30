import os
import yt_dlp

def get_ffmpeg_dir():
    """Lấy đường dẫn tới thư mục chứa ffmpeg.exe nếu có"""
    custom_ffmpeg_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bin', 'ffmpeg-master-latest-win64-gpl', 'bin'))
    if os.path.exists(os.path.join(custom_ffmpeg_dir, 'ffmpeg.exe')):
        return custom_ffmpeg_dir
    return None

def format_duration(seconds):
    if not seconds:
        return "Không xác định"
    try:
        seconds = int(seconds)
        mins, secs = divmod(seconds, 60)
        hours, mins = divmod(mins, 60)
        if hours > 0:
            return f"{hours:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"
    except Exception:
        return str(seconds)

def get_video_info(url: str):
    """Trích xuất thông tin chi tiết của video từ URL"""
    ffmpeg_dir = get_ffmpeg_dir()
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
    }
    if ffmpeg_dir:
        ydl_opts['ffmpeg_location'] = ffmpeg_dir

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Xử lý trường hợp là Playlist
            if '_type' in info and info['_type'] == 'playlist':
                if 'entries' in info and len(info['entries']) > 0:
                    info = info['entries'][0]

            title = info.get('title', 'Video không có tiêu đề')
            thumbnail = info.get('thumbnail') or (info.get('thumbnails')[-1]['url'] if info.get('thumbnails') else None)
            duration = info.get('duration')
            uploader = info.get('uploader') or info.get('channel') or info.get('uploader_id') or 'N/A'
            extractor = info.get('extractor_key') or info.get('extractor') or 'Web'

            return {
                "status": "success",
                "title": title,
                "thumbnail": thumbnail,
                "duration": duration,
                "duration_formatted": format_duration(duration),
                "uploader": uploader,
                "extractor": extractor,
                "url": url
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Không thể lấy thông tin video: {str(e)}"
        }

def download_video(url: str, format_choice: str = "best"):
    """Tải video hoặc audio từ URL về máy server và trả về file info"""
    downloads_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'downloads'))
    os.makedirs(downloads_dir, exist_ok=True)

    ffmpeg_dir = get_ffmpeg_dir()
    
    outtmpl = os.path.join(downloads_dir, '%(title).80s_%(id)s.%(ext)s')

    ydl_opts = {
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
        'restrictfilenames': False,
    }

    if ffmpeg_dir:
        ydl_opts['ffmpeg_location'] = ffmpeg_dir

    if format_choice == 'mp3':
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    elif format_choice == '1080p':
        ydl_opts['format'] = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best'
        ydl_opts['merge_output_format'] = 'mp4'
    elif format_choice == '720p':
        ydl_opts['format'] = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best'
        ydl_opts['merge_output_format'] = 'mp4'
    elif format_choice == '480p':
        ydl_opts['format'] = 'bestvideo[height<=480]+bestaudio/best[height<=480]/best'
        ydl_opts['merge_output_format'] = 'mp4'
    else: # 'best'
        ydl_opts['format'] = 'bestvideo+bestaudio/best'
        ydl_opts['merge_output_format'] = 'mp4'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            if '_type' in info and info['_type'] == 'playlist':
                if 'entries' in info and len(info['entries']) > 0:
                    info = info['entries'][0]

            filename = ydl.prepare_filename(info)
            
            # Nếu vừa chuyển MP3, định dạng đuôi file thực tế là .mp3
            if format_choice == 'mp3':
                base_name, _ = os.path.splitext(filename)
                filename = base_name + '.mp3'
            elif not os.path.exists(filename):
                # Trường hợp merge_output_format làm đổi thành .mp4
                base_name, _ = os.path.splitext(filename)
                if os.path.exists(base_name + '.mp4'):
                    filename = base_name + '.mp4'

            if not os.path.exists(filename):
                # Fallback tìm file mới nhất trong downloads_dir
                files = [os.path.join(downloads_dir, f) for f in os.listdir(downloads_dir)]
                if files:
                    filename = max(files, key=os.path.getmtime)

            file_size_bytes = os.path.getsize(filename) if os.path.exists(filename) else 0
            if file_size_bytes > 1024 * 1024:
                file_size_str = f"{file_size_bytes / (1024 * 1024):.2f} MB"
            else:
                file_size_str = f"{file_size_bytes / 1024:.1f} KB"

            actual_basename = os.path.basename(filename)
            file_url = f"http://localhost:8000/data/downloads/{actual_basename}"

            return {
                "status": "success",
                "title": info.get('title', actual_basename),
                "file_name": actual_basename,
                "file_path": filename,
                "file_url": file_url,
                "file_size": file_size_str,
                "thumbnail": info.get('thumbnail'),
                "duration_formatted": format_duration(info.get('duration')),
                "format_choice": format_choice
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Lỗi khi tải video: {str(e)}"
        }

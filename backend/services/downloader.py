import os
import re
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

def get_common_ydl_opts():
    """Cấu hình chung chống treo và tối ưu tốc độ cho yt-dlp"""
    ffmpeg_dir = get_ffmpeg_dir()
    opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'no_color': True,
        'noplaylist': True,
        'ignoreerrors': True,
        'socket_timeout': 20,
        'retries': 5,
        'fragment_retries': 5,
        'concurrent_fragment_downloads': 4,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'extractor_args': {
            'youtube': {
                'player_client': ['android']
            }
        }
    }
    if ffmpeg_dir:
        opts['ffmpeg_location'] = ffmpeg_dir

    # Tự động tìm file cookies.txt trong các thư mục dự án
    base_dir = os.path.dirname(__file__)
    possible_cookie_paths = [
        os.path.abspath(os.path.join(base_dir, '..', 'cookies.txt')),
        os.path.abspath(os.path.join(base_dir, '..', '..', 'data', 'cookies.txt')),
        os.path.abspath(os.path.join(base_dir, '..', '..', 'cookies.txt')),
    ]
    for c_path in possible_cookie_paths:
        if os.path.exists(c_path) and os.path.getsize(c_path) > 0:
            opts['cookiefile'] = c_path
            break

    return opts

def format_clean_error(e: Exception) -> str:
    """Xóa mã màu ANSI và định dạng lại thông báo lỗi thân thiện bằng tiếng Việt"""
    msg = str(e)
    msg = re.sub(r'(\x1b)?\[[0-9;]*[a-zA-Z]', '', msg).strip()

    if "Private video" in msg or "Sign in" in msg:
        return (
            "Video này ở chế độ Riêng tư (Private Video) hoặc yêu cầu đăng nhập YouTube.\n\n"
            "💡 Hướng dẫn khắc phục:\n"
            "1. Nếu bạn có quyền xem video này trên trình duyệt (Chrome, Edge, Firefox...), hệ thống sẽ tự động thử dùng cookie từ trình duyệt.\n"
            "2. Hoặc bạn có thể xuất file 'cookies.txt' từ trình duyệt (bằng tiện ích 'Get cookies.txt LOCALLY') "
            "và đặt file này vào thư mục 'backend/cookies.txt' hoặc 'data/cookies.txt'."
        )
    elif "members-only" in msg or "Join this channel" in msg:
        return (
            "Video này chỉ dành cho Hội viên (Members-only).\n"
            "💡 Cần xuất file cookies.txt của tài khoản YouTube đã mua gói hội viên kênh này và chép vào thư mục backend/cookies.txt."
        )
    elif "Video unavailable" in msg:
        return "Video không tồn tại, bị ẩn hoặc đã bị xóa khỏi YouTube."

    return msg

def extract_info_with_cookie_fallback(url: str, download: bool = False, extra_opts: dict = None):
    """Trích xuất thông tin video, tự động chuyển đổi client và thử cookie trình duyệt nếu cần"""
    ydl_opts = get_common_ydl_opts()
    if extra_opts:
        ydl_opts.update(extra_opts)

    # 1. Thử lấy thông tin với cấu hình mặc định (player_client: android)
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=download)
    except Exception as e:
        last_exception = e

    # 2. Thử các player_client thay thế nếu client android gặp sự cố
    fallback_clients = [['android_vr'], ['ios'], ['web_creator'], ['tv_embedded']]
    for client in fallback_clients:
        try:
            client_opts = dict(ydl_opts)
            client_opts['extractor_args'] = {'youtube': {'player_client': client}}
            with yt_dlp.YoutubeDL(client_opts) as ydl:
                return ydl.extract_info(url, download=download)
        except Exception as e:
            last_exception = e

    # 3. Nếu vẫn không được và chưa có cookiefile, thử lấy cookie từ các trình duyệt
    err_str = str(last_exception)
    if 'cookiefile' not in ydl_opts and any(k in err_str for k in ["Private video", "Sign in", "cookies", "members-only"]):
        for browser in ['chrome', 'edge', 'firefox', 'brave', 'opera']:
            try:
                browser_opts = dict(ydl_opts)
                browser_opts['cookiesfrombrowser'] = (browser,)
                with yt_dlp.YoutubeDL(browser_opts) as ydl:
                    return ydl.extract_info(url, download=download)
            except Exception:
                continue

    raise last_exception

def get_video_info(url: str):
    """Trích xuất thông tin chi tiết của video từ URL"""
    extra_opts = {'skip_download': True}

    try:
        info = extract_info_with_cookie_fallback(url, download=False, extra_opts=extra_opts)
        
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
            "message": format_clean_error(e)
        }

def download_video(url: str, format_choice: str = "best"):
    """Tải video hoặc audio từ URL về máy server và trả về file info"""
    downloads_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'downloads'))
    os.makedirs(downloads_dir, exist_ok=True)

    outtmpl = os.path.join(downloads_dir, '%(title).80s_%(id)s.%(ext)s')

    extra_opts = {
        'outtmpl': outtmpl,
        'restrictfilenames': False,
    }

    if format_choice == 'mp3':
        extra_opts['format'] = 'bestaudio/best'
        extra_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    elif format_choice == '1080p':
        extra_opts['format'] = 'bestvideo[height<=?1080]+bestaudio/best[height<=?720]/best'
        extra_opts['merge_output_format'] = 'mp4'
    elif format_choice == '720p':
        extra_opts['format'] = 'bestvideo[height<=?720]+bestaudio/best[height<=?720]/best'
        extra_opts['merge_output_format'] = 'mp4'
    elif format_choice == '480p':
        extra_opts['format'] = 'bestvideo[height<=?480]+bestaudio/best[height<=?480]/best'
        extra_opts['merge_output_format'] = 'mp4'
    else: # 'best'
        extra_opts['format'] = 'bestvideo+bestaudio/best'
        extra_opts['merge_output_format'] = 'mp4'

    try:
        info = extract_info_with_cookie_fallback(url, download=True, extra_opts=extra_opts)
        
        if '_type' in info and info['_type'] == 'playlist':
            if 'entries' in info and len(info['entries']) > 0:
                info = info['entries'][0]

        # Lấy tên file đã tải xuống
        ydl_opts = get_common_ydl_opts()
        ydl_opts.update(extra_opts)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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
            "message": format_clean_error(e)
        }


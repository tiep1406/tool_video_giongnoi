import yt_dlp
import requests
from bs4 import BeautifulSoup

def extract_content(url: str):
    if "youtube.com" in url or "youtu.be" in url:
        return extract_youtube(url)
    else:
        return extract_article(url)

def extract_youtube(url: str):
    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['vi', 'en'],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "type": "youtube",
            "title": info.get('title'),
            "description": info.get('description'),
            "thumbnail": info.get('thumbnail'),
            "transcript": "Transcript extraction logic placeholder"
        }

def extract_article(url: str):
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    title = soup.find('h1')
    title_text = title.text.strip() if title else "Unknown Title"
    
    paragraphs = soup.find_all('p')
    content = "\n".join([p.text.strip() for p in paragraphs if p.text.strip()])
    
    images = [img.get('src') for img in soup.find_all('img') if img.get('src') and str(img.get('src')).startswith('http')]
    
    return {
        "type": "article",
        "title": title_text,
        "content": content[:5000],
        "images": images[:5]
    }

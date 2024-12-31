from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
from yt_dlp import YoutubeDL
import os

app = Flask(__name__)
DOWNLOAD_FOLDER = 'downloads'

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download_video():
    video_url = request.form['url']
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            duration = info.get('duration', 0)
            if duration > 900:
                return "Error: Video is longer than 15 minutes", 400
            
            info = ydl.extract_info(video_url, download=True)
            audio_path = os.path.join(DOWNLOAD_FOLDER, f"{info['title']}.mp3")
            
            try:
                response = send_file(
                    audio_path,
                    as_attachment=True,
                    download_name=f"{info['title']}.mp3"
                )
                
                @response.call_on_close
                def cleanup():
                    if os.path.exists(audio_path):
                        os.remove(audio_path)
                        
                return response
                
            except Exception as e:
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                raise e
                
    except Exception as e:
        return f"Download error: {str(e)}", 400

@app.route('/search', methods=['GET'])
def search_videos():
    query = request.args.get('query', '')
    limit = min(int(request.args.get('limit', 5)), 20)
    
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400
        
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'in_playlist',
        'force_generic_extractor': True
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            search_query = f"ytsearch{limit}:{query}"
            results = ydl.extract_info(search_query, download=False)
            
            videos = []
            for entry in results['entries']:
                if entry:
                    # Получаем среднее качество превью
                    thumbnails = entry.get('thumbnails', [])
                    preview_thumbnail = None
                    if thumbnails:
                        for thumb in thumbnails:
                            if thumb.get('height', 0) <= 180:
                                preview_thumbnail = thumb['url']
                                break
                    
                    # Безопасное получение и форматирование длительности
                    try:
                        duration = int(entry.get('duration', 0))
                        minutes = duration // 60
                        seconds = duration % 60
                        duration_str = f"{minutes}:{seconds:02d}"
                    except (ValueError, TypeError):
                        duration_str = "0:00"
                    
                    videos.append({
                        'title': entry.get('title', ''),
                        'url': f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                        'thumbnail': preview_thumbnail or entry.get('thumbnail', ''),
                        'duration': duration_str,
                        'channel': entry.get('uploader', ''),
                        'channel_url': entry.get('uploader_url', '')
                    })
            
            return jsonify({
                'query': query,
                'results': videos
            })
                
    except Exception as e:
        return jsonify({"error": f"Search error: {str(e)}"}), 400

if __name__ == '__main__':
    app.run(debug=False, port=8888, host='0.0.0.0')
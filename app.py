from flask import Flask, render_template, request, send_file, jsonify
import yt_dlp
import os
import re
from urllib.parse import urlparse, parse_qs
import threading
import time

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create necessary directories
os.makedirs('downloads', exist_ok=True)

def is_valid_youtube_url(url):
    """Validate if the URL is a valid YouTube URL"""
    youtube_regex = re.compile(
        r'(https?://)?(www\.)?'
        r'(youtube\.com|youtu\.be)'
        r'(/watch\?v=|/embed/|/v/|/\?v=)?'
        r'([^&=%\?]{11})'
    )
    
    match = re.match(youtube_regex, url)
    return match is not None

def get_video_id(url):
    """Extract YouTube video ID from URL"""
    parsed_url = urlparse(url)
    
    if parsed_url.hostname in ('youtu.be', 'www.youtu.be'):
        return parsed_url.path[1:]
    
    if parsed_url.hostname in ('youtube.com', 'www.youtube.com'):
        if parsed_url.path == '/watch':
            query_params = parse_qs(parsed_url.query)
            return query_params.get('v', [None])[0]
        elif parsed_url.path.startswith('/embed/'):
            return parsed_url.path.split('/')[2]
        elif parsed_url.path.startswith('/v/'):
            return parsed_url.path.split('/')[2]
    
    return None

def download_video(url, quality='hd', format='mp4'):
    """Download YouTube video using yt-dlp with HD quality priority"""
    video_id = get_video_id(url)
    if not video_id:
        return None, "Invalid YouTube URL"
    
    output_template = f'downloads/%(title)s.%(ext)s'
    
    # Quality format strings for different resolutions
    quality_formats = {
        '4k': 'bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/best[height<=2160][ext=mp4]/best',
        'fhd': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
        'hd': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best',
        'sd': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best',
        'best': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    }
    
    # Default to HD if quality not specified or invalid
    selected_format = quality_formats.get(quality, quality_formats['hd'])
    
    ydl_opts = {
        'format': selected_format,
        'outtmpl': output_template,
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
        'writeinfojson': False,
        'writethumbnail': False,
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        # Ensure we get the best quality audio
        'audioquality': '0',
        'audioformat': 'best',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # Ensure the file has .mp4 extension
            if not filename.endswith('.mp4'):
                new_filename = os.path.splitext(filename)[0] + '.mp4'
                if os.path.exists(filename):
                    os.rename(filename, new_filename)
                    filename = new_filename
            
            return filename, None
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "Video unavailable" in error_msg:
            return None, "This video is not available or has been removed"
        elif "Private video" in error_msg:
            return None, "This video is private and cannot be downloaded"
        elif "age-restricted" in error_msg:
            return None, "This video is age-restricted and cannot be downloaded"
        elif "region" in error_msg.lower():
            return None, "This video is not available in your region"
        else:
            return None, f"Download failed: {error_msg}"
    except yt_dlp.utils.ExtractorError as e:
        return None, f"Failed to extract video information: {str(e)}"
    except FileNotFoundError:
        return None, "FFmpeg is required but not found. Please install FFmpeg to convert videos."
    except PermissionError:
        return None, "Permission denied. Unable to save the file to downloads folder."
    except Exception as e:
        error_msg = str(e)
        if "HTTP Error 403" in error_msg:
            return None, "Access denied. The video may be restricted or unavailable."
        elif "HTTP Error 404" in error_msg:
            return None, "Video not found. Please check the URL and try again."
        elif "network" in error_msg.lower() or "connection" in error_msg.lower():
            return None, "Network error. Please check your internet connection and try again."
        else:
            return None, f"An unexpected error occurred: {error_msg}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video-info', methods=['POST'])
def get_video_info():
    """Get video information without downloading"""
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        if not isinstance(url, str) or len(url.strip()) == 0:
            return jsonify({'error': 'Invalid URL format'}), 400
            
        url = url.strip()
        
        if not is_valid_youtube_url(url):
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Extract relevant information
            video_info = {
                'title': info.get('title', 'Unknown Title'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'uploader': info.get('uploader', 'Unknown'),
                'view_count': info.get('view_count', 0),
                'upload_date': info.get('upload_date', ''),
                'description': info.get('description', '')[:200] + '...' if info.get('description') else '',
            }
            
            # Format duration
            if video_info['duration']:
                minutes = video_info['duration'] // 60
                seconds = video_info['duration'] % 60
                video_info['duration_formatted'] = f"{minutes}:{seconds:02d}"
            else:
                video_info['duration_formatted'] = "Unknown"
            
            # Format view count
            if video_info['view_count']:
                if video_info['view_count'] >= 1000000:
                    video_info['view_count_formatted'] = f"{video_info['view_count'] / 1000000:.1f}M views"
                elif video_info['view_count'] >= 1000:
                    video_info['view_count_formatted'] = f"{video_info['view_count'] / 1000:.1f}K views"
                else:
                    video_info['view_count_formatted'] = f"{video_info['view_count']} views"
            else:
                video_info['view_count_formatted'] = "Unknown views"
            
            return jsonify({
                'success': True,
                'video_info': video_info
            })
            
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "Video unavailable" in error_msg:
            return jsonify({'error': 'This video is not available or has been removed'}), 400
        elif "Private video" in error_msg:
            return jsonify({'error': 'This video is private and cannot be accessed'}), 400
        else:
            return jsonify({'error': f'Failed to get video information: {error_msg}'}), 400
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500
@app.route('/download', methods=['POST'])
def download():
    try:
        data = request.get_json()
        url = data.get('url')
        quality = data.get('quality', 'hd')  # Default to HD quality
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Validate URL format
        if not isinstance(url, str) or len(url.strip()) == 0:
            return jsonify({'error': 'Invalid URL format'}), 400
            
        url = url.strip()
        
        if not is_valid_youtube_url(url):
            return jsonify({'error': 'Invalid YouTube URL. Please provide a valid YouTube video link.'}), 400
        
        # Validate quality parameter
        valid_qualities = ['sd', 'hd', 'fhd', '4k', 'best']
        if quality not in valid_qualities:
            quality = 'hd'  # Default to HD if invalid quality provided
        
        filename, error = download_video(url, quality)
        
        if error:
            return jsonify({'error': error}), 500
        
        # Verify file exists and is not empty
        if not os.path.exists(filename) or os.path.getsize(filename) == 0:
            return jsonify({'error': 'Download completed but file is empty or missing'}), 500
        
        # Get just the filename without path for display
        display_name = os.path.basename(filename)
        
        return jsonify({
            'success': True,
            'filename': display_name,
            'download_path': filename,
            'quality': quality
        })
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/download-file/<path:filename>')
def download_file(filename):
    # Security check to prevent directory traversal
    if '..' in filename or filename.startswith('/'):
        return "Invalid filename", 400
    
    file_path = os.path.join('downloads', filename)
    
    if not os.path.exists(file_path):
        return "File not found", 404
    
    return send_file(file_path, as_attachment=True)

@app.route('/cleanup', methods=['POST'])
def cleanup():
    """Clean up old download files"""
    try:
        for filename in os.listdir('downloads'):
            file_path = os.path.join('downloads', filename)
            # Delete files older than 1 hour
            if os.path.isfile(file_path) and time.time() - os.path.getctime(file_path) > 3600:
                os.remove(file_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Start cleanup thread
    def cleanup_old_files():
        while True:
            time.sleep(3600)  # Run every hour
            with app.app_context():
                cleanup()
    
    cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
    cleanup_thread.start()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
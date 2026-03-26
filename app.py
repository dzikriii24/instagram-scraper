import os
import time
import threading
import shutil
import uuid
import webbrowser
from flask import Flask, render_template, request, jsonify, send_file
from scraper import InstagramScraper

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

# Store progress in memory
scraping_status = {}

def run_scraping_task(session_id, nim_nama, usernames, target_images, target_texts, target_videos, cookies_json):
    """Run the entire scraping task in a thread."""
    scraper = None
    try:
        output_dir = os.path.join(os.getcwd(), 'scraped_data')
        os.makedirs(output_dir, exist_ok=True)
        
        scraping_status[session_id] = {
            'status': 'running',
            'message': '🚀 Mempersiapkan driver... (Initializing driver...)'
        }
        
        scraper = InstagramScraper(nim_nama, output_dir)
        scraper.setup_driver()
        
        scraping_status[session_id]['message'] = '🍪 Mencoba login dengan cookies...'
        
        if not scraper.login_with_cookies(cookies_json):
            raise Exception("Login dengan cookies gagal. Pastikan cookies valid dan tidak kedaluwarsa.")
        
        total_results = {
            'images': 0,
            'texts': 0,
            'videos': 0,
            'accounts': {}
        }
        
        for idx, username in enumerate(usernames):
            username = username.strip()
            if not username:
                continue
                
            scraping_status[session_id] = {
                'status': 'running', 
                'progress': (idx / len(usernames)) * 100,
                'message': f'📱 Scraping {username} ({idx+1}/{len(usernames)})...',
                'current_account': username,
                'account_progress': {
                    'feeds': 0,
                    'reels': 0,
                    'captions': 0,
                    'images': 0,
                    'videos': 0
                }
            }
            
            # Scrape single account
            result = scraper.scrape_account(
                username, target_images, target_texts, target_videos,
                progress_callback=lambda p: update_progress(session_id, p)
            )
            
            total_results['images'] += result['image']
            total_results['texts'] += result['text']
            total_results['videos'] += result['video']
            total_results['accounts'][username] = result
            
            # Create zip for this account
            zip_path = scraper.create_zip(username)
            total_results[f'{username}_zip'] = zip_path
        
        # Create master zip with all accounts
        master_zip = create_master_zip(output_dir, nim_nama, usernames)
        
        # Hapus folder raw data (image, text, audio) otomatis untuk menghemat ruang
        for folder in ['image', 'text', 'audio']:
            folder_path = os.path.join(output_dir, folder)
            if os.path.exists(folder_path):
                try:
                    shutil.rmtree(folder_path)
                except Exception:
                    pass
        
        scraping_status[session_id] = {
            'status': 'completed',
            'result': total_results,
            'master_zip': master_zip,
            'message': f'✅ Scraping selesai! Total: {total_results["images"]} gambar, {total_results["texts"]} caption, {total_results["videos"]} video dari {len(usernames)} akun'
        }
        
    except Exception as e:
        scraping_status[session_id] = {
            'status': 'error',
            'error': str(e),
            'message': f'❌ Error: {str(e)}'
        }
    finally:
        if scraper and scraper.driver:
            try:
                scraper.driver.quit()
            except:
                pass

def update_progress(session_id, progress):
    """Update progress for current account"""
    if session_id in scraping_status:
        status = scraping_status[session_id]
        if 'account_progress' in status:
            status['account_progress'].update(progress)

def create_master_zip(output_dir, nim_nama, usernames):
    """Create master zip containing all scraped data"""
    import zipfile
    
    master_zip_path = os.path.join(output_dir, f'{nim_nama}_all_accounts.zip')
    
    with zipfile.ZipFile(master_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for username in usernames:
            username = username.strip()
            if not username:
                continue
            folder_name = f"{nim_nama}_{username.replace('.', '_')}"
            
            for root, dirs, files in os.walk(os.path.join(output_dir, 'image', folder_name)):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join('image', folder_name, file)
                    zipf.write(file_path, arcname)
                    
            for root, dirs, files in os.walk(os.path.join(output_dir, 'text', folder_name)):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join('text', folder_name, file)
                    zipf.write(file_path, arcname)
                    
            for root, dirs, files in os.walk(os.path.join(output_dir, 'audio', folder_name)):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join('audio', folder_name, file)
                    zipf.write(file_path, arcname)
    
    return master_zip_path

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/preview.gif')
def serve_preview():
    file_path = os.path.join(os.getcwd(), 'preview.gif')
    if os.path.exists(file_path):
        return send_file(file_path, mimetype='image/gif')
    return '', 404

@app.route('/start_scrape', methods=['POST'])
def start_scrape():
    data = request.json
    
    # Get usernames
    if 'usernames' in data:
        usernames = data['usernames']
        if isinstance(usernames, str):
            usernames = [u.strip() for u in usernames.split(',') if u.strip()]
    elif 'username' in data:
        usernames = [data['username']]
    else:
        return jsonify({'error': 'No username provided'}), 400
    
    if not data.get('cookies'):
        return jsonify({'error': 'Cookie session Instagram wajib diisi.'}), 400
        
    session_id = str(uuid.uuid4())
    
    # Start the scraping task in a background thread
    thread = threading.Thread(
        target=run_scraping_task,
        args=(
            session_id,
            data['nim_nama'],
            usernames,
            int(data['target_images']),
            int(data['target_texts']),
            int(data['target_videos']),
            data['cookies']
        )
    )
    thread.daemon = True
    thread.start()
    
    scraping_status[session_id] = {'status': 'starting', 'message': '🚀 Proses scraping dimulai...'}
    
    return jsonify({'session_id': session_id, 'status': 'started'})

@app.route('/status/<session_id>')
def status(session_id):
    if session_id in scraping_status:
        return jsonify(scraping_status[session_id])
    return jsonify({'status': 'not_found'})

@app.route('/download/<session_id>')
def download(session_id):
    if session_id in scraping_status and scraping_status[session_id]['status'] == 'completed':
        master_zip = scraping_status[session_id].get('master_zip')
        if master_zip and os.path.exists(master_zip):
            return send_file(master_zip, as_attachment=True, download_name=f'scraped_data.zip')
    return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    if not os.environ.get('RENDER'):
        webbrowser.open(f'http://localhost:{port}')
    app.run(host='0.0.0.0', port=port, debug=False)
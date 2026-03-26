import os
import time
import requests
import yt_dlp
import hashlib
import re
import zipfile
import json
from selenium import webdriver
from selenium.webdriver.common.by import By

class InstagramScraper:
    def __init__(self, nim_nama, output_dir):
        self.nim_nama = nim_nama
        self.output_dir = output_dir
        self.driver = None
        self.progress_callback = None
        
    def setup_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Jika berjalan di server Render/Cloud, paksa mode Headless agar tidak crash
        if os.environ.get('RENDER'):
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
        
        self.driver = webdriver.Chrome(options=options)
        
        # Tambahkan batas waktu (timeout) yang lebih lama untuk server hosting
        self.driver.set_page_load_timeout(180)
        self.driver.set_script_timeout(180)
        
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
    def login_with_cookies(self, cookies_json_str):
        """Login using session cookies from a JSON string."""
        self.driver.get("https://www.instagram.com/")
        time.sleep(2)
        
        if not cookies_json_str:
            print("  ❌ Cookie string is empty.")
            return False
            
        try:
            cookies = json.loads(cookies_json_str)
            if not isinstance(cookies, list):
                print("  ❌ Cookie JSON is not a list.")
                return False

            for cookie in cookies:
                if 'name' in cookie and 'value' in cookie:
                    # Some cookie extensions export 'expiry' but selenium wants it as int.
                    if 'expiry' in cookie and cookie['expiry'] is not None:
                        cookie['expiry'] = int(cookie['expiry'])
                    # remove unsupported keys by some webdriver versions
                    if 'sameSite' in cookie and cookie['sameSite'] not in ['Strict', 'Lax', 'None']:
                        del cookie['sameSite']
                    self.driver.add_cookie(cookie)
            
            print("  🍪 Cookies loaded. Refreshing page...")
            self.driver.refresh()
            time.sleep(5)
            
            # Verify login by checking for a known element that only appears when logged in
            try:
                self.driver.find_element(By.XPATH, "//*[local-name()='svg' and @aria-label='Home']")
                print("  ✅ Login with cookies successful!")
                return True
            except:
                print("  ❌ Login with cookies failed. The page does not seem to be logged in. Please use fresh cookies.")
                return False
        except Exception as e:
            print(f"  ❌ An unexpected error occurred while loading cookies: {e}")
            return False
        
    def save_cookies(self):
        """Save cookies to file for yt-dlp"""
        cookies = self.driver.get_cookies()
        with open('cookies.txt', 'w') as f:
            f.write("# Netscape HTTP Cookie File\n")
            for cookie in cookies:
                domain = cookie.get('domain', '.instagram.com')
                flag = 'TRUE' if domain.startswith('.') else 'FALSE'
                path = cookie.get('path', '/')
                secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
                expiry = cookie.get('expiry')
                if expiry is None:
                    expiry = int(time.time() + 86400 * 30)
                else:
                    expiry = int(expiry)
                name = cookie.get('name', '')
                value = cookie.get('value', '')
                f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")
    
    def get_feed_links(self, username, limit=90):
        url = f"https://www.instagram.com/{username}/"
        print(f"  🌐 Membuka profile: {url}")
        self.driver.get(url)
        time.sleep(5)
        
        post_links = []
        try:
            last_height = self.driver.execute_script("return document.body.scrollHeight")
        except:
            last_height = 0
        scroll_attempts = 0
        
        while scroll_attempts < 15 and len(post_links) < limit:
            links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")
            for link in links:
                href = link.get_attribute("href")
                if href and "/p/" in href and href not in post_links:
                    post_links.append(href)
            
            try:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            except Exception:
                print("  ⚠️ Timeout saat scroll feed, memproses data yang sudah ada...")
                break
                
            scroll_attempts += 1
            
        return post_links[:limit]
    
    def get_reel_links(self, username, limit=20):
        url = f"https://www.instagram.com/{username}/reels/"
        print(f"  🎬 Membuka tab reels: {url}")
        self.driver.get(url)
        time.sleep(5)
        
        reel_links = []
        try:
            last_height = self.driver.execute_script("return document.body.scrollHeight")
        except:
            last_height = 0
        scroll_attempts = 0
        
        while scroll_attempts < 8 and len(reel_links) < limit:
            links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/reel/')]")
            for link in links:
                href = link.get_attribute("href")
                if href and "/reel/" in href and href not in reel_links:
                    reel_links.append(href)
            
            try:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            except Exception:
                print("  ⚠️ Timeout saat scroll reels, memproses data yang sudah ada...")
                break
                
            scroll_attempts += 1
            
        return reel_links[:limit]
    
    def get_caption(self):
        try:
            time.sleep(2)
            caption = ""
            selectors = [
                "div._a9zr",
                "div._a9zr div._a9zs", 
                "div._a9zr span._ap3a",
                "div.x1lliihq.x1plvlek.xryxfnj.x1n2onr6.x193iq5w.x1swvt13.x1f6kntn",
                "div[role='dialog'] div._a9zr",
            ]
            
            for selector in selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    text = elem.text
                    if text and len(text) > 10:
                        if not text.startswith("like") and not "likes" in text.lower():
                            if not text.startswith("view all"):
                                caption = text
                                break
                if caption:
                    break
            
            if not caption:
                try:
                    meta_desc = self.driver.find_element(By.CSS_SELECTOR, "meta[property='og:description']")
                    caption = meta_desc.get_attribute("content")
                    if caption and "… more" in caption:
                        caption = caption.replace("… more", "")
                except:
                    pass
            
            if not caption:
                caption = "[Caption tidak tersedia]"
            
            if caption:
                lines = caption.split('\n')
                cleaned_lines = []
                for line in lines:
                    if not re.match(r'^[·\d]+[wmdh]\s*$', line.strip()):
                        if not line.strip().startswith('like') and not line.strip().startswith('view'):
                            if not line.strip().startswith('Reply'):
                                cleaned_lines.append(line)
                caption = '\n'.join(cleaned_lines).strip()
                
            return caption
            
        except Exception as e:
            return "[Gagal mengambil caption]"
    
    def capture_post_image(self, save_path, slide_target=None):
        try:
            if slide_target and slide_target > 1:
                for i in range(slide_target - 1):
                    try:
                        next_btn = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Next']")
                        if next_btn.is_enabled():
                            next_btn.click()
                            time.sleep(1.5)
                        else:
                            break
                    except:
                        break
            
            selectors = [
                "div[role='dialog'] article img",
                "div[role='dialog'] div.x5yr21d img",
                "article div._aagv img",
                "div._aagu img",
                "img[style*='object-fit']"
            ]
            
            for selector in selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    src = elem.get_attribute("src")
                    alt = elem.get_attribute("alt") or ""
                    class_name = elem.get_attribute("class") or ""
                    
                    if "profile" in src.lower() or "avatar" in src.lower():
                        continue
                    if "profile" in class_name.lower():
                        continue
                    if "profile" in alt.lower():
                        continue
                    
                    elem.screenshot(save_path)
                    if os.path.getsize(save_path) > 5000:
                        return True
            
            return False
            
        except Exception as e:
            return False
    
    def capture_reel_thumbnail(self, save_path):
        """Screenshot reels thumbnail as fallback"""
        try:
            selectors = [
                "video",
                "canvas",
                "div[role='dialog'] video",
                "div[role='dialog'] canvas",
                "img[src*='cdninstagram']"
            ]
            
            for selector in selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    elem.screenshot(save_path)
                    if os.path.getsize(save_path) > 5000:
                        return True
            
            return False
            
        except Exception as e:
            return False
    
    def download_video_with_ytdlp(self, video_url, save_path):
        """Download video using yt-dlp with cookies"""
        try:
            # Save cookies first
            self.save_cookies()
            
            ydl_opts = {
                'outtmpl': save_path,
                'quiet': False,
                'no_warnings': False,
                'extract_flat': False,
                'format': 'best',
                'cookiefile': 'cookies.txt',
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Sec-Fetch-Mode': 'navigate',
                }
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            if os.path.exists(save_path) and os.path.getsize(save_path) > 10000:
                return True
            return False
            
        except Exception as e:
            print(f"      yt-dlp error: {e}")
            return False
    
    def process_feed(self, post_url, folder_paths, counters, target_texts, target_images):
        self.driver.get(post_url)
        time.sleep(5)
        
        shortcode = post_url.split('/')[-2]
        print(f"    📌 Post: {shortcode}")
        
        # Get caption
        if counters['text'] < target_texts:
            caption = self.get_caption()
            text_path = os.path.join(folder_paths['text'], f"post_{counters['text']+1}.txt")
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(f"URL: {post_url}\n")
                f.write(f"="*50 + "\n")
                f.write(f"CAPTION:\n")
                f.write(f"-"*30 + "\n")
                f.write(caption)
                f.write(f"\n" + "="*50 + "\n")
            counters['text'] += 1
            print(f"      📝 Teks ke-{counters['text']}")
            
            if self.progress_callback:
                self.progress_callback({'captions': counters['text']})
        
        # Get image
        if counters['image'] < target_images:
            url_hash = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
            img_filename = f"image_{counters['image']+1}_{url_hash}.jpg"
            img_path = os.path.join(folder_paths['image'], img_filename)
            
            print(f"      📸 Screenshot gambar...")
            
            if self.capture_post_image(img_path, slide_target=1):
                counters['image'] += 1
                file_size = os.path.getsize(img_path) / 1024
                print(f"      ✅ Gambar ke-{counters['image']} ({file_size:.1f} KB)")
                
                if self.progress_callback:
                    self.progress_callback({'images': counters['image']})
            
            # Carousel navigation
            slide_count = 1
            max_slides = 15
            
            while slide_count < max_slides and counters['image'] < target_images:
                try:
                    next_btn = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Next']")
                    if next_btn.is_enabled():
                        next_btn.click()
                        time.sleep(2)
                        slide_count += 1
                        
                        url_hash = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
                        img_filename = f"image_{counters['image']+1}_{url_hash}.jpg"
                        img_path = os.path.join(folder_paths['image'], img_filename)
                        
                        print(f"      📸 Screenshot carousel slide {slide_count}...")
                        
                        if self.capture_post_image(img_path, slide_target=1):
                            counters['image'] += 1
                            file_size = os.path.getsize(img_path) / 1024
                            print(f"      ✅ Gambar ke-{counters['image']} ({file_size:.1f} KB)")
                            
                            if self.progress_callback:
                                self.progress_callback({'images': counters['image']})
                    else:
                        break
                except:
                    break
    
    def process_reel(self, reel_url, folder_paths, counters, target_videos):
        self.driver.get(reel_url)
        time.sleep(5)
        
        shortcode = reel_url.split('/')[-2]
        print(f"    🎬 Reel: {shortcode}")
        
        # Get caption
        if counters['text'] < target_videos * 2:
            caption = self.get_caption()
            text_path = os.path.join(folder_paths['text'], f"post_{counters['text']+1}.txt")
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(f"URL: {reel_url}\n")
                f.write(f"="*50 + "\n")
                f.write(f"CAPTION (REELS):\n")
                f.write(f"-"*30 + "\n")
                f.write(caption)
                f.write(f"\n" + "="*50 + "\n")
            counters['text'] += 1
            print(f"      📝 Teks ke-{counters['text']}")
            
            if self.progress_callback:
                self.progress_callback({'captions': counters['text']})
        
        # Try to download video
        video_downloaded = False
        if counters['video'] < target_videos:
            video_path = os.path.join(folder_paths['audio'], f"video_{counters['video']+1}.mp4")
            print(f"      🎬 Download video...")
            
            if self.download_video_with_ytdlp(reel_url, video_path):
                counters['video'] += 1
                file_size = os.path.getsize(video_path) / 1024
                print(f"      ✅ Video ke-{counters['video']} ({file_size:.1f} KB)")
                video_downloaded = True
                
                if self.progress_callback:
                    self.progress_callback({'videos': counters['video']})
            else:
                print(f"      ❌ Gagal download video, mencoba screenshot thumbnail...")
        
        # If video download fails, try screenshot thumbnail as fallback
        if not video_downloaded and counters['image'] < target_videos * 2:
            url_hash = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
            img_filename = f"reel_thumbnail_{counters['image']+1}_{url_hash}.jpg"
            img_path = os.path.join(folder_paths['image'], img_filename)
            
            print(f"      📸 Screenshot reel thumbnail...")
            
            if self.capture_reel_thumbnail(img_path):
                counters['image'] += 1
                file_size = os.path.getsize(img_path) / 1024
                print(f"      ✅ Thumbnail ke-{counters['image']} ({file_size:.1f} KB)")
                
                if self.progress_callback:
                    self.progress_callback({'images': counters['image']})
    
    def scrape_account(self, username, target_images, target_texts, target_videos, progress_callback=None):
        self.progress_callback = progress_callback
        
        folder_name = f"{self.nim_nama}_{username.replace('.', '_')}"
        folder_paths = {
            'image': os.path.join(self.output_dir, 'image', folder_name),
            'text': os.path.join(self.output_dir, 'text', folder_name),
            'audio': os.path.join(self.output_dir, 'audio', folder_name)
        }
        
        for path in folder_paths.values():
            os.makedirs(path, exist_ok=True)
        
        counters = {'image': 0, 'text': 0, 'video': 0}
        
        # Get feeds for images and texts
        print(f"\n  📸 Getting feeds from @{username}...")
        feed_links = self.get_feed_links(username, limit=target_images)
        
        for idx, post_url in enumerate(feed_links, 1):
            if counters['image'] >= target_images and counters['text'] >= target_texts:
                break
            print(f"\n    [{idx}/{len(feed_links)}] Processing feed...")
            self.process_feed(post_url, folder_paths, counters, target_texts, target_images)
            time.sleep(1)
        
        # Get reels for videos
        if target_videos > 0:
            print(f"\n  🎬 Getting reels from @{username}...")
            reel_links = self.get_reel_links(username, limit=target_videos + 10)
            
            for idx, reel_url in enumerate(reel_links, 1):
                if counters['video'] >= target_videos:
                    break
                print(f"\n    [{idx}/{len(reel_links)}] Processing reel...")
                self.process_reel(reel_url, folder_paths, counters, target_videos)
                time.sleep(2)
        
        print(f"\n  📊 Hasil {username}: {counters['image']} gambar, {counters['text']} caption, {counters['video']} video")
        return counters
    
    def create_zip(self, username):
        folder_name = f"{self.nim_nama}_{username.replace('.', '_')}"
        zip_path = os.path.join(self.output_dir, f"{folder_name}.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(os.path.join(self.output_dir, 'image', folder_name)):
                for file in files:
                    zipf.write(os.path.join(root, file), os.path.join('image', file))
            for root, dirs, files in os.walk(os.path.join(self.output_dir, 'text', folder_name)):
                for file in files:
                    zipf.write(os.path.join(root, file), os.path.join('text', file))
            for root, dirs, files in os.walk(os.path.join(self.output_dir, 'audio', folder_name)):
                for file in files:
                    zipf.write(os.path.join(root, file), os.path.join('audio', file))
                    
        return zip_path
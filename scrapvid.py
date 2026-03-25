import os
import time
import yt_dlp
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- KONFIGURASI ---
NIM_NAMA = "1237050027_DzikriRabbani"
BASE_DIR = "evaluasi mbg/raw data"

target_akun_video = [
    "sppg.landasan.ulin.utara",
    "sppg.pahandutpanarung",
    "sppg.tangkiling",
    "sppggaruda_jekanraya02",
    "sppghiuputih",
    "sppgmentaos_bjb",
    "sppgpahandutlangkai2",
    "sppgsungaiulin1"
]

TARGET_VIDEO_PER_AKUN = 10  # Ubah jadi 10 video per akun

def create_audio_folder(sppg_name):
    folder_name = f"{NIM_NAMA}_{sppg_name.replace('.', '_')}"
    folder_path = os.path.join(BASE_DIR, "audio", folder_name)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path

def count_existing_videos(sppg_name):
    folder_name = f"{NIM_NAMA}_{sppg_name.replace('.', '_')}"
    folder_path = os.path.join(BASE_DIR, "audio", folder_name)
    if not os.path.exists(folder_path):
        return 0
    return len([f for f in os.listdir(folder_path) if f.endswith('.mp4')])

# --- FUNGSI DOWNLOAD VIDEO DENGAN YT-DLP ---
def download_video_with_ytdlp(video_url, save_path):
    """Download video menggunakan yt-dlp"""
    try:
        ydl_opts = {
            'outtmpl': save_path,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'format': 'best',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        if os.path.exists(save_path) and os.path.getsize(save_path) > 10000:
            return True
        return False
        
    except Exception as e:
        print(f"      ❌ yt-dlp error: {e}")
        return False

# --- FUNGSI AMBIL LINK REELS DARI TAB REELS (LANGSUNG) ---
def get_reel_links_from_tab(driver, username, limit=15):
    """Ambil link reels langsung dari tab REELS"""
    url = f"https://www.instagram.com/{username}/reels/"
    print(f"  🎬 Membuka tab REELS: {url}")
    driver.get(url)
    
    # Tunggu loading
    time.sleep(6)
    
    reel_links = []
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_attempts = 0
    
    while scroll_attempts < 15 and len(reel_links) < limit:
        # Cari semua link yang mengarah ke /reel/
        links = driver.find_elements(By.XPATH, "//a[contains(@href, '/reel/')]")
        for link in links:
            href = link.get_attribute("href")
            if href and '/reel/' in href and href not in reel_links:
                clean_url = href.split('?')[0]
                if clean_url not in reel_links:
                    reel_links.append(clean_url)
        
        # Scroll untuk load lebih banyak reels
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2.5)
        
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        scroll_attempts += 1
        print(f"    📊 Menemukan {len(reel_links)} reels...")
    
    print(f"  📹 Total reels ditemukan: {len(reel_links)}")
    return reel_links[:limit]

# --- FUNGSI PROSES REEL ---
def process_reel(reel_url, audio_path, video_counter, username):
    print(f"    🎬 Downloading: {reel_url.split('/')[-2]}")
    
    filename = f"video_{video_counter + 1}.mp4"
    filepath = os.path.join(audio_path, filename)
    
    if download_video_with_ytdlp(reel_url, filepath):
        size = os.path.getsize(filepath) / 1024
        print(f"      ✅ Video ke-{video_counter + 1} ({size:.1f} KB)")
        return True
    else:
        print(f"      ❌ Gagal download")
        return False

# --- FUNGSI UTAMA SCRAPE VIDEO ---
def scrape_videos_from_account(driver, username, target_count):
    existing = count_existing_videos(username)
    need = target_count - existing
    
    if need <= 0:
        print(f"  ✅ Sudah punya {existing} video dari target {target_count}")
        return 0
    
    print(f"  📊 Video existing: {existing}/{target_count}")
    print(f"  🎯 Perlu {need} video lagi")
    
    # Ambil link reels langsung dari tab REELS
    reel_links = get_reel_links_from_tab(driver, username, limit=need + 10)
    
    if not reel_links:
        print(f"  ⚠️ Tidak ada reels ditemukan di tab REELS")
        return 0
    
    print(f"  📹 Akan memproses {min(len(reel_links), need)} reels...")
    
    audio_path = create_audio_folder(username)
    downloaded = 0
    
    for idx, reel_url in enumerate(reel_links, 1):
        if downloaded >= need:
            break
            
        print(f"\n    [{idx}/{len(reel_links)}] Processing...")
        
        if process_reel(reel_url, audio_path, existing + downloaded, username):
            downloaded += 1
            print(f"      📊 Progress: {existing + downloaded}/{target_count}")
        else:
            print(f"      ⚠️ Skip, lanjut ke reels berikutnya")
        
        # Delay antar download
        time.sleep(3)
    
    print(f"\n  ✅ Selesai: +{downloaded} video baru")
    return downloaded

# --- MAIN ---
def main():
    print("="*70)
    print("🎬 INSTAGRAM REELS DOWNLOADER - LANGSUNG DARI TAB REELS")
    print(f"Target per akun: {TARGET_VIDEO_PER_AKUN} video")
    print("="*70)
    
    # Setup Chrome
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    print("\n🔓 SILAKAN LOGIN MANUAL DI BROWSER YANG TERBUKA")
    print("1. Browser Chrome akan terbuka")
    print("2. Login ke Instagram dengan akun Anda")
    print("3. Setelah login, tekan ENTER di sini untuk melanjutkan...")
    print("="*70)
    
    driver.get("https://www.instagram.com/")
    input("⏎ TEKAN ENTER SETELAH LOGIN MANUAL...")
    
    print("\n✅ Memulai scraping video dari TAB REELS...")
    
    total = 0
    results = {}
    
    for idx, username in enumerate(target_akun_video, 1):
        print(f"\n{'='*60}")
        print(f"🎬 [{idx}/{len(target_akun_video)}] {username}")
        print(f"{'='*60}")
        
        before = count_existing_videos(username)
        downloaded = scrape_videos_from_account(driver, username, TARGET_VIDEO_PER_AKUN)
        after = count_existing_videos(username)
        total += downloaded
        
        results[username] = {'before': before, 'downloaded': downloaded, 'after': after}
        
        print(f"\n  📊 STATUS {username}: {before} → {after} video (+{downloaded})")
        
        # Delay antar akun
        time.sleep(5)
    
    # RINGKASAN
    print("\n" + "="*70)
    print("🎉 RINGKASAN SCRAPING VIDEO")
    print("="*70)
    
    for username, data in results.items():
        status = "✅" if data['after'] >= TARGET_VIDEO_PER_AKUN else "⚠️"
        print(f"{status} {username}: {data['before']} → {data['after']} (+{data['downloaded']})")
    
    print(f"\n📊 TOTAL VIDEO BARU: {total}")
    print(f"🎯 TARGET: {TARGET_VIDEO_PER_AKUN * len(target_akun_video)} video")
    print(f"\n📁 SEMUA VIDEO TERSIMPAN DI:")
    print(f"   {os.path.abspath(BASE_DIR)}/audio/")
    
    # Tampilkan folder per akun
    print("\n📂 FOLDER PER AKUN:")
    for username in target_akun_video:
        folder_name = f"{NIM_NAMA}_{username.replace('.', '_')}"
        folder_path = os.path.join(BASE_DIR, "audio", folder_name)
        count = len([f for f in os.listdir(folder_path) if f.endswith('.mp4')]) if os.path.exists(folder_path) else 0
        bar = "█" * min(count, 10) + "░" * (10 - min(count, 10))
        print(f"   {folder_name}: [{bar}] {count}/10 video")
    
    print("="*70)
    
    driver.quit()

if __name__ == "__main__":
    # Install yt-dlp jika belum
    try:
        import yt_dlp
    except ImportError:
        print("📦 Installing yt-dlp...")
        os.system("pip install yt-dlp")
    main()
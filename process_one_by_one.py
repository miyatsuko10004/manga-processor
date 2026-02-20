import os
import shutil
import subprocess
from pathlib import Path

def load_dotenv(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value.strip('"').strip("'")

# Load environment variables
load_dotenv()

# Configuration
SOURCE_ROOT = os.environ.get("SOURCE_ROOT", "/Users/manyo/Desktop/漫画")
TARGET_ROOT = os.environ.get("TARGET_ROOT", "/Users/manyo/Library/CloudStorage/GoogleDrive-manyo10004@gmail.com/My Drive/manga")
TEMP_ROOT = os.environ.get("TEMP_ROOT", "/Users/manyo/.gemini/tmp/manga_processing")
DONE_DIR = os.environ.get("DONE_DIR", "/Users/manyo/Desktop/漫画/Done")

def log(msg):
    print(msg, flush=True)

def run_unar_extract(archive_path, output_dir):
    cmd = ["unar", "-f", "-q", "-o", output_dir, str(archive_path)]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return result.returncode == 0

def create_zip_from_folder(source_folder, output_path):
    if not os.path.isdir(source_folder):
        return
    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        return
    items = [i for i in Path(source_folder).glob("*") if not i.name.startswith('.')]
    final_source = source_folder
    if len(items) == 1 and items[0].is_dir():
        final_source = items[0]
    base_name = str(output_path).replace('.zip', '')
    try:
        shutil.make_archive(base_name, 'zip', final_source)
    except Exception as e:
        log(f"      Zip error: {e}")

def is_image_folder(path):
    if not path.is_dir():
        return False
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp', '*.gif']:
        if any(path.glob(ext)) or any(path.glob(ext.upper())):
            return True
    return False

def process_extracted_content(extracted_root, target_series_dir):
    nested_archives = []
    for ext in ['*.rar', '*.zip', '*.7z', '*.cbz', '*.cbr']:
        nested_archives.extend(list(extracted_root.rglob(ext)))
    
    if nested_archives:
        for archive in nested_archives:
            if archive.name.startswith('.'): continue
            sub_temp = extracted_root / f"__ext_{archive.stem}"
            if sub_temp.exists(): shutil.rmtree(sub_temp)
            os.makedirs(sub_temp, exist_ok=True)
            try:
                if run_unar_extract(archive, sub_temp):
                    vol_name = archive.stem
                    target_zip = target_series_dir / f"{vol_name}.zip"
                    create_zip_from_folder(sub_temp, target_zip)
                    if os.path.exists(target_zip):
                        log(f"      Done: {target_zip.name}")
            finally:
                if sub_temp.exists(): shutil.rmtree(sub_temp)
        return

    image_dirs = []
    for root, dirs, files in os.walk(extracted_root):
        p = Path(root)
        if p.name.startswith('.') or "__ext_" in p.name: continue
        if is_image_folder(p):
            image_dirs.append(p)
    if image_dirs:
        for img_dir in image_dirs:
            vol_name = img_dir.name
            if img_dir == extracted_root:
                vol_name = extracted_root.name
            target_zip = target_series_dir / f"{vol_name}.zip"
            create_zip_from_folder(img_dir, target_zip)
            if os.path.exists(target_zip):
                log(f"    Done: {target_zip.name}")

def process_single_title(item_path):
    name = item_path.name.strip()
    log(f"\n>>> Starting Title: {name}")
    
    series_name = name
    if item_path.is_file():
        series_name = name.split(' ')[0]
    
    target_series_dir = Path(TARGET_ROOT) / series_name
    os.makedirs(target_series_dir, exist_ok=True)
    
    try:
        if item_path.is_dir():
            for sub in sorted(list(item_path.glob("*"))):
                if sub.name.startswith('.') or sub.suffix in [".py", ".log"]: continue
                if sub.is_file():
                    temp_dir = Path(TEMP_ROOT) / f"temp_{sub.name}"
                    os.makedirs(temp_dir, exist_ok=True)
                    try:
                        if run_unar_extract(sub, temp_dir):
                            process_extracted_content(temp_dir, target_series_dir)
                    finally:
                        if temp_dir.exists(): shutil.rmtree(temp_dir)
                else:
                    process_extracted_content(sub, target_series_dir)
        else:
            temp_dir = Path(TEMP_ROOT) / f"temp_{item_path.name}"
            os.makedirs(temp_dir, exist_ok=True)
            try:
                if run_unar_extract(item_path, temp_dir):
                    process_extracted_content(temp_dir, target_series_dir)
            finally:
                if temp_dir.exists(): shutil.rmtree(temp_dir)
        
        # Success! Move to Done
        os.makedirs(DONE_DIR, exist_ok=True)
        shutil.move(str(item_path), str(Path(DONE_DIR) / item_path.name))
        log(f"<<< Completed and moved to Done: {name}")
        return True
    except Exception as e:
        log(f"!!! Error processing {name}: {e}")
        return False

if __name__ == "__main__":
    if os.path.exists(TEMP_ROOT): shutil.rmtree(TEMP_ROOT)
    os.makedirs(TEMP_ROOT, exist_ok=True)
    
    # Get one title to process
    items = sorted([i for i in Path(SOURCE_ROOT).glob("*") 
                   if not i.name.startswith('.') 
                   and i.name not in ["Done", "process_manga_final.py", "process_manga_v2.py", "process_manga_test.py", "debug_3gatsu.py"]
                   and i.suffix not in [".log", ".txt", ".py"]])
    
    if not items:
        log("No more titles to process.")
    else:
        # Process ONLY the first item
        process_single_title(items[0])

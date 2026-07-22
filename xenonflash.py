#!/usr/bin/env python3
"""
XENON FF PROXY CHECKER - Professional Edition
Version: 2.0.0
Developer: XENON TEAM
"""

import warnings
warnings.filterwarnings('ignore')

import requests
import random
import string
import time
import os
import json
import codecs
import base64
import sys
import hashlib
import secrets
import re
import threading
import tempfile
import shutil
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque, Counter
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =============================================================================
# TELEGRAM CONFIG
# =============================================================================
BOT_TOKEN = "8352741188:AAFHsikjWPVULweV8U0nPBmn_C6b-tnTCK4"
OWNER_ID = "8818676309"
DEV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)) or os.getcwd(), "devices.json")

# =============================================================================
# DEVICE MANAGEMENT
# =============================================================================

def load_devices():
    """Load device data from JSON"""
    if os.path.exists(DEV_FILE):
        try:
            with open(DEV_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_devices(devices):
    """Save device data to JSON"""
    try:
        with open(DEV_FILE, 'w') as f:
            json.dump(devices, f, indent=2)
    except:
        pass

def get_device_password(device_id):
    """Get password for a device, create if not exists"""
    devices = load_devices()
    if device_id in devices:
        return devices[device_id]['password']
    
    # Create new device entry with default password and 7 days expiry
    default_pw = generate_random_password()
    expiry = (datetime.now() + timedelta(days=7)).isoformat()
    devices[device_id] = {
        'password': default_pw,
        'expiry': expiry,
        'created_at': datetime.now().isoformat(),
        'ip': 'N/A'
    }
    save_devices(devices)
    return default_pw

def validate_device(device_id, entered_password):
    """Check if device password is valid and not expired"""
    devices = load_devices()
    if device_id not in devices:
        return False, "Device not registered"
    
    device = devices[device_id]
    
    # Check password
    if device['password'] != entered_password:
        return False, "Invalid password"
    
    # Check expiry
    expiry = datetime.fromisoformat(device['expiry'])
    if datetime.now() > expiry:
        return False, f"Password expired. Please contact 083135353690"
    
    return True, "Valid"

def update_device_ip(device_id, ip):
    """Update device IP"""
    devices = load_devices()
    if device_id in devices:
        devices[device_id]['ip'] = ip
        save_devices(devices)

def generate_random_password():
    """Generate random password for new device"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# =============================================================================
# TELEGRAM NOTIFICATION
# =============================================================================

def send_telegram(message):
    """Send message to owner via Telegram"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": OWNER_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        requests.post(url, data=data, timeout=5)
    except:
        pass

def notify_new_run(device_id, ip):
    """Notify owner when someone runs the script"""
    devices = load_devices()
    device_info = devices.get(device_id, {})
    pw = device_info.get('password', 'N/A')
    expiry = device_info.get('expiry', 'N/A')
    
    msg = f"""<b>🚀 XENON FF RUN DETECTED</b>

<b>Device ID:</b> <code>{device_id}</code>
<b>IP Address:</b> <code>{ip}</code>
<b>Password:</b> <code>{pw}</code>
<b>Expiry:</b> <code>{expiry}</code>
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<b>Commands:</b>
/listdev - List all devices
/changepw DEVICE_ID NEW_PW - Change password
/setexpiry DEVICE_ID DAYS - Set expiry (days)
/delete DEVICE_ID - Delete device
"""
    send_telegram(msg)

# =============================================================================
# TELEGRAM COMMAND HANDLER (Background Thread)
# =============================================================================

def get_updates(offset=None):
    """Get updates from Telegram"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        params = {"timeout": 30, "allowed_updates": ["message"]}
        if offset:
            params["offset"] = offset
        resp = requests.get(url, params=params, timeout=35)
        if resp.status_code == 200:
            return resp.json().get('result', [])
    except:
        pass
    return []

def send_telegram_message(chat_id, text):
    """Send message to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        requests.post(url, data=data, timeout=5)
    except:
        pass

def handle_telegram_commands():
    """Background thread to handle Telegram commands"""
    last_update_id = 0
    
    while True:
        try:
            updates = get_updates(last_update_id + 1 if last_update_id else None)
            for update in updates:
                last_update_id = update.get('update_id', 0)
                message = update.get('message', {})
                chat_id = str(message.get('chat', {}).get('id', ''))
                text = message.get('text', '').strip()
                
                # Only owner can execute commands
                if chat_id != OWNER_ID:
                    send_telegram_message(chat_id, "❌ You are not authorized to use this bot.")
                    continue
                
                if text.startswith('/listdev'):
                    handle_list_devices(chat_id)
                elif text.startswith('/changepw'):
                    handle_change_password(chat_id, text)
                elif text.startswith('/setexpiry'):
                    handle_set_expiry(chat_id, text)
                elif text.startswith('/delete'):
                    handle_delete_device(chat_id, text)
                elif text.startswith('/help'):
                    handle_help(chat_id)
                    
        except:
            pass
        time.sleep(2)

def handle_list_devices(chat_id):
    """Handle /listdev command"""
    devices = load_devices()
    if not devices:
        send_telegram_message(chat_id, "No devices registered.")
        return
    
    msg = "<b>📱 REGISTERED DEVICES</b>\n\n"
    for device_id, info in devices.items():
        pw = info.get('password', 'N/A')
        expiry = info.get('expiry', 'N/A')
        ip = info.get('ip', 'N/A')
        created = info.get('created_at', 'N/A')
        msg += f"<b>Device:</b> <code>{device_id}</code>\n"
        msg += f"<b>Password:</b> <code>{pw}</code>\n"
        msg += f"<b>Expiry:</b> {expiry}\n"
        msg += f"<b>IP:</b> {ip}\n"
        msg += f"<b>Created:</b> {created}\n"
        msg += "─" * 20 + "\n"
    
    send_telegram_message(chat_id, msg)

def handle_change_password(chat_id, text):
    """Handle /changepw command"""
    parts = text.split()
    if len(parts) != 3:
        send_telegram_message(chat_id, "❌ Usage: /changepw DEVICE_ID NEW_PASSWORD")
        return
    
    _, device_id, new_pw = parts
    devices = load_devices()
    
    if device_id not in devices:
        send_telegram_message(chat_id, f"❌ Device {device_id} not found.")
        return
    
    devices[device_id]['password'] = new_pw
    save_devices(devices)
    send_telegram_message(chat_id, f"✅ Password for {device_id} changed to: <code>{new_pw}</code>")

def handle_set_expiry(chat_id, text):
    """Handle /setexpiry command"""
    parts = text.split()
    if len(parts) != 3:
        send_telegram_message(chat_id, "❌ Usage: /setexpiry DEVICE_ID DAYS")
        return
    
    _, device_id, days_str = parts
    try:
        days = int(days_str)
        if days <= 0:
            send_telegram_message(chat_id, "❌ Days must be positive.")
            return
    except:
        send_telegram_message(chat_id, "❌ Invalid days format.")
        return
    
    devices = load_devices()
    if device_id not in devices:
        send_telegram_message(chat_id, f"❌ Device {device_id} not found.")
        return
    
    new_expiry = (datetime.now() + timedelta(days=days)).isoformat()
    devices[device_id]['expiry'] = new_expiry
    save_devices(devices)
    send_telegram_message(chat_id, f"✅ Expiry for {device_id} set to: {new_expiry}")

def handle_delete_device(chat_id, text):
    """Handle /delete command"""
    parts = text.split()
    if len(parts) != 2:
        send_telegram_message(chat_id, "❌ Usage: /delete DEVICE_ID")
        return
    
    _, device_id = parts
    devices = load_devices()
    
    if device_id not in devices:
        send_telegram_message(chat_id, f"❌ Device {device_id} not found.")
        return
    
    del devices[device_id]
    save_devices(devices)
    send_telegram_message(chat_id, f"✅ Device {device_id} deleted.")

def handle_help(chat_id):
    """Handle /help command"""
    msg = """<b>🤖 XENON FF BOT COMMANDS</b>

/listdev - List all devices with passwords
/changepw DEVICE_ID NEW_PW - Change device password
/setexpiry DEVICE_ID DAYS - Set expiry in days
/delete DEVICE_ID - Delete device
/help - Show this help

<b>Example:</b>
/changepw ABC123 NEWPASS123
/setexpiry ABC123 30
"""
    send_telegram_message(chat_id, msg)

# =============================================================================
# CONFIGURATION
# =============================================================================

HARDCODED_KEY = "XENON-FREE-FIRE"

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) or os.getcwd()
CONFIG_DIR = os.path.join(CURRENT_DIR, ".xenon_config")
os.makedirs(CONFIG_DIR, exist_ok=True)

# File paths
USER_KEY_FILE = os.path.join(CONFIG_DIR, ".userkey")
DEVICE_FILE_PATH = os.path.join(CONFIG_DIR, ".device_id")
OUTPUT_MODE_FILE = os.path.join(CONFIG_DIR, ".output_mode")
CUSTOM_NAME_FILE = os.path.join(CONFIG_DIR, ".custom_name")
RARE_ONLY_FILE = os.path.join(CONFIG_DIR, ".rare_only")
CUSTOM_LETTERS_FILE = os.path.join(CONFIG_DIR, ".custom_letters")

# Output directories
OUTPUT_FOLDER = os.path.join(CURRENT_DIR, "XENON_FF")
SPECIAL_FOLDER = os.path.join(OUTPUT_FOLDER, "special")
ALL_FOLDER = os.path.join(OUTPUT_FOLDER, "allaccount")
os.makedirs(SPECIAL_FOLDER, exist_ok=True)
os.makedirs(ALL_FOLDER, exist_ok=True)

# Constants
REGION = "ID"
REGION_NAME = "ID"
REGION_LANG = {"ID": "id"}
WATERMARK = "XENON FF TEAM"
VERSION = "v2.0.0"
DEV_NAME = "XENON FLASH"

# =============================================================================
# COLOR CODES
# =============================================================================

class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    BLINK = '\033[5m'
    
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    BRIGHT_WHITE = '\033[97m'
    
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'
    BG_BRIGHT_RED = '\033[101m'
    BG_BRIGHT_GREEN = '\033[102m'
    BG_BRIGHT_YELLOW = '\033[103m'
    BG_BRIGHT_BLUE = '\033[104m'
    BG_BRIGHT_MAGENTA = '\033[105m'
    BG_BRIGHT_CYAN = '\033[106m'
    BG_BRIGHT_WHITE = '\033[107m'

C = Colors

# =============================================================================
# PROXY MANAGEMENT
# =============================================================================

PROXY_LIST = [None]
proxy_index = 0
PROXY_LOCK = threading.Lock()

def load_proxies_from_file():
    proxy_file = os.path.join(CURRENT_DIR, "proxy.txt")
    proxies = [None]
    
    if os.path.exists(proxy_file):
        try:
            with open(proxy_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if not line.startswith('http'):
                            line = f"http://{line}"
                        proxies.append(line)
            print(f"{C.GREEN}[+] Loaded {len(proxies)-1} proxies from proxy.txt{C.RESET}")
        except Exception as e:
            print(f"{C.YELLOW}[!] Error loading proxy.txt: {e}{C.RESET}")
    else:
        print(f"{C.YELLOW}[!] No proxy.txt found - running direct{C.RESET}")
    
    return proxies

def get_next_proxy():
    global proxy_index
    with PROXY_LOCK:
        if len(PROXY_LIST) <= 1:
            return None
        proxy = PROXY_LIST[proxy_index % len(PROXY_LIST)]
        proxy_index += 1
        return proxy

# =============================================================================
# REGION ROTATION
# =============================================================================

REGION_POOL = ["TH", "ME", "BR", "VN", "PH", "SG", "MY", "MX"]
region_index = 0
REGION_LOCK = threading.Lock()

def get_next_region():
    global region_index
    with REGION_LOCK:
        region_index = (region_index + 1) % len(REGION_POOL)
        return REGION_POOL[region_index]

# =============================================================================
# CHARACTER SETS
# =============================================================================

VIETNAMESE_LETTERS = [
    'a','à','á','ả','ã','ạ','ă','ằ','ắ','ẳ','ẵ','ặ','â','ầ','ấ','ẩ','ẫ','ậ',
    'b','c','d','đ','e','è','é','ẻ','ẽ','ẹ','ê','ề','ế','ể','ễ','ệ',
    'g','h','i','ì','í','ỉ','ĩ','ị','k','l','m','n',
    'o','ò','ó','ỏ','õ','ọ','ô','ồ','ố','ổ','ỗ','ộ','ơ','ờ','ớ','ở','ỡ','ợ',
    'p','q','r','s','t','u','ù','ú','ủ','ũ','ụ','ư','ừ','ứ','ử','ữ','ự',
    'v','x','y','ỳ','ý','ỷ','ỹ','ỵ'
]

KHMER_LETTERS = [
    'ក','ខ','គ','ឃ','ង','ច','ឆ','ជ','ឈ','ញ','ដ','ឋ','ឌ','ឍ','ណ','ត',
    'ថ','ទ','ធ','ន','ប','ផ','ព','ភ','ម','យ','រ','ល','វ','ឝ','ឞ','ស',
    'ហ','ឡ','អ','ឣ','ឤ','ឥ','ឦ','ឧ','ឨ','ឩ','ឪ','ឫ','ឬ','ឭ','ឮ','ឯ',
    'ឰ','ឱ','ឲ','ឳ','កា','ខា','គា','ឃា','ងា','ចា','ឆា','ជា','ឈា','ញា'
]

THAI_LETTERS = [
    'ก','ข','ฃ','ค','ฅ','ฆ','ง','จ','ฉ','ช','ซ','ฌ','ญ','ฎ','ฏ','ฐ','ฑ','ฒ',
    'ณ','ด','ต','ถ','ท','ธ','น','บ','ป','ผ','ฝ','พ','ฟ','ภ','ม','ย','ร','ฤ',
    'ล','ว','ศ','ษ','ส','ห','ฬ','อ','ฮ','ะ','ั','า','ำ','ิ','ี','ึ','ื','ุ','ู'
]

JAPANESE_LETTERS = [
    'あ','い','う','え','お','か','き','く','け','こ','さ','し','す','せ','そ',
    'た','ち','つ','て','と','な','に','ぬ','ね','の','は','ひ','ふ','へ','ほ',
    'ま','み','む','め','も','や','ゆ','よ','ら','り','る','れ','ろ','わ','を','ん'
]

MANDARIN_LETTERS = [
    '的','一','是','了','我','不','人','在','他','有','这','个','上','们','来',
    '到','时','大','地','为','子','中','你','说','生','国','年','着','就','那',
    '和','要','她','出','也','得','里','后','自','以','会','家','可','下','而'
]

CHARS = VIETNAMESE_LETTERS + KHMER_LETTERS + THAI_LETTERS + JAPANESE_LETTERS + MANDARIN_LETTERS

# =============================================================================
# DEVICE POOL
# =============================================================================

DEVICE_POOL = []
all_models = []
brands = ["samsung","xiaomi","oppo","vivo","realme","oneplus","motorola","asus","google","sony","nokia","lg","honor","poco","iqoo","nubia"]
android_versions = ["9","10","11","12","13","14","15","16"]

for brand in brands:
    for _ in range(1000):
        model = f"{brand.capitalize()} {random.randint(1000, 9999)}"
        all_models.append(model)

for _ in range(30000):
    DEVICE_POOL.append({
        "model": random.choice(all_models) if all_models else "Generic",
        "brand": random.choice(brands),
        "android": random.choice(android_versions)
    })

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_public_ip():
    """Get public IP address"""
    try:
        resp = requests.get('https://api.ipify.org', timeout=5)
        if resp.status_code == 200:
            return resp.text.strip()
    except:
        pass
    return "Unknown"

def get_random_ip():
    return f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}"

def get_headers():
    device = random.choice(DEVICE_POOL)
    return {
        "User-Agent": f"GarenaMSDK/4.0.39({device['model']};Android {device['android']};en;ID;)",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "Connection": "Keep-Alive",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": f"v1 {random.randint(100000, 999999)}",
        "X-Forwarded-For": get_random_ip(),
        "X-Real-IP": get_random_ip(),
    }

def get_headers_form():
    h = get_headers()
    h["Content-Type"] = "application/x-www-form-urlencoded"
    return h

def encode_varint(n):
    if n < 0:
        return b''
    result = []
    while True:
        byte = n & 0x7F
        n >>= 7
        if n:
            byte |= 0x80
        result.append(byte)
        if not n:
            break
    return bytes(result)

def create_proto_field(field_num, value):
    if isinstance(value, dict):
        nested = b''
        for k, v in value.items():
            nested += create_proto_field(k, v)
        header = (field_num << 3) | 2
        return encode_varint(header) + encode_varint(len(nested)) + nested
    elif isinstance(value, int):
        header = (field_num << 3) | 0
        return encode_varint(header) + encode_varint(value)
    elif isinstance(value, (str, bytes)):
        encoded_val = value.encode() if isinstance(value, str) else value
        header = (field_num << 3) | 2
        return encode_varint(header) + encode_varint(len(encoded_val)) + encoded_val
    return b''

def build_proto(fields):
    return b''.join(create_proto_field(k, v) for k, v in fields.items())

def aes_encrypt(hex_data):
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
    data = bytes.fromhex(hex_data)
    aes_key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
    iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
    cipher = AES.new(aes_key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(data, AES.block_size))

def encrypt_api(plain_hex):
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
    plain = bytes.fromhex(plain_hex)
    aes_key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
    iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
    cipher = AES.new(aes_key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(plain, AES.block_size)).hex()

HEX_KEY = bytes.fromhex("32656534343831396539623435393838343531343130363762323831363231383734643064356437616639643866376530306331653534373135623764316533")

# =============================================================================
# FILE OPERATIONS
# =============================================================================

file_lock = threading.RLock()

def read_file_safe(filepath):
    with file_lock:
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read()
        except:
            pass
    return ""

def write_file_atomic(filepath, content):
    with file_lock:
        try:
            temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(filepath) or '.', text=True)
            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                shutil.move(temp_path, filepath)
            except:
                try:
                    os.unlink(temp_path)
                except:
                    pass
                raise
        except:
            pass

def append_file_atomic(filepath, content):
    with file_lock:
        try:
            existing = read_file_safe(filepath)
            write_file_atomic(filepath, existing + content)
        except:
            pass

# =============================================================================
# KEY MANAGEMENT - HARDCODE + DEVICE PASSWORD
# =============================================================================

def get_license_key():
    """Get license key - hardcoded"""
    print(f"{C.GREEN}[+] Using hardcoded license key: {HARDCODED_KEY}{C.RESET}")
    return HARDCODED_KEY

def get_device_fingerprint():
    """Get or create device fingerprint"""
    with file_lock:
        try:
            content = read_file_safe(DEVICE_FILE_PATH).strip()
            if content:
                return content
            raw = secrets.token_hex(16)
            device_id = hashlib.sha256(raw.encode()).hexdigest()[:32]
            write_file_atomic(DEVICE_FILE_PATH, device_id)
            return device_id
        except:
            return hashlib.sha256(secrets.token_hex(16).encode()).hexdigest()[:32]

def activation_flow():
    """Main activation flow with device password check"""
    clear_screen()
    
    print(f"{C.BG_BRIGHT_BLUE}{C.BRIGHT_WHITE}{C.BOLD}")
    print("  XENON FF PROXY CHECKER  ")
    print(f"  {VERSION}  ")
    print(C.RESET)
    print()
    print(f"{C.CYAN}========================================{C.RESET}")
    print(f"{C.CYAN}  DEVICE AUTHENTICATION{C.RESET}")
    print(f"{C.CYAN}========================================{C.RESET}")
    print()
    
    device_id = get_device_fingerprint()
    public_ip = get_public_ip()
    
    print(f"{C.CYAN}[*] Device ID: {device_id}{C.RESET}")
    print(f"{C.CYAN}[*] IP Address: {public_ip}{C.RESET}")
    print()
    
    # Get device password
    device_pw = get_device_password(device_id)
    update_device_ip(device_id, public_ip)
    
    # Notify owner via Telegram
    notify_new_run(device_id, public_ip)
    
    print(f"{C.YELLOW}[!] Enter your device password{C.RESET}")
    print(f"{C.DIM}Contact owner if you don't have one{C.RESET}")
    print()
    
    entered_pw = input(f"{C.CYAN}Password: {C.RESET}").strip()
    
    valid, msg = validate_device(device_id, entered_pw)
    
    if valid:
        print(f"{C.GREEN}[+] Password accepted!{C.RESET}")
        time.sleep(1)
        return "valid", HARDCODED_KEY, {"device_id": device_id}
    else:
        print(f"{C.RED}[!] {msg}{C.RESET}")
        if "expired" in msg.lower():
            print(f"{C.YELLOW}[!] Please contact 083135353690 for new password{C.RESET}")
        time.sleep(3)
        sys.exit(0)

# =============================================================================
# ACCOUNT GENERATION
# =============================================================================

session_pool = deque()
session_lock = threading.Lock()

def get_session():
    with session_lock:
        if session_pool:
            return session_pool.popleft()
    s = requests.Session()
    s.verify = False
    proxy = get_next_proxy()
    if proxy:
        s.proxies = {'http': proxy, 'https': proxy}
    return s

def return_session(s):
    with session_lock:
        if len(session_pool) < 200:
            session_pool.append(s)
        else:
            s.close()

for _ in range(min(20, 200)):
    s = requests.Session()
    s.verify = False
    session_pool.append(s)

def generate_password():
    digits = ''.join(random.choices(string.digits, k=random.randint(4, 6)))
    letters = ''.join(random.choices(string.ascii_uppercase, k=random.randint(3, 5)))
    return f"XENONFLASHFF{digits}{letters}"

def generate_cool_name():
    letters = load_custom_letters()
    first_char = letters[0]
    second_char = letters[1]
    length = random.randint(8, 12)
    f_pos = random.randint(0, length - 1)
    k_pos = random.randint(0, length - 1)
    while k_pos == f_pos:
        k_pos = random.randint(0, length - 1)
    name = []
    for i in range(length):
        if i == f_pos:
            name.append(first_char)
        elif i == k_pos:
            name.append(second_char)
        else:
            name.append(random.choice(CHARS))
    return ''.join(name)

def major_login(uid, password, access_token, open_id, region):
    try:
        lang = REGION_LANG.get(region, "en")
        payload_parts = [
            b'\x1a\x132025-08-30 05:19:21"\tfree fire(\x01:\x081.114.13B2Android OS 9 / API-28 (PI/rel.cjw.20220518.114133)J\x08HandheldR\nATM MobilsZ\x04WIFI`\xb6\nh\xee\x05r\x03300z\x1fARMv7 VFPv3 NEON VMH | 2400 | 2\x80\x01\xc9\x0f\x8a\x01\x0fAdreno (TM) 640\x92\x01\rOpenGL ES 3.2\x9a\x01+Google|dfa4ab4b-9dc4-454e-8065-e70c733fa53f\xa2\x01\x0e105.235.139.91\xaa\x01\x02',
            lang.encode("ascii"),
            b'\xb2\x01 1d8ec0240ede109973f3321b9354b44d\xba\x01\x014\xc2\x01\x08Handheld\xca\x01\x10Asus ASUS_I005DA\xea\x01@afcfbf13334be42036e4f742c80b956344bed760ac91b3aff9b607a610ab4390\xf0\x01\x01\xca\x02\nATM Mobils\xd2\x02\x04WIFI\xca\x03 7428b253defc164018c604a1ebbfebdf\xe0\x03\xa8\x81\x02\xe8\x03\xf6\xe5\x01\xf0\x03\xaf\x13\xf8\x03\x84\x07\x80\x04\xe7\xf0\x01\x88\x04\xa8\x81\x02\x90\x04\xe7\xf0\x01\x98\x04\xa8\x81\x02\xc8\x04\x01\xd2\x04=/data/app/com.dts.freefireth-PdeDnOilCSFn37p1AH_FLg==/lib/arm\xe0\x04\x01\xea\x04_2087f61c19f57f2af4e7feff0b24d9d9|/data/app/com.dts.freefireth-PdeDnOilCSFn37p1AH_FLg==/base.apk\xf0\x04\x03\xf8\x04\x01\x8a\x05\x0232\x9a\x05\n2019118692\xb2\x05\tOpenGLES2\xb8\x05\xff\x7f\xc0\x05\x04\xe0\x05\xf3F\xea\x05\x07android\xf2\x05pKqsHT5ZLWrYljNb5Vqh//yFRlaPHSO9NWSQsVvOmdhEEn7W+VHNUK+Q+fduA3ptNrGB0Ll0LRz3WW0jOwesLj6aiU7sZ40p8BfUE/FI/jzSTwRe2\xf8\x05\xfb\xe4\x06\x88\x06\x01\x90\x06\x01\x9a\x06\x014\xa2\x06\x014\xb2\x06"GQ@O\x00\x0e^\x00D\x06UA\x0ePM\r\x13hZ\x07T\x06\x0cm\\V\x0ejYV;\x0bU5'
        ]
        payload = b''.join(payload_parts)
        if region in ["ME", "TH"]:
            url = "https://loginbp.common.ggbluefox.com/MajorLogin"
        else:
            url = "https://loginbp.ggblueshark.com/MajorLogin"
        headers = {
            "Accept-Encoding": "gzip",
            "Authorization": "Bearer",
            "Connection": "Keep-Alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Expect": "100-continue",
            "Host": "loginbp.ggblueshark.com" if region not in ["ME","TH"] else "loginbp.common.ggbluefox.com",
            "ReleaseVersion": "OB54",
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_I005DA Build/PI)",
            "X-GA": "v1 1",
            "X-Unity-Version": "2018.4.11f1"
        }
        data = payload.replace(b'afcfbf13334be42036e4f742c80b956344bed760ac91b3aff9b607a610ab4390', access_token.encode())
        data = data.replace(b'1d8ec0240ede109973f3321b9354b44d', open_id.encode())
        d = encrypt_api(data.hex())
        session = requests.Session()
        session.verify = False
        response = session.post(url, headers=headers, data=bytes.fromhex(d), timeout=5)
        if response.status_code == 200 and len(response.text) > 10:
            jwt_start = response.text.find("eyJ")
            if jwt_start != -1:
                jwt_token = response.text[jwt_start:]
                second_dot = jwt_token.find(".", jwt_token.find(".") + 1)
                if second_dot != -1:
                    jwt_token = jwt_token[:second_dot + 44]
                try:
                    parts = jwt_token.split('.')
                    if len(parts) >= 2:
                        payload_part = parts[1]
                        padding = 4 - len(payload_part) % 4
                        if padding != 4:
                            payload_part += '=' * padding
                        decoded = base64.urlsafe_b64decode(payload_part)
                        data = json.loads(decoded)
                        account_id = data.get('account_id') or data.get('external_id')
                        if account_id:
                            return {"account_id": str(account_id), "jwt_token": jwt_token}
                except:
                    pass
        return {"account_id": "N/A", "jwt_token": ""}
    except:
        return {"account_id": "N/A", "jwt_token": ""}

def generate_account():
    session = get_session()
    try:
        for retry in range(2):
            try:
                password = generate_password()
                name = generate_cool_name()
                resp = session.post(
                    "https://100067.connect.garena.com/api/v2/oauth/guest:register",
                    headers=get_headers(),
                    json={"app_id": 100067, "client_type": 2, "password": password, "source": 2},
                    timeout=5
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if "data" in data and "uid" in data["data"]:
                        uid = data["data"]["uid"]
                        resp2 = session.post(
                            "https://100067.connect.garena.com/oauth/guest/token/grant",
                            headers=get_headers_form(),
                            data={"uid": uid, "password": password, "response_type": "token", "client_type": "2", "client_secret": HEX_KEY, "client_id": "100067"},
                            timeout=5
                        )
                        if resp2.status_code == 200:
                            token_data = resp2.json()
                            open_id = token_data.get('open_id', '')
                            access_token = token_data.get('access_token', '')
                            if open_id and access_token:
                                keystream = [0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30]
                                encoded = ""
                                for i in range(len(open_id)):
                                    encoded += chr(ord(open_id[i]) ^ keystream[i % len(keystream)])
                                hex_str = ''.join(c if 32 <= ord(c) <= 126 else '\\u{:04x}'.format(ord(c)) for c in encoded)
                                field = codecs.decode(hex_str, 'unicode_escape').encode('latin1')
                                if REGION in ["ME", "TH"]:
                                    url_major = "https://loginbp.common.ggbluefox.com/MajorRegister"
                                else:
                                    url_major = "https://loginbp.ggblueshark.com/MajorRegister"
                                lang_code = REGION_LANG.get(REGION, "en")
                                payload = {1: name, 2: access_token, 3: open_id, 5: 102000007, 6: 4, 7: 1, 13: 1, 14: field, 15: lang_code, 16: 1, 17: 1}
                                payload_bytes = build_proto(payload)
                                encrypted_payload = aes_encrypt(payload_bytes.hex())
                                headers_major = {
                                    "Accept-Encoding": "gzip",
                                    "Authorization": "Bearer",
                                    "Connection": "Keep-Alive",
                                    "Content-Type": "application/x-www-form-urlencoded",
                                    "Expect": "100-continue",
                                    "Host": "loginbp.ggblueshark.com" if REGION not in ["ME","TH"] else "loginbp.common.ggbluefox.com",
                                    "ReleaseVersion": "OB54",
                                    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_I005DA Build/PI)",
                                    "X-GA": "v1 1",
                                    "X-Unity-Version": "2018.4.11f1"
                                }
                                session.post(url_major, headers=headers_major, data=encrypted_payload, timeout=5)
                                login_result = major_login(uid, password, access_token, open_id, REGION)
                                account_id = login_result.get("account_id", "N/A")
                                jwt_token = login_result.get("jwt_token", "")
                                if account_id != "N/A":
                                    return_session(session)
                                    return {
                                        "uid": uid,
                                        "password": password,
                                        "name": name,
                                        "account_id": account_id,
                                        "jwt_token": jwt_token,
                                        "success": True
                                    }
            except:
                pass
    except:
        pass
    return_session(session)
    return None

# =============================================================================
# RARITY & OUTPUT FUNCTIONS
# =============================================================================

def count_same_digits(account_id):
    aid = str(account_id)
    if not aid.isdigit() or len(aid) < 5:
        return 0, None
    analyzed = aid[1:]
    digit_counts = Counter(analyzed)
    max_count = max(digit_counts.values()) if digit_counts else 0
    most_digit = max(digit_counts, key=digit_counts.get) if digit_counts else None
    return max_count, most_digit

def get_color_for_digit(count):
    if count >= 9:
        return C.BG_CYAN + C.WHITE + C.BOLD
    elif count == 8:
        return C.BG_RED + C.WHITE
    elif count == 7:
        return C.BG_YELLOW + C.BLACK
    elif count == 6:
        return C.BG_MAGENTA + C.WHITE
    elif count == 5:
        return C.BG_BLUE + C.WHITE
    return C.WHITE

def get_rarity(same_count):
    if same_count >= 9:
        return f"{C.BG_BRIGHT_YELLOW}{C.BLACK} GODLIKE {C.RESET}", "GODLIKE"
    elif same_count == 8:
        return f"{C.BG_BRIGHT_RED}{C.WHITE} MYTHIC {C.RESET}", "MYTHIC"
    elif same_count == 7:
        return f"{C.BG_YELLOW}{C.BLACK} LEGENDARY {C.RESET}", "LEGENDARY"
    elif same_count == 6:
        return f"{C.BG_MAGENTA}{C.WHITE} EPIC {C.RESET}", "EPIC"
    elif same_count == 5:
        return f"{C.BG_BLUE}{C.WHITE} RARE {C.RESET}", "RARE"
    elif same_count == 4:
        return f"{C.BG_GREEN}{C.BLACK} UNCOMMON {C.RESET}", "UNCOMMON"
    else:
        return f"{C.DIM} COMMON {C.RESET}", "COMMON"

def save_account_special(account_data, custom_name=""):
    try:
        same_count = account_data.get('same_digit_count', 0)
        most_digit = account_data.get('most_digit', '')
        uid = account_data.get('uid', 'N/A')
        aid = account_data.get('account_id', 'N/A')
        password = account_data.get('password', 'N/A')
        name = account_data.get('name', 'N/A')
        created_at = account_data.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        jwt_token = account_data.get('jwt_token', '')
        _, rarity_name = get_rarity(same_count)
        
        account_json_file = os.path.join(SPECIAL_FOLDER, "account.json")
        id_txt_file = os.path.join(SPECIAL_FOLDER, "id.txt")
        cariid_file = os.path.join(SPECIAL_FOLDER, "cariid.txt")
        rarity_file = os.path.join(SPECIAL_FOLDER, "by_rarity.txt")
        
        if same_count >= 5 and most_digit:
            cat_file = os.path.join(SPECIAL_FOLDER, f"{most_digit}.txt")
            cat_entry = f"{uid} | {aid} | {password} | [{rarity_name}]\n"
            append_file_atomic(cat_file, cat_entry)
        
        with file_lock:
            all_accounts = []
            if os.path.exists(account_json_file):
                try:
                    with open(account_json_file, 'r', encoding='utf-8') as f:
                        all_accounts = json.load(f)
                except:
                    all_accounts = []
            
            account_entry = {
                "uid": uid,
                "account_id": aid,
                "password": password,
                "name": name,
                "same_digit_count": same_count,
                "most_digit": most_digit,
                "rarity": rarity_name,
                "created_at": created_at,
                "jwt_token": jwt_token,
                "region": REGION_NAME,
                "custom_name": custom_name
            }
            all_accounts.append(account_entry)
            write_file_atomic(account_json_file, json.dumps(all_accounts, indent=2, ensure_ascii=False))
            
            all_ids = [acc.get('account_id', 'N/A') for acc in all_accounts]
            write_file_atomic(id_txt_file, '\n'.join(all_ids))
            
            all_entries = []
            header = ""
            if os.path.exists(cariid_file):
                content = read_file_safe(cariid_file)
                lines = content.split('\n')
                if lines:
                    header = lines[0] + '\n\n'
                    all_entries = [line for line in lines[2:] if line.strip()]
            if not header:
                header = "[9] [8] [7] [6] [5] (URUTAN SAME DIGIT TERBANYAK)\n\n"
            
            display_uid = f"{uid} | {password}" if custom_name else uid
            digit_info = f"{most_digit}x{same_count}" if most_digit else f"{same_count}x"
            new_entry = f"[{same_count}] {display_uid} | {aid} | {digit_info} | [{rarity_name}]"
            all_entries.append(new_entry)
            
            def sort_key(line):
                for digit in range(9, 0, -1):
                    if f"[{digit}]" in line:
                        return -digit
                return 0
            
            all_entries.sort(key=sort_key)
            final_content = header + '\n'.join(all_entries) + '\n'
            write_file_atomic(cariid_file, final_content)
            
            rarity_entry = f"[{rarity_name}] {uid} | {aid} | {password} | {digit_info}\n"
            append_file_atomic(rarity_file, rarity_entry)
    except:
        pass

def save_account_all(account_data, custom_name=""):
    try:
        same_count = account_data.get('same_digit_count', 0)
        uid = account_data.get('uid', 'N/A')
        aid = account_data.get('account_id', 'N/A')
        password = account_data.get('password', 'N/A')
        name = account_data.get('name', 'N/A')
        created_at = account_data.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        jwt_token = account_data.get('jwt_token', '')
        _, rarity_name = get_rarity(same_count)
        
        account_json_file = os.path.join(ALL_FOLDER, "account.json")
        id_txt_file = os.path.join(ALL_FOLDER, "id.txt")
        
        with file_lock:
            all_accounts = []
            if os.path.exists(account_json_file):
                try:
                    with open(account_json_file, 'r', encoding='utf-8') as f:
                        all_accounts = json.load(f)
                except:
                    all_accounts = []
            
            account_entry = {
                "uid": uid,
                "account_id": aid,
                "password": password,
                "name": name,
                "same_digit_count": same_count,
                "rarity": rarity_name,
                "created_at": created_at,
                "jwt_token": jwt_token,
                "region": REGION_NAME,
                "custom_name": custom_name
            }
            all_accounts.append(account_entry)
            write_file_atomic(account_json_file, json.dumps(all_accounts, indent=2, ensure_ascii=False))
            
            all_ids = [acc.get('account_id', 'N/A') for acc in all_accounts]
            write_file_atomic(id_txt_file, '\n'.join(all_ids))
    except:
        pass

def print_output(no, account_data, output_mode, custom_name="", rare_only=False):
    same_count = account_data.get('same_digit_count', 0)
    most_digit = account_data.get('most_digit', '')
    uid = account_data.get('uid', 'N/A')
    aid = account_data.get('account_id', 'N/A')
    password = account_data.get('password', 'N/A')
    
    if rare_only and same_count < 5:
        return False
    
    color = get_color_for_digit(same_count)
    rarity_colored, rarity_name = get_rarity(same_count)
    prefix = f"[{custom_name}]" if custom_name else ""
    
    if same_count >= 5:
        digit_info = f"{most_digit}x{same_count}" if most_digit else f"{same_count}x"
        if output_mode == 'full':
            print(f"{color}[{no}] {prefix} {uid} | {aid} | {password} | {rarity_colored} | {digit_info}{C.RESET}")
        else:
            print(f"{color}[{no}] {prefix} {aid} | {rarity_colored} | {digit_info}{C.RESET}")
    else:
        if output_mode == 'full':
            print(f"{C.WHITE}[{no}] {prefix} {uid} | {aid} | {password} | {rarity_colored}{C.RESET}")
        else:
            print(f"{C.WHITE}[{no}] {prefix} {aid} | {rarity_colored}{C.RESET}")
    return True

# =============================================================================
# CONFIGURATION FUNCTIONS
# =============================================================================

def load_output_mode():
    content = read_file_safe(OUTPUT_MODE_FILE).strip()
    return content if content else "clean"

def save_output_mode(mode):
    write_file_atomic(OUTPUT_MODE_FILE, mode)

def load_custom_name():
    content = read_file_safe(CUSTOM_NAME_FILE).strip()
    return content if content else ""

def save_custom_name(name):
    write_file_atomic(CUSTOM_NAME_FILE, name)

def load_rare_only():
    content = read_file_safe(RARE_ONLY_FILE).strip()
    return content == "true"

def save_rare_only(enabled):
    write_file_atomic(RARE_ONLY_FILE, "true" if enabled else "false")

def load_custom_letters():
    content = read_file_safe(CUSTOM_LETTERS_FILE).strip()
    if content and len(content) == 2 and content.isalpha():
        return content.upper()
    return "AB"

def save_custom_letters(letters):
    write_file_atomic(CUSTOM_LETTERS_FILE, letters.upper())

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# =============================================================================
# CONFIGURATION MENU
# =============================================================================

def config_menu():
    global rare_only
    clear_screen()
    print(f"{C.BG_BRIGHT_CYAN}{C.BLACK}{C.BOLD}")
    print("  CONFIGURATION MENU  ")
    print(C.RESET)
    print()
    
    current_mode = load_output_mode()
    print(f"{C.YELLOW}[1] Output Mode: {C.BOLD}{current_mode.upper()}{C.RESET}")
    print(f"    {C.DIM}clean = only account_id{C.RESET}")
    print(f"    {C.DIM}full  = UID | Account_ID | Password | 5x7{C.RESET}")
    print()
    
    current_name = load_custom_name()
    display_name = current_name if current_name else "None"
    print(f"{C.YELLOW}[2] Custom Name: {C.BOLD}{display_name}{C.RESET}")
    print(f"    {C.DIM}max 2 characters (e.g. A, B, X, Z){C.RESET}")
    print()
    
    current_letters = load_custom_letters()
    print(f"{C.YELLOW}[3] Account Letters: {C.BOLD}{current_letters}{C.RESET}")
    print(f"    {C.DIM}2 letters inside account name (e.g. AB, XY, FK){C.RESET}")
    print()
    
    rare_enabled = load_rare_only()
    rare_status = "ON" if rare_enabled else "OFF"
    print(f"{C.YELLOW}[4] Rare Only Mode: {C.BOLD}{rare_status}{C.RESET}")
    print(f"    {C.DIM}Only show accounts with x5+ (5x, 6x, 7x, 8x, 9x){C.RESET}")
    print()
    
    print(f"{C.YELLOW}[5] Back to Main Menu{C.RESET}")
    print()
    
    choice = input(f"{C.CYAN}Select [1/2/3/4/5]: {C.RESET}").strip()
    
    if choice == '1':
        clear_screen()
        print(f"{C.BG_BRIGHT_CYAN}{C.BLACK}{C.BOLD}")
        print("  OUTPUT MODE  ")
        print(C.RESET)
        print()
        print(f"{C.GREEN}1{C.RESET}. Clean - Only account_id")
        print(f"{C.GREEN}2{C.RESET}. Full  - UID | Account_ID | Password | 5x7")
        print()
        sub = input(f"{C.CYAN}Select [1/2]: {C.RESET}").strip()
        if sub == '2':
            save_output_mode('full')
            print(f"{C.GREEN}[+] Output mode set to: FULL{C.RESET}")
        else:
            save_output_mode('clean')
            print(f"{C.GREEN}[+] Output mode set to: CLEAN{C.RESET}")
        time.sleep(1)
        return config_menu()
    
    elif choice == '2':
        clear_screen()
        print(f"{C.BG_BRIGHT_CYAN}{C.BLACK}{C.BOLD}")
        print("  CUSTOM NAME  ")
        print(C.RESET)
        print()
        print(f"{C.CYAN}Enter custom name (max 2 characters){C.RESET}")
        print(f"{C.DIM}Leave empty to remove custom name{C.RESET}")
        print()
        name = input(f"{C.YELLOW}Name: {C.RESET}").strip().upper()
        if name == "":
            save_custom_name("")
            print(f"{C.GREEN}[+] Custom name removed{C.RESET}")
        elif len(name) <= 2 and name.isalnum():
            save_custom_name(name)
            print(f"{C.GREEN}[+] Custom name set to: {name}{C.RESET}")
        else:
            print(f"{C.RED}[!] Invalid! Max 2 alphanumeric characters{C.RESET}")
        time.sleep(1)
        return config_menu()
    
    elif choice == '3':
        clear_screen()
        print(f"{C.BG_BRIGHT_CYAN}{C.BLACK}{C.BOLD}")
        print("  ACCOUNT LETTERS  ")
        print(C.RESET)
        print()
        current = load_custom_letters()
        print(f"{C.CYAN}Current letters: {C.BOLD}{current}{C.RESET}")
        print()
        print(f"{C.CYAN}Enter 2 letters for account name{C.RESET}")
        print(f"{C.DIM}Example: AB, XY, FK, 12{C.RESET}")
        print()
        letters = input(f"{C.YELLOW}Letters: {C.RESET}").strip().upper()
        if len(letters) == 2 and letters.isalpha():
            save_custom_letters(letters)
            print(f"{C.GREEN}[+] Account letters set to: {letters}{C.RESET}")
        elif letters == "":
            save_custom_letters("AB")
            print(f"{C.GREEN}[+] Account letters reset to: AB{C.RESET}")
        else:
            print(f"{C.RED}[!] Invalid! Must be exactly 2 letters (A-Z){C.RESET}")
        time.sleep(2)
        return config_menu()
    
    elif choice == '4':
        rare_enabled = not rare_enabled
        save_rare_only(rare_enabled)
        status = "ON" if rare_enabled else "OFF"
        print(f"{C.GREEN}[+] Rare Only Mode set to: {status}{C.RESET}")
        time.sleep(1)
        return config_menu()
    
    else:
        return

# =============================================================================
# MAIN MENU
# =============================================================================

def show_menu():
    clear_screen()
    print(f"{C.BG_BRIGHT_BLUE}{C.BRIGHT_WHITE}{C.BOLD}")
    print(f"  XENON FF CHECKER {VERSION}  ")
    print(C.RESET)
    print(f"{C.DIM}Developer: {DEV_NAME}{C.RESET}")
    print()
    print(f"{C.CYAN}========================================{C.RESET}")
    print(f"{C.CYAN}  {C.GREEN}1{C.CYAN}. Normal Mode{C.RESET}")
    print(f"{C.CYAN}  {C.GREEN}2{C.CYAN}. Target Mode{C.RESET}")
    print(f"{C.CYAN}  {C.GREEN}3{C.CYAN}. Rare Only Mode{C.RESET}")
    print(f"{C.CYAN}  {C.GREEN}4{C.CYAN}. Configuration{C.RESET}")
    print(f"{C.CYAN}  {C.GREEN}5{C.CYAN}. Exit{C.RESET}")
    print(f"{C.CYAN}========================================{C.RESET}")
    print()
    print(f"{C.DIM}RARITY: {C.WHITE}Common {C.GREEN}Uncommon {C.BLUE}Rare {C.MAGENTA}Epic {C.YELLOW}Legendary {C.RED}Mythic {C.BG_BRIGHT_YELLOW}{C.BLACK}Godlike{C.RESET}")
    print()
    return input(f"{C.CYAN}Select [1/2/3/4/5]: {C.RESET}").strip()

# =============================================================================
# WORKER AND GENERATOR
# =============================================================================

running = True
last_success_time = time.time()
stuck_warning_shown = False
target_mode_active = False
target_id = None
target_progress = 0
rare_only = False
THREAD_COUNT = 200
FAIL_SLEEP = 0

stats = {
    'total': 0,
    'same_5': 0,
    'same_6': 0,
    'same_7': 0,
    'same_8': 0,
    'same_9': 0,
    'same_10': 0,
    'same_11plus': 0,
    'start_time': time.time()
}
stats_lock = threading.Lock()

def show_stuck_warning():
    global stuck_warning_shown
    if stuck_warning_shown:
        return
    stuck_warning_shown = True
    print()
    print(f"{C.BG_BRIGHT_RED}{C.BRIGHT_WHITE}{C.BOLD}")
    print("  RATE LIMIT DETECTED  ")
    print(C.RESET)
    print(f"{C.YELLOW}No generation in last 10 seconds{C.RESET}")
    print(f"{C.YELLOW}Possible rate limit or IP banned{C.RESET}")
    print(f"{C.CYAN}Solution: Enable Airplane Mode or Change IP{C.RESET}")
    print()
    stuck_warning_shown = False

def stuck_monitor():
    global last_success_time, stuck_warning_shown
    while running:
        time.sleep(10)
        if not running:
            break
        elapsed = time.time() - last_success_time
        if elapsed > 10 and stats['total'] > 0:
            show_stuck_warning()

monitor_thread = threading.Thread(target=stuck_monitor, daemon=True)
monitor_thread.start()

def worker(output_mode, custom_name="", rare_only=False):
    global running, last_success_time, target_mode_active, target_id, target_progress
    
    while running:
        account = generate_account()
        if account and account.get("success"):
            uid = account["uid"]
            aid = account["account_id"]
            if aid == "N/A":
                aid = str(uid)
            password = account["password"]
            name = account["name"]
            jwt_token = account.get("jwt_token", "")
            
            same_count, most_digit = count_same_digits(aid)
            
            with stats_lock:
                stats['total'] += 1
                if same_count == 5:
                    stats['same_5'] += 1
                elif same_count == 6:
                    stats['same_6'] += 1
                elif same_count == 7:
                    stats['same_7'] += 1
                elif same_count == 8:
                    stats['same_8'] += 1
                elif same_count == 9:
                    stats['same_9'] += 1
                elif same_count == 10:
                    stats['same_10'] += 1
                elif same_count >= 11:
                    stats['same_11plus'] += 1
                current_no = stats['total']
            
            account_info = {
                'uid': uid,
                'password': password,
                'account_id': aid,
                'name': name,
                'region': REGION_NAME,
                'same_digit_count': same_count,
                'most_digit': most_digit,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'watermark': WATERMARK,
                'jwt_token': jwt_token
            }
            
            if target_mode_active and target_id:
                if aid == target_id or uid == target_id:
                    print(f"{C.BG_BRIGHT_GREEN}{C.BLACK}{C.BOLD}")
                    print("  TARGET FOUND!  ")
                    print(C.RESET)
                    print(f"{C.GREEN}UID: {uid} | Account_ID: {aid} | Password: {password}{C.RESET}")
                    target_progress = 0
                else:
                    target_progress += 1
                    if target_progress % 10 == 0:
                        print(f"{C.YELLOW}[TARGET] Searching... {target_progress} accounts checked{C.RESET}")
            
            printed = print_output(current_no, account_info, output_mode, custom_name, rare_only)
            
            if same_count >= 5:
                save_account_special(account_info, custom_name)
            else:
                save_account_all(account_info, custom_name)
            
            last_success_time = time.time()
        else:
            time.sleep(FAIL_SLEEP)

def run_generator(output_mode, custom_name="", rare_only=False, is_target=False):
    global running, target_mode_active, target_id, target_progress, THREAD_COUNT
    
    clear_screen()
    mode_text = "TARGET" if is_target else ("RARE ONLY" if rare_only else "NORMAL")
    target_info = f" | Target: {target_id}" if is_target and target_id else ""
    
    print(f"{C.BG_BRIGHT_CYAN}{C.BLACK}{C.BOLD}")
    print(f"  XENON FF CHECKER {VERSION}  ")
    print(C.RESET)
    print(f"{C.DIM}Developer: {DEV_NAME}{C.RESET}")
    print()
    print(f"{C.CYAN}MODE:     {C.BOLD}{mode_text}{C.RESET}")
    print(f"{C.CYAN}OUTPUT:   {C.BOLD}{output_mode.upper()}{C.RESET}")
    if custom_name:
        print(f"{C.CYAN}PREFIX:   {C.BOLD}[{custom_name}]{C.RESET}")
    letters = load_custom_letters()
    print(f"{C.CYAN}LETTERS:  {C.BOLD}{letters}{C.RESET}")
    print(f"{C.CYAN}REGION:   {C.BOLD}{REGION_NAME}{C.RESET}")
    print(f"{C.CYAN}THREADS:  {C.BOLD}{THREAD_COUNT}{C.RESET}")
    print(f"{C.CYAN}DELAY:    {C.BOLD}0ms{C.RESET}")
    if is_target:
        print(f"{C.CYAN}TARGET:   {C.BOLD}{target_id}{C.RESET}")
        print(f"{C.YELLOW}[*] Target mode: checking each account for match{C.RESET}")
    if rare_only:
        print(f"{C.YELLOW}[*] Rare Only: Only showing x5+ accounts{C.RESET}")
    print()
    print(f"{C.DIM}RARITY: {C.WHITE}Common {C.GREEN}Uncommon {C.BLUE}Rare {C.MAGENTA}Epic {C.YELLOW}Legendary {C.RED}Mythic {C.BG_BRIGHT_YELLOW}{C.BLACK}Godlike{C.RESET}")
    print()
    print(f"{C.GREEN}SAVE: XENON_FF/special/ & XENON_FF/allaccount/{C.RESET}")
    print()
    print(f"{C.YELLOW}[CTRL+C] to stop{C.RESET}")
    print()
    
    try:
        with ThreadPoolExecutor(max_workers=THREAD_COUNT) as executor:
            futures = [executor.submit(worker, output_mode, custom_name, rare_only) for _ in range(THREAD_COUNT)]
            for future in as_completed(futures):
                if not running:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                future.result()
    except KeyboardInterrupt:
        print()
        print(f"{C.BG_YELLOW}{C.BLACK}{C.BOLD}")
        print("  STOPPING...  ")
        print(C.RESET)
        running = False
        time.sleep(1)
    except Exception as e:
        print()
        print(f"{C.BG_BRIGHT_RED}{C.BRIGHT_WHITE}{C.BOLD}")
        print("  ERROR  ")
        print(C.RESET)
        print(f"{C.RED}{e}{C.RESET}")
    
    time.sleep(1)
    elapsed = time.time() - stats['start_time']
    print()
    print(f"{C.BG_BRIGHT_GREEN}{C.BRIGHT_WHITE}{C.BOLD}")
    print("  XENON FF CHECKER - COMPLETE  ")
    print(C.RESET)
    print()
    print(f"{C.GREEN}TOTAL:     {stats['total']}{C.RESET}")
    print(f"{C.BG_BLUE}{C.WHITE}5x:        {stats['same_5']}{C.RESET}")
    print(f"{C.BG_MAGENTA}{C.WHITE}6x:        {stats['same_6']}{C.RESET}")
    print(f"{C.BG_YELLOW}{C.BLACK}7x:        {stats['same_7']}{C.RESET}")
    print(f"{C.BG_RED}{C.WHITE}8x:        {stats['same_8']}{C.RESET}")
    print(f"{C.BG_CYAN}{C.WHITE}{C.BOLD}9x+:       {stats['same_9'] + stats['same_10'] + stats['same_11plus']}{C.RESET}")
    print(f"{C.CYAN}TIME:     {elapsed:.1f}s{C.RESET}")
    if elapsed > 0:
        print(f"{C.CYAN}SPEED:    {stats['total']/elapsed:.2f} acc/s{C.RESET}")
    print()

# =============================================================================
# MAIN
# =============================================================================

def main():
    global running, THREAD_COUNT, REGION, REGION_NAME, PROXY_LIST, target_mode_active, target_id, rare_only
    
    # Start Telegram command handler in background
    telegram_thread = threading.Thread(target=handle_telegram_commands, daemon=True)
    telegram_thread.start()
    
    # Load proxies
    PROXY_LIST = load_proxies_from_file()
    
    # Activation flow with device password
    mode, key, info = activation_flow()
    
    clear_screen()
    print(f"{C.BG_BRIGHT_MAGENTA}{C.BRIGHT_WHITE}{C.BOLD}")
    print("  XENON FF PROXY CHECKER  ")
    print(C.RESET)
    print()
    print(f"{C.CYAN}========================================{C.RESET}")
    print(f"{C.CYAN}  PROXY + BYPASS MODE{C.RESET}")
    print(f"{C.CYAN}  Auto proxy.txt loader{C.RESET}")
    print(f"{C.CYAN}  Auto region rotate{C.RESET}")
    print(f"{C.CYAN}  NO DELAY | UNLIMITED THREADS{C.RESET}")
    print(f"{C.CYAN}========================================{C.RESET}")
    print()
    
    # Proxy status
    if len(PROXY_LIST) > 1:
        print(f"{C.GREEN}[+] Proxies loaded: {len(PROXY_LIST)-1}{C.RESET}")
    else:
        print(f"{C.YELLOW}[!] No proxy.txt found - running direct{C.RESET}")
        print(f"{C.DIM}Create proxy.txt with format: ip:port{C.RESET}")
    print()
    
    # Thread input
    try:
        thread_input = input(f"{C.YELLOW}Threads (default 200, unlimited): {C.RESET}").strip()
        if thread_input:
            THREAD_COUNT = int(thread_input)
        else:
            THREAD_COUNT = 200
    except:
        THREAD_COUNT = 200
    
    print(f"{C.GREEN}[+] Threads: {THREAD_COUNT}{C.RESET}")
    time.sleep(0.5)
    
    # Target mode
    clear_screen()
    print(f"{C.BG_BRIGHT_RED}{C.BRIGHT_WHITE}{C.BOLD}")
    print("  TARGET MODE  ")
    print(C.RESET)
    print()
    print(f"{C.YELLOW}Enter target Account ID or UID to hunt{C.RESET}")
    print(f"{C.DIM}Leave empty to skip (Normal Mode){C.RESET}")
    print()
    target_input = input(f"{C.CYAN}Target ID: {C.RESET}").strip()
    if target_input:
        target_id = target_input
        target_mode_active = True
        print(f"{C.BG_BRIGHT_GREEN}{C.BLACK} TARGET SET: {target_id} {C.RESET}")
    else:
        target_mode_active = False
        target_id = None
        print(f"{C.DIM}Normal mode (no target){C.RESET}")
    time.sleep(0.5)
    
    # Output mode
    clear_screen()
    print(f"{C.BG_BRIGHT_BLUE}{C.BRIGHT_WHITE}{C.BOLD}")
    print("  OUTPUT MODE  ")
    print(C.RESET)
    print()
    print(f"{C.GREEN}1{C.RESET}. Clean - Only Account ID + Rarity")
    print(f"{C.GREEN}2{C.RESET}. Full  - UID | Account_ID | Password | Rarity | 5x7")
    print()
    out_choice = input(f"{C.CYAN}Select [1/2]: {C.RESET}").strip()
    if out_choice == '2':
        save_output_mode('full')
        output_mode = 'full'
    else:
        save_output_mode('clean')
        output_mode = 'clean'
    
    # Custom letters
    clear_screen()
    print(f"{C.BG_BRIGHT_BLUE}{C.BRIGHT_WHITE}{C.BOLD}")
    print("  CUSTOM LETTERS  ")
    print(C.RESET)
    print()
    current = load_custom_letters()
    print(f"{C.CYAN}Current: {C.BOLD}{current}{C.RESET}")
    print()
    letters = input(f"{C.YELLOW}Letters (Enter=keep {current}): {C.RESET}").strip().upper()
    if len(letters) == 2 and letters.isalpha():
        save_custom_letters(letters)
    
    # Start
    running = True
    stats['total'] = 0
    stats['same_5'] = 0
    stats['same_6'] = 0
    stats['same_7'] = 0
    stats['same_8'] = 0
    stats['same_9'] = 0
    stats['same_10'] = 0
    stats['same_11plus'] = 0
    stats['start_time'] = time.time()
    
    run_generator(output_mode, "", load_rare_only(), target_mode_active)

if __name__ == "__main__":
    try:
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad
        main()
    except ImportError:
        print(f"{C.BG_BRIGHT_RED}{C.BRIGHT_WHITE}{C.BOLD}")
        print("  ERROR  ")
        print(C.RESET)
        print(f"{C.RED}pip install pycryptodome{C.RESET}")
        sys.exit(0)
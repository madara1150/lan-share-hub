"""Thai / English UI strings."""

S = {
    "app_title": ("LAN Share Hub", "LAN Share Hub"),
    "brand_sub": ("แชร์ไฟล์และเว็บให้เพื่อนในวง LAN", "Share files & websites on your LAN"),
    "lang_switch": ("English", "ภาษาไทย"),
    "dark": ("ธีมมืด", "Dark"),
    "light": ("ธีมสว่าง", "Light"),
    "your_ip": ("IP เครื่องนี้", "This computer"),
    "no_network": ("ไม่ได้เชื่อมต่อเครือข่าย", "Not connected to a network"),
    "shares": ("รายการที่แชร์", "Shares"),
    "new_files": ("แชร์โฟลเดอร์", "Share a folder"),
    "new_site": ("เปิดเว็บไซต์", "Host a website"),
    "drop_hint": ("ลากโฟลเดอร์มาวางที่นี่ก็ได้", "or drop a folder here"),
    "mode_files": ("แชร์ไฟล์", "File sharing"),
    "mode_site": ("เว็บไซต์", "Website"),
    "mode_proxy": ("เทสแอปจาก localhost", "Test a localhost app"),
    "new_proxy": ("ให้เพื่อนเทสแอป localhost", "Let friends test localhost"),
    "target": ("แอปที่รันอยู่", "Your app"),
    "target_on": ("● เจอแอปแล้ว", "● App is running"),
    "target_off": ("○ ยังไม่เจอแอปที่พอร์ตนี้ — เปิด dev server ก่อน (เช่น npm run dev)",
                   "○ Nothing running on this port — start your dev server (e.g. npm run dev)"),
    "detect": ("ค้นหาแอปที่เปิดอยู่", "Find running apps"),
    "detect_none": ("ไม่พบ dev server ที่เปิดอยู่ในพอร์ตยอดนิยม", "No dev server found on the usual ports"),
    "proxy_note": ("เพื่อนเปิดลิงก์ด้านบน = เห็นเหมือนคุณเปิด localhost:{port} เอง รวมถึง hot reload "
                   "ไม่ต้องแก้ config ของโปรเจค", "Friends opening the link above see exactly what you see at "
                   "localhost:{port}, hot reload included — no project config changes needed"),
    "status_on": ("กำลังแชร์", "Sharing"),
    "status_off": ("หยุดอยู่", "Stopped"),
    "start": ("เริ่มแชร์", "Start sharing"),
    "stop": ("หยุดแชร์", "Stop sharing"),
    "start_all": ("เริ่มทั้งหมด", "Start all"),
    "stop_all": ("หยุดทั้งหมด", "Stop all"),
    "link_title": ("ลิงก์สำหรับเพื่อน", "Link for your friends"),
    "link_hint": ("ให้เพื่อนที่ต่อ Wi-Fi / LAN เดียวกันเปิดลิงก์นี้ หรือสแกน QR ด้วยมือถือ",
                  "Friends on the same Wi-Fi / LAN open this link or scan the QR code"),
    "link_off": ("กด \"เริ่มแชร์\" แล้วลิงก์จะใช้งานได้", "Press \"Start sharing\" to make the link work"),
    "copy": ("คัดลอก", "Copy"),
    "copied": ("คัดลอกแล้ว ✓", "Copied ✓"),
    "open_browser": ("เปิดในเบราว์เซอร์", "Open in browser"),
    "settings": ("ตั้งค่า", "Settings"),
    "name": ("ชื่อ", "Name"),
    "folder": ("โฟลเดอร์", "Folder"),
    "choose": ("เลือก…", "Choose…"),
    "show_folder": ("เปิดโฟลเดอร์", "Show folder"),
    "type": ("ประเภท", "Type"),
    "port": ("พอร์ต", "Port"),
    "allow_upload": ("ให้เพื่อนอัปโหลดไฟล์เข้ามาได้", "Let friends upload files"),
    "upload_note": ("ไฟล์ที่อัปโหลดจะไม่เขียนทับไฟล์เดิม ถ้าชื่อซ้ำจะตั้งชื่อใหม่ให้",
                    "Uploads never overwrite files — duplicates get a new name"),
    "upload_site_note": ("โหมดเว็บไซต์ไม่รับการอัปโหลด", "Websites don't accept uploads"),
    "use_password": ("ตั้งรหัสผ่าน", "Require a password"),
    "password": ("รหัสผ่าน", "Password"),
    "password_hint": ("เพื่อนพิมพ์ชื่ออะไรก็ได้ แล้วใส่รหัสนี้", "Friends can type any user name, then this password"),
    "show": ("แสดง", "Show"),
    "auto_start": ("เริ่มแชร์อัตโนมัติเมื่อเปิดโปรแกรม", "Start automatically when the app opens"),
    "delete": ("ลบรายการนี้", "Remove share"),
    "delete_confirm": ("ลบ \"{name}\" ออกจากรายการ?\n(ไฟล์ในโฟลเดอร์จะไม่ถูกลบ)",
                       "Remove \"{name}\" from the list?\n(The files in the folder are not deleted.)"),
    "activity": ("กิจกรรม", "Activity"),
    "clear": ("ล้าง", "Clear"),
    "visitors": ("{n} เครื่องเข้ามาแล้ว", "Connected devices: {n}"),
    "no_activity": ("ยังไม่มีใครเข้ามา", "No visitors yet"),
    "col_time": ("เวลา", "Time"),
    "col_device": ("เครื่อง", "Device"),
    "col_action": ("ทำอะไร", "Action"),
    "col_file": ("ไฟล์ / หน้า", "File / page"),
    "act_view": ("เปิดดู", "Viewed"),
    "act_download": ("ดาวน์โหลด", "Downloaded"),
    "act_upload": ("อัปโหลด", "Uploaded"),
    "act_denied": ("ถูกปฏิเสธ", "Denied"),
    "act_auth": ("รหัสผิด / ยังไม่ใส่รหัส", "Wrong / missing password"),
    "empty_title": ("เริ่มแชร์ได้ในไม่กี่วินาที", "Start sharing in seconds"),
    "empty_body": ("ให้เพื่อนเทสแอปที่คุณรันบน localhost, แชร์โฟลเดอร์ไฟล์ หรือเปิดเว็บ static\n"
                   "แล้วส่งลิงก์หรือ QR code ให้เพื่อนที่ต่อเครือข่ายเดียวกัน",
                   "Let friends test the app you run on localhost, share a folder, or host a static site,\n"
                   "then send the link or QR code to friends on the same network"),
    "err_port": ("พอร์ต {port} ถูกใช้อยู่ ลองเปลี่ยนพอร์ตเป็น {free}", "Port {port} is busy. Try port {free} instead."),
    "use_port": ("ใช้พอร์ต {port}", "Use port {port}"),
    "err_folder": ("ไม่พบโฟลเดอร์ \"{folder}\"", "Folder \"{folder}\" was not found"),
    "err_start": ("เริ่มแชร์ไม่ได้", "Couldn't start sharing"),
    "no_index_warn": ("โฟลเดอร์นี้ยังไม่มี index.html — เพื่อนจะเห็นหน้า \"ยังไม่มีหน้าเว็บ\"",
                      "This folder has no index.html — friends will see a \"No web page yet\" page"),
    "restart_note": ("เปลี่ยนพอร์ตแล้ว เริ่มแชร์ใหม่ให้อัตโนมัติ", "Port changed — sharing restarted"),
    "firewall_tip": ("ถ้าเพื่อนเปิดไม่ได้: ตรวจว่าอยู่ Wi-Fi เดียวกัน และกด \"อนุญาต\" เมื่อไฟร์วอลล์ถาม",
                     "Friends can't connect? Make sure you're on the same Wi-Fi and allow the app in your firewall"),
    "choose_folder": ("เลือกโฟลเดอร์", "Choose a folder"),
    "about": ("เกี่ยวกับ", "About"),
    "about_msg": ("แชร์ไฟล์และเปิดเว็บไซต์ให้เพื่อนในเครือข่ายเดียวกัน\n"
                  "ทำงานในเครื่อง 100% ไม่ส่งไฟล์ขึ้นอินเทอร์เน็ต\n\nเวอร์ชัน {v} · MIT License · Tanathip",
                  "Share files and host websites for friends on your network.\n"
                  "Runs 100% on your computer — nothing goes to the internet.\n\nVersion {v} · MIT License · Tanathip"),
    "quit_running": ("ยังมี {n} รายการกำลังแชร์อยู่ ปิดโปรแกรมแล้วจะหยุดแชร์ทั้งหมด",
                     "{n} shares are running. Closing the app stops them all."),
    "quit": ("ปิดโปรแกรม", "Quit"),
    "cancel": ("ยกเลิก", "Cancel"),
}

_lang = "th"


def set_lang(lang: str):
    global _lang
    _lang = lang if lang in ("th", "en") else "th"


def lang() -> str:
    return _lang


def tr(key: str, **kw) -> str:
    th, en = S[key]
    s = th if _lang == "th" else en
    return s.format(**kw) if kw else s

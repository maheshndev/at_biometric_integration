import os
from datetime import datetime
from frappe import get_site_path

def cleanup_old_attendance_logs():
    ATTENDANCE_DIR = get_site_path("public", "files", "attendance_logs")
    today = datetime.now().strftime("%Y-%m-%d")

    for f in os.listdir(ATTENDANCE_DIR):
        if f.endswith(".json") and today not in f:
            os.remove(os.path.join(ATTENDANCE_DIR, f))

import frappe, os, json
from frappe.utils import getdate, nowdate
from zk import ZK

PUNCH_MAPPING = {
    0: "Check-In", 1: "Check-Out", 2: "Break-Out", 3: "Break-In",
    4: "Overtime Start", 5: "Overtime End"
}

ATTENDANCE_NAME = "attendance_logs"
ATTENDANCE_DIR = frappe.get_site_path("public", "files", ATTENDANCE_NAME)


def get_attendance_file_path(ip):
    date_str = getdate(nowdate()).strftime("%Y-%m-%d")
    return os.path.join(ATTENDANCE_DIR, f"attendance_{ip}_{date_str}.json")


def load_attendance_data(ip):
    file_path = get_attendance_file_path(ip)
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return []


def save_attendance_data(ip, attendance):
    os.makedirs(ATTENDANCE_DIR, exist_ok=True)
    file_path = get_attendance_file_path(ip)
    with open(file_path, "w") as f:
        json.dump(attendance, f, indent=4)


def fetch_attendance_from_device(ip, port):
    """Fetch logs from biometric device using zk library."""
    try:
        conn = ZK(ip, port=int(port), timeout=10)
        connection = conn.connect()
        attendance_logs = connection.get_attendance()
        connection.disconnect()
        return attendance_logs
    except Exception as e:
        frappe.log_error(f"Error connecting to device {ip}: {e}", "Biometric Fetch Error")
        return []


def process_attendance_logs(ip, logs):
    """Merge new logs into JSON file and return new records."""
    existing = load_attendance_data(ip)
    existing_keys = {(i["user_id"], i["timestamp"]) for i in existing}
    new_records = []

    for log in logs:
        ts = log.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        key = (log.user_id, ts)
        if key not in existing_keys:
            new_records.append({
                "uid": log.uid,
                "user_id": log.user_id,
                "timestamp": ts,
                "status": log.status,
                "punch": log.punch,
                "punch_type": PUNCH_MAPPING.get(log.punch, "Unknown"),
                "device_ip": ip
            })

    if new_records:
        existing.extend(new_records)
        save_attendance_data(ip, existing)

    return new_records

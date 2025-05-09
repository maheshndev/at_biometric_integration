import frappe
import json
import os
from frappe.utils import getdate, nowdate, cint, add_days, today, get_datetime, time_diff_in_hours, add_to_date
from zk import ZK
from datetime import datetime, timedelta


PUNCH_MAPPING = {
    0: "Check-In",
    1: "Check-Out",
    2: "Break-Out",
    3: "Break-In",
    4: "Overtime Start",
    5: "Overtime End"
}

PUNCH_STATUS = {
    1: "Check-In",
    4: "Check-Out",
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
    file_path = get_attendance_file_path(ip)
    with open(file_path, "w") as f:
        json.dump(attendance, f, indent=4)

def fetch_attendance_from_device(ip, port):
    try:
        conn = ZK(ip, port=int(port), timeout=10, force_udp=False, ommit_ping=False).connect()
        if conn:
            attendance_logs = conn.get_attendance()
            conn.disconnect()
            return attendance_logs
    except Exception as e:
        frappe.log_error(f"Error connecting to device {ip}: {str(e)}", "Biometric Device Connection Error")
    return []

def process_attendance_logs(ip, logs):
    existing_data = load_attendance_data(ip)
    existing_keys = {(entry['user_id'], entry['timestamp']) for entry in existing_data}
    new_records = []

    for log in logs:
        timestamp_str = log.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        key = (log.user_id, timestamp_str)
        if key not in existing_keys:
            new_records.append({
                "uid": log.uid,
                "user_id": log.user_id,
                "timestamp": timestamp_str,
                "status": log.status,
                "punch": log.punch,
                "punch_type": PUNCH_MAPPING.get(log.punch, "Unknown")
            })

    if new_records:
        existing_data.extend(new_records)
        save_attendance_data(ip, existing_data)

    return new_records

def create_frappe_attendance(ip):
    attendance_data = load_attendance_data(ip)
    if not attendance_data:
        return

    user_ids = list(set([record['user_id'] for record in attendance_data]))
    employee_map = {
        r.attendance_device_id: r.name
        for r in frappe.get_all("Employee",
            filters={"attendance_device_id": ["in", user_ids]},
            fields=["name", "attendance_device_id"]
        )
    }

    timestamps = [record['timestamp'] for record in attendance_data]
    existing_checkins = {
        (c.employee, c.time.strftime("%Y-%m-%d %H:%M:%S"))
        for c in frappe.get_all("Employee Checkin",
            filters={"time": ["in", timestamps]},
            fields=["employee", "time"]
        )
    }

    checkins_to_create = []
    for record in attendance_data:
        employee = employee_map.get(record['user_id'])
        if not employee:
            continue
        key = (employee, record['timestamp'])
        if key in existing_checkins:
            continue
        log_type = "IN" if record['punch'] in [0, 4] else "OUT"
        checkins_to_create.append({
            "doctype": "Employee Checkin",
            "employee": employee,
            "time": record['timestamp'],
            "log_type": log_type,
            "device_id": record['user_id']
        })

    for doc in checkins_to_create:
        try:
            frappe.get_doc(doc).insert()
        except Exception as e:
            frappe.log_error(f"Failed to insert checkin: {doc} | {e}", "Checkin Insertion Error")
    if checkins_to_create:
        frappe.db.commit()

def cleanup_old_attendance_logs():
    today_str = datetime.now().strftime("%Y-%m-%d")
    for filename in os.listdir(ATTENDANCE_DIR):
        if filename.endswith(".json") and today_str not in filename:
            file_path = os.path.join(ATTENDANCE_DIR, filename)
            os.remove(file_path)

@frappe.whitelist()
def fetch_and_upload_attendance():
    if not os.path.exists(ATTENDANCE_DIR):
        os.makedirs(ATTENDANCE_DIR, exist_ok=True)
        
    response = {"success": [], "errors": []}
    devices = frappe.get_all("Biometric Device Settings", fields=["device_ip", "device_port", "name"])
    
    if not devices:
        response["errors"].append("No devices found.")
        return response
    
    for device in devices:
        
        ip = device["device_ip"]
        port = device.get("device_port", 4370)
        file_path = get_attendance_file_path(ip)

        try:
            if os.path.exists(file_path):
                frappe.logger().info(f"[{ip}] JSON exists. Creating check-ins.")
                create_frappe_attendance(ip)

                logs = fetch_attendance_from_device(ip, port)
                if logs:
                    new_records = process_attendance_logs(ip, logs)
                    if new_records:
                        frappe.logger().info(f"[{ip}] New records added. Creating check-ins.")
                        create_frappe_attendance(ip)
                    response["success"].append(f"Updated check-ins for {ip}")
                else:
                    response["errors"].append(f"No new logs fetched from {ip}")
            else:
                frappe.logger().info(f"[{ip}] No JSON. Fetching logs from device.")
                logs = fetch_attendance_from_device(ip, port)
                if logs:
                    process_attendance_logs(ip, logs)
                    create_frappe_attendance(ip)
                    response["success"].append(f"Created check-ins from new device data {ip}")
                else:
                    response["errors"].append(f"No logs fetched from device {ip}")
        except Exception as e:
            frappe.log_error(f"Error processing device {ip}: {str(e)}", "Biometric Sync Error")
            response["errors"].append(f"Error processing device {ip}: {str(e)}")

    cleanup_old_attendance_logs()
    return response


################################################################

def process_attendance():
    employees = frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "default_shift"])
    for emp in employees:
        process_employee_attendance(emp["name"], emp["default_shift"])

def process_employee_attendance(employee, shift):
    checkins = frappe.get_all(
        "Employee Checkin",
        filters={"employee": employee},
        fields=["name", "employee", "time", "log_type"],
        order_by="time ASC"
    )

    today_date = get_datetime(today()).date()
    if not checkins:
        check_missing_days(employee, shift, today_date)
        return

    dates_with_checkins = sorted(set(get_datetime(ci["time"]).date() for ci in checkins))
    first_date = dates_with_checkins[0]
    date_range = [add_days(first_date, i) for i in range((today_date - first_date).days + 1)]

    for date in date_range:
        daily_checkins = [ci for ci in checkins if get_datetime(ci["time"]).date() == date]
        if daily_checkins:
            existing = frappe.db.exists("Attendance", {"employee": employee, "attendance_date": date})
            attendance = frappe.get_doc("Attendance", {"employee": employee, "attendance_date": date}) if existing else None
            first_checkin = daily_checkins[0]
            last_checkout = daily_checkins[-1]

            if attendance:
                update_attendance(attendance.name, employee, date, shift, first_checkin, last_checkout)
            else:
                if is_holiday(employee, date):
                    handle_holiday_attendance(employee, date, shift, daily_checkins)
                else:
                    handle_non_holiday_attendance(employee, date, shift, daily_checkins)
        else:
            mark_absent_if_no_checkin_leave_holiday(employee, date, shift)

def check_missing_days(employee, shift, today_date):
    for i in range(7):
        date = add_days(today_date, -i)
        mark_absent_if_no_checkin_leave_holiday(employee, date, shift)

def mark_absent_if_no_checkin_leave_holiday(employee, date, shift):
    leave_status, leave_type, leave_application = get_leave_status(employee, date)
    is_holiday_flag = is_holiday(employee, date)
    has_checkin = frappe.db.exists("Employee Checkin", {"employee": employee, "time": ["between", [f"{date} 00:00:00", f"{date} 23:59:59"]]})
    has_attendance = frappe.db.exists("Attendance", {"employee": employee, "attendance_date": date})

    if not has_checkin and not is_holiday_flag and not has_attendance:
        status = leave_status or "Absent"
        attendance = frappe.get_doc({
            "doctype": "Attendance",
            "employee": employee,
            "attendance_date": date,
            "shift": shift,
            "status": status,
            "leave_type": leave_type,
            "leave_application": leave_application,
            # "half_day_status": "Absent" if leave_status == "Half Day" else "",
        })
        attendance.insert(ignore_permissions=True)
        frappe.db.commit()

def handle_holiday_attendance(employee, date, shift, checkins):
    first = checkins[0]
    last = checkins[-1]
    hours = calculate_working_hours(first, last)
    status = "Half Day" if hours < 4 else "Present"
    create_attendance(employee, date, shift, first, last, status)

def handle_non_holiday_attendance(employee, date, shift, checkins):
    leave_status, leave_type, leave_application = get_leave_status(employee, date)
    first = checkins[0] if checkins else None
    last = checkins[-1] if checkins else None
    hours = calculate_working_hours(first, last)

    if not checkins:
        status = leave_status or "Absent"
    else:
        if leave_status == "On Leave":
            status = "On Leave"
        elif leave_status == "Half Day" or hours < 4:
            status = "Half Day"
        else:
            status = "Present"

    create_attendance(
        employee, date, shift, first, last, status,
        working_hours=hours, leave_type=leave_type,
        leave_application=leave_application,
        # half_day_status="Absent" if leave_status == "Half Day" else ""
    )

def create_attendance(employee, date, shift, first, last, status, working_hours=0, leave_type=None, leave_application=None):
    if not first or not last:
        return

    emp_doc = frappe.get_doc("Employee", employee)
    attendance = frappe.get_doc({
        "doctype": "Attendance",
        "employee": employee,
        "employee_name": emp_doc.employee_name,
        "attendance_date": date,
        "company": emp_doc.company,
        "department": emp_doc.department,
        "shift": shift,
        "status": status,
        "leave_type": leave_type,
        "leave_application": leave_application,
        "working_hours": working_hours,
        "in_time": first["time"],
        "out_time": last["time"],
        # "half_day_status": half_day_status,
        "late_entry": False,
        "early_exit": False
    })

    attendance.insert(ignore_permissions=True)
    frappe.db.set_value("Employee Checkin", first["name"], {"attendance": attendance.name, "log_type": "IN"})
    if first["name"] != last["name"]:
        frappe.db.set_value("Employee Checkin", last["name"], {"attendance": attendance.name, "log_type": "OUT"})
    frappe.db.commit()

def update_attendance(attendance_name, employee, date, shift, first, last):
    working_hours = calculate_working_hours(first, last)
    leave_status, leave_type, leave_application = get_leave_status(employee, date)

    status = "Present" if working_hours >= 4 else "Half Day"
    if leave_status == "On Leave":
        status = "On Leave"
    elif leave_status == "Half Day" or working_hours < 4:
        status = "Half Day"

    frappe.db.set_value("Attendance", attendance_name, {
        "in_time": first["time"],
        "out_time": last["time"],
        "working_hours": working_hours,
        "status": status,
        "leave_type": leave_type,
        "leave_application": leave_application,
        # "half_day_status": "Absent" if status == "Half Day" else "",
    })

    frappe.db.set_value("Employee Checkin", first["name"], {"attendance": attendance_name, "log_type": "IN"})
    if first["name"] != last["name"]:
        frappe.db.set_value("Employee Checkin", last["name"], {"attendance": attendance_name, "log_type": "OUT"})

    frappe.db.commit()

def get_leave_status(employee, date):
    leave = frappe.get_all("Leave Application", {
        "employee": employee,
        "from_date": ["<=", date],
        "to_date": [">=", date],
        "status": "Approved"
    }, ["name", "leave_type", "half_day"])

    if leave:
        is_half_day = leave[0]["half_day"]
        return ("Half Day" if is_half_day else "On Leave", leave[0]["leave_type"], leave[0]["name"])
    return (None, None, None)

def is_holiday(employee, date):
    holiday_list = frappe.get_value("Employee", employee, "holiday_list")
    return frappe.db.exists("Holiday", {"parent": holiday_list, "holiday_date": date}) if holiday_list else False

def calculate_working_hours(first, last):
    if not first or not last:
        return 0
    return time_diff_in_hours(get_datetime(last["time"]), get_datetime(first["time"]))

@frappe.whitelist()
def mark_attendance():
    process_attendance()
    return {"message": "Attendance marked successfully"}

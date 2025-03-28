# import frappe
# import requests
# from frappe.utils import cint, getdate, nowdate, add_days, today, get_datetime, time_diff_in_hours
# import json
# import os
# from zk import ZK

import frappe
import json
import os
from frappe.utils import getdate, nowdate, cint, add_days, today, get_datetime, time_diff_in_hours, add_to_date
from zk import ZK
from datetime import datetime, timedelta

# Punch Mapping
PUNCH_MAPPING = {
    0: "Check-In",
    1: "Check-Out",
    2: "Break-Out",
    3: "Break-In",
    4: "Overtime Start",
    5: "Overtime End"
}

# JSON File Management
ATTENDANCE_DIR = "attendance_logs"

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
    if not os.path.exists(ATTENDANCE_DIR):
        os.makedirs(ATTENDANCE_DIR)
    file_path = get_attendance_file_path(ip)
    with open(file_path, "w") as f:
        json.dump(attendance, f, indent=4)

# Fetch Attendance from Biometric Device
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

# Process Attendance Data
def process_attendance_logs(ip, logs):
    existing_data = load_attendance_data(ip)
    existing_records = {(entry['user_id'], entry['timestamp']) for entry in existing_data}
    new_records = []
    
    for log in logs:
        record = {
            "uid": log.uid,
            "user_id": log.user_id,
            "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "status": log.status,
            "punch": log.punch,
            "punch_type": PUNCH_MAPPING.get(log.punch, "Unknown")
        }
        if (log.user_id, log.timestamp.strftime("%Y-%m-%d %H:%M:%S")) not in existing_records:
            new_records.append(record)
    
    if new_records:
        existing_data.extend(new_records)
        save_attendance_data(ip, existing_data)
    return new_records

# Create Check-in/Check-out Records in Frappe
def create_frappe_attendance(ip):
    attendance_data = load_attendance_data(ip)
    for record in attendance_data:
        try:
            employee = frappe.get_value("Employee", {"attendance_device_id": record['user_id']}, "name")
            if employee:
                existing_checkin = frappe.get_all("Employee Checkin", 
                    filters={"employee": employee, "time": record['timestamp']}, 
                    fields=["name"])
                if not existing_checkin:
                    checkin_doc = frappe.get_doc({
                        "doctype": "Employee Checkin",
                        "employee": employee,
                        "time": record['timestamp'],
                        "log_type": "IN" if record['punch'] in [0, 4] else "OUT",
                        "device_id": record['user_id']
                    })
                    checkin_doc.insert()
                    frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"Error processing attendance for user {record['user_id']}: {str(e)}", "Biometric Sync Error")

# Cleanup Old Attendance Files
def cleanup_old_attendance_logs():
    cutoff_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    for filename in os.listdir(ATTENDANCE_DIR):
        if cutoff_date in filename:
            os.remove(os.path.join(ATTENDANCE_DIR, filename))

# Main Function
@frappe.whitelist()
def fetch_and_upload_attendance():
    response = {"success": [], "errors": []}
    devices = frappe.get_all("Biometric Device Settings", fields=["device_ip", "device_port","name"])
    
    for device in devices:
        ip, port = device["device_ip"], device.get("device_port", 4370)
        logs = fetch_attendance_from_device(ip, port)
        if logs:
            new_records = process_attendance_logs(ip, logs)
            if new_records:
                create_frappe_attendance(ip)
                response["success"].append(f"New attendance records processed for device")
        else:
            response["errors"].append(f"No new records fetched from device ")
    
    cleanup_old_attendance_logs()
    return response


########################################
# @frappe.whitelist()
# def fetch_and_upload_attendance():
#     response = {"success": [], "errors": []}
    
#     devices = frappe.get_all("Biometric Device Settings", fields=["device_ip", "device_port", "sync_from_date"])
    
#     for device in devices:
#         ip, port, sync_date = device["device_ip"], device.get("device_port", 4370), device["sync_from_date"]
#         try:
#             conn = ZK(ip, port=int(port), timeout=30, force_udp=False, ommit_ping=False).connect()
#             if conn:
#                 attendances = conn.get_attendance()
#                 for log in attendances:
#                     try:
#                         employee = frappe.get_value("Employee", {"attendance_device_id": log.user_id}, "name")
#                         if employee:
#                             existing_checkin = frappe.get_all("Employee Checkin", 
#                                 filters={"employee": employee, "time": log.timestamp}, 
#                                 fields=["name"])
#                             if not existing_checkin:
#                                 checkin_doc = frappe.get_doc({
#                                     "doctype": "Employee Checkin",
#                                     "employee": employee,
#                                     "time": log.timestamp,
#                                     "log_type": "IN" if log.punch in [0, 4] else "OUT",
#                                     "device_id": log.user_id
#                                 })
#                                 checkin_doc.insert()
#                                 frappe.db.commit()
                                
#                                 frappe.log(f"Attendance recorded for {employee} at {log.timestamp}")
#                             else:
#                                 frappe.log(f"Duplicate entry for {employee} at {log.timestamp}")
#                     except Exception as e:
#                         error_msg = f"Error processing log for user {log.user_id}: {str(e)}"
#                         frappe.log_error(error_msg, "Biometric Sync Error")
#                         response["errors"].append(error_msg)
#                 conn.disconnect()
#             else:
#                 error_msg = f"Failed to connect to device {ip}"
#                 frappe.log_error(error_msg, "Biometric Device Connection Error")
#                 response["errors"].append(error_msg)
#         except Exception as e:
#             error_msg = f"Error connecting to device {ip}: {str(e)}"
#             frappe.log_error(error_msg, "Biometric Device Connection Error")
#             response["errors"].append(error_msg)
#     if attendances:
#         response["success"].append(f"Attendance records fetched successfully ....")
#     return response

###########################################

# def calculate_final_working_hours(employee, date):
#     """Calculate final working hours from employee check-in records."""
    
#     start_datetime = get_datetime(date)  # Convert date to datetime
#     end_datetime = add_to_date(start_datetime, days=1, as_datetime=True)  # Get next day's midnight

#     # Fetch check-ins for the employee on the given date
#     checkins = frappe.get_all(
#         "Employee Checkin",
#         filters={"employee": employee, "time": [">=", start_datetime], "time": ["<", end_datetime]},
#         fields=["name", "time"],
#         order_by="time ASC"
#     )

#     if not checkins or len(checkins) < 2:
#         return 0  # Not enough records to calculate working hours
    
#     first_checkin = get_datetime(checkins[0]["time"])
#     last_checkout = get_datetime(checkins[-1]["time"])
    
#     total_working_hours = 0
#     total_break_time = 0

#     # Process check-in records (odd as IN, even as OUT)
#     for i in range(0, len(checkins) - 1, 2):  # Step by 2
#         in_time = get_datetime(checkins[i]["time"])
#         out_time = get_datetime(checkins[i + 1]["time"]) if i + 1 < len(checkins) else last_checkout

#         total_working_hours += time_diff_in_hours(out_time, in_time)

#         # Calculate break time (OUT to next IN)
#         if i + 2 < len(checkins):
#             next_in_time = get_datetime(checkins[i + 2]["time"])
#             total_break_time += time_diff_in_hours(next_in_time, out_time)

#     # Subtract break time from total working hours
#     final_working_hours = total_working_hours - total_break_time
#     return max(final_working_hours, 0) 

def process_attendance():
    """Fetch employee check-ins, determine attendance, and update records."""
    employees = frappe.get_all("Employee", fields=["name", "default_shift"])
    
    for emp in employees:
        process_employee_attendance(emp["name"], emp["default_shift"])

def process_employee_attendance(employee, shift):
    """Process check-ins, determine attendance status, check leaves, and calculate working hours."""
    checkins = frappe.get_all(
        "Employee Checkin",
        filters={"employee": employee},
        fields=["name", "employee", "time", "log_type"],
        order_by="time ASC"
    )

    if not checkins:
        mark_absent_or_leave(employee, today(), shift)
        return

    dates = sorted(set(get_datetime(ci["time"]).date() for ci in checkins))
    
    for date in dates:
        if is_holiday(employee, date):
            continue

        checkins_on_date = [ci for ci in checkins if get_datetime(ci["time"]).date() == date]
        if not checkins_on_date:
            mark_absent_or_leave(employee, date, shift)
            continue

        first_checkin = checkins_on_date[0]
        last_checkout = checkins_on_date[-1]

        shift_end_time = frappe.get_value("Shift Type", shift, "end_time")
        if isinstance(shift_end_time, str):
            shift_end_time = datetime.datetime.strptime(shift_end_time, "%H:%M:%S").time()

        existing_attendance = frappe.get_value(
            "Attendance", {"employee": employee, "attendance_date": date}, "name"
        )

        if date == today():
            if existing_attendance:
                update_attendance(existing_attendance, employee, date, shift, first_checkin, last_checkout)
            else:
                create_attendance(employee, date, shift, first_checkin, last_checkout)
        else:
            create_attendance(employee, date, shift, first_checkin, last_checkout)

        # Ensure last checkout is marked OUT only after shift end time or if attendance is submitted
        if last_checkout and (date != today() or get_datetime().time() >= shift_end_time):
            frappe.db.set_value("Employee Checkin", first_checkin["name"], "log_type", "IN")
            frappe.db.set_value("Employee Checkin", last_checkout["name"], "log_type", "OUT")
            frappe.db.set_value("Employee Checkin", first_checkin["name"], "attendance", existing_attendance or attendance.name)
            frappe.db.set_value("Employee Checkin", last_checkout["name"], "attendance", existing_attendance or attendance.name)



def create_attendance(employee, date, shift, first_checkin, last_checkout):
    """Create or update attendance entry considering breaks, leaves, and working hours."""
    shift_end_time = frappe.get_value("Shift Type", shift, "end_time")
    if isinstance(shift_end_time, str):
        shift_end_time = datetime.datetime.strptime(shift_end_time, "%H:%M:%S").time()

    working_hours = calculate_working_hours(first_checkin, last_checkout)
    leave_status, leave_type = get_leave_status(employee, date)

    status = "Present"
    if leave_status == "On Leave":
        status = "On Leave"
    elif leave_status == "Half Day" or working_hours < 4:
        status = "Half Day"

    existing_attendance = frappe.get_value("Attendance", 
        {"employee": employee, "attendance_date": date}, "name")
    
    if existing_attendance:
        frappe.db.set_value("Attendance", existing_attendance, {
            "working_hours": working_hours,
            "status": status,
            "leave_type": leave_type if leave_status in ["On Leave", "Half Day"] else "",
            "out_time": last_checkout["time"] if last_checkout else None,
            "checkout": last_checkout["name"] if last_checkout else ""
        })
        frappe.db.commit()
    else:
        attendance = frappe.get_doc({
            "doctype": "Attendance",
            "employee": employee,
            "attendance_date": date,
            "shift": shift,
            "status": status,
            "checkin": first_checkin["name"],
            "checkout": last_checkout["name"] if last_checkout else "",
            "leave_type": leave_type if leave_status in ["On Leave", "Half Day"] else "",
            "working_hours": working_hours,
            "in_time": first_checkin["time"],
            "out_time": last_checkout["time"] if last_checkout else None
        })
        attendance.insert(ignore_permissions=True)
        frappe.db.commit()

    # Only mark OUT if shift end time is reached
    if last_checkout and (date != today() or get_datetime().time() >= shift_end_time):
        frappe.db.set_value("Employee Checkin", first_checkin["name"], "log_type", "IN")
        frappe.db.set_value("Employee Checkin", last_checkout["name"], "log_type", "OUT")
        frappe.db.set_value("Employee Checkin", first_checkin["name"], "attendance", attendance.name)
        frappe.db.set_value("Employee Checkin", last_checkout["name"], "attendance", attendance.name)


def update_attendance(attendance_name, employee, date, shift, first_checkin, last_checkout):
    """Update an existing attendance record with out time, working hours, and link to Employee Checkin."""
    working_hours = calculate_working_hours(first_checkin, last_checkout)
    
    frappe.db.set_value("Attendance", attendance_name, {
        "out_time": last_checkout["time"] if last_checkout else None,
        "working_hours": working_hours,
    })

    # Link check-ins to the attendance record
    frappe.db.set_value("Employee Checkin", first_checkin["name"], "attendance", attendance_name)
    if last_checkout:
        frappe.db.set_value("Employee Checkin", last_checkout["name"], "attendance", attendance_name)
    
    frappe.db.commit()



def mark_absent_or_leave(employee, date, shift):
    """Mark employee absent or on leave if applicable."""
    leave_status, leave_type = get_leave_status(employee, date)
    status = leave_status if leave_status else "Absent"

    if not frappe.db.exists("Attendance", {"employee": employee, "attendance_date": date}):
        attendance = frappe.get_doc({
            "doctype": "Attendance",
            "employee": employee,
            "attendance_date": date,
            "shift": shift,
            "status": status,
            "leave_type": leave_type if leave_status in ["On Leave", "Half Day"] else ""
        })
        attendance.insert(ignore_permissions=True)
        frappe.db.commit()

def get_leave_status(employee, date):
    """Check if the employee is on leave for the given date."""
    leave = frappe.get_all("Leave Application",
        filters={"employee": employee, "from_date": ["<=", date], "to_date": [">=", date], "status": "Approved"},
        fields=["leave_type", "half_day"]
    )

    if leave:
        return ("Half Day", leave[0]["leave_type"]) if leave[0]["half_day"] else ("On Leave", leave[0]["leave_type"])
    
    return ("Absent", "")

def is_holiday(employee, date):
    """Check if the date is a holiday for the employee."""
    holiday_list = frappe.get_value("Employee", employee, "holiday_list")
    return frappe.db.exists("Holiday", {"parent": holiday_list, "holiday_date": date}) if holiday_list else False

def calculate_working_hours(first_checkin, last_checkout):
    """Calculate working hours excluding breaks."""
    if not first_checkin or not last_checkout:
        return 0
    return time_diff_in_hours(get_datetime(last_checkout["time"]), get_datetime(first_checkin["time"]))

def mark_today_attendance():
    """Mark today's attendance after shift end time."""
    employees = frappe.get_all("Employee", fields=["name", "default_shift"])
    for emp in employees:
        shift_end_time = frappe.get_value("Shift Type", emp["default_shift"], "end_time")
        if isinstance(shift_end_time, str):
            shift_end_time = datetime.datetime.strptime(shift_end_time, "%H:%M:%S").time()
        if shift_end_time and get_datetime().time() >= shift_end_time:
            process_employee_attendance(emp["name"], emp["default_shift"])

@frappe.whitelist(allow_guest=True)
def mark_attendance():
    """API to process attendance."""
    process_attendance()
    return {"message": "Attendance processed successfully"}
import frappe
import requests
from frappe.utils import cint, getdate, nowdate, add_days, today, get_datetime, time_diff_in_hours

from zk import ZK

@frappe.whitelist()
def fetch_and_upload_attendance():
    response = {"success": [], "errors": []}
    
    devices = frappe.get_all("Biometric Device Settings", fields=["device_ip", "device_port", "sync_from_date"])
    
    for device in devices:
        ip, port, sync_date = device["device_ip"], device.get("device_port", 4370), device["sync_from_date"]
        try:
            conn = ZK(ip, port=int(port), timeout=30, force_udp=False, ommit_ping=False).connect()
            if conn:
                attendances = conn.get_attendance()
                for log in attendances:
                    try:
                        employee = frappe.get_value("Employee", {"attendance_device_id": log.user_id}, "name")
                        if employee:
                            existing_checkin = frappe.get_all("Employee Checkin", 
                                filters={"employee": employee, "time": log.timestamp}, 
                                fields=["name"])
                            if not existing_checkin:
                                checkin_doc = frappe.get_doc({
                                    "doctype": "Employee Checkin",
                                    "employee": employee,
                                    "time": log.timestamp,
                                    "log_type": "IN" if log.punch in [0, 4] else "OUT",
                                    "device_id": log.user_id
                                })
                                checkin_doc.insert()
                                frappe.db.commit()
                                
                                frappe.log(f"Attendance recorded for {employee} at {log.timestamp}")
                            else:
                                frappe.log(f"Duplicate entry for {employee} at {log.timestamp}")
                    except Exception as e:
                        error_msg = f"Error processing log for user {log.user_id}: {str(e)}"
                        frappe.log_error(error_msg, "Biometric Sync Error")
                        response["errors"].append(error_msg)
                conn.disconnect()
            else:
                error_msg = f"Failed to connect to device {ip}"
                frappe.log_error(error_msg, "Biometric Device Connection Error")
                response["errors"].append(error_msg)
        except Exception as e:
            error_msg = f"Error connecting to device {ip}: {str(e)}"
            frappe.log_error(error_msg, "Biometric Device Connection Error")
            response["errors"].append(error_msg)
    if attendances:
        response["success"].append(f"Attendance records fetched successfully ....")
    return response

###########################################


def process_attendance():
    """Fetch employee check-ins, determine attendance, and update records."""
    employees = frappe.get_all("Employee", fields=["name", "default_shift"])
    
    for emp in employees:
        process_employee_attendance(emp.name, emp.default_shift)

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
        # Skip holidays
        if is_holiday(employee, date):
            continue

        checkins_on_date = [ci for ci in checkins if get_datetime(ci["time"]).date() == date]

        if not checkins_on_date:
            mark_absent_or_leave(employee, date, shift)
            continue
        
        first_checkin = checkins_on_date[0]
        last_checkout = checkins_on_date[-1] if checkins_on_date[-1]["log_type"] == "OUT" else None

        if not frappe.db.exists("Attendance", {"employee": employee, "attendance_date": date}):
            create_attendance(employee, date, shift, first_checkin, last_checkout)

def create_attendance(employee, date, shift, first_checkin, last_checkout):
    """Create attendance entry considering breaks and leaves."""
    shift_details = frappe.get_value("Shift Type", shift, ["end_time"])
    
    # Calculate working hours with breaks
    working_hours = calculate_working_hours(first_checkin, last_checkout)
    
    # Check leave application
    leave_status, leave_type = get_leave_status(employee, date)
    
    if leave_status == "On Leave":
        status = "On Leave"
    elif leave_status == "Half Day":
        status = "Half Day"
    else:
        status = "Present" if working_hours >= 4 else "Half Day"

    # Create Attendance record
    attendance = frappe.get_doc({
        "doctype": "Attendance",
        "employee": employee,
        "attendance_date": date,
        "shift": shift,
        "status": status,
        "checkin": first_checkin["name"],
        "checkout": last_checkout["name"] if last_checkout else "",
        "log_type": "IN" if last_checkout else "ABSENT",
        "leave_type": leave_type if leave_status in ["On Leave", "Half Day"] else "",
        "working_hours": working_hours
    })
    attendance.insert(ignore_permissions=True)
    frappe.db.commit()

    # Update Check-in Log Type
    frappe.db.set_value("Employee Checkin", first_checkin["name"], "log_type", "IN")
    if last_checkout:
        frappe.db.set_value("Employee Checkin", last_checkout["name"], "log_type", "OUT")

def mark_absent_or_leave(employee, date, shift):
    """Mark employee absent or on leave if applicable."""
    leave_status, leave_type = get_leave_status(employee, date)

    if leave_status == "On Leave":
        status = "On Leave"
    elif leave_status == "Half Day":
        status = "Half Day"
    else:
        status = "Absent"

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
    
    return ("", "")

def is_holiday(employee, date):
    """Check if the date is a holiday for the employee."""
    holiday_list = frappe.get_value("Employee", employee, "holiday_list")
    if holiday_list:
        return frappe.db.exists("Holiday", {"parent": holiday_list, "holiday_date": date})
    return False

def calculate_working_hours(first_checkin, last_checkout):
    """Calculate working hours excluding breaks."""
    if not last_checkout:
        return 0
    
    total_hours = time_diff_in_hours(get_datetime(last_checkout["time"]), get_datetime(first_checkin["time"]))

    # Subtract breaks: 30 min lunch, 15 min morning tea, 15 min evening tea
    # break_time = 30 + 15 + 15
    working_hours = total_hours

    return working_hours

def mark_today_attendance():
    """Mark today's attendance after shift end time."""
    employees = frappe.get_all("Employee", fields=["name", "default_shift"])

    for emp in employees:
        shift_end_time = frappe.get_value("Shift Type", emp.default_shift, "end_time")
        if shift_end_time and get_datetime().time() >= shift_end_time:
            process_employee_attendance(emp.name, emp.default_shift)


############################
@frappe.whitelist(allow_guest=True)
def mark_attendance():
    process_attendance()
    return {"status": "success", "message": "Attendance processed successfully"}





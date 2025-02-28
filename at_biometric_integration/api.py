import frappe
import json
import datetime
from zk import ZK

def get_device_and_employee_details():
    """Fetch device details and employee details from ERPNext."""
    devices = frappe.get_all("Biometric Device Settings", fields=["device_name", "device_ip", "port", "sync_from_date"])
    employees = frappe.get_all("Employee", fields=["name", "attendance_device_id", "default_shift"])
    return devices, employees

def get_punch_direction(punch):
    """Determine if the punch is IN or OUT."""
    if punch in [0, 4]:
        return "IN"
    elif punch in [1, 5]:
        return "OUT"
    return None

def get_biometric_attendance(ip, port=4370, timeout=30):
    """Fetch attendance logs from the biometric device."""
    zk = ZK(ip, port=port, timeout=timeout)
    conn = None
    attendances = []
    try:
        conn = zk.connect()
        conn.disable_device()
        attendances = conn.get_attendance()
        conn.enable_device()
    except Exception as e:
        frappe.log_error(f"Error fetching attendance from device {ip}: {str(e)}", "Biometric Fetch Error")
    finally:
        if conn:
            conn.disconnect()
    return [att.__dict__ for att in attendances]

def upload_attendance_to_erpnext(attendance_logs, employees):
    """Upload biometric attendance data to ERPNext Employee Check-In."""
    for log in attendance_logs:
        user_id = log["user_id"]
        punch = get_punch_direction(log["punch"])
        timestamp = log["timestamp"]
        
        if not punch:
            continue
        
        employee = next((emp for emp in employees if emp["attendance_device_id"] == user_id), None)
        if not employee:
            frappe.log_error(f"No employee found for device ID {user_id}", "Employee Match Error")
            continue
        
        try:
            checkin = frappe.get_doc({
                "doctype": "Employee Checkin",
                "employee": employee["name"],
                "time": timestamp,
                "log_type": punch,
                "device_id":employee["attendance_device_id"] ,
                "shift": employee["default_shift"],
            })
            checkin.insert(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"Error inserting Employee Checkin: {str(e)}", "Employee Checkin Error")

@frappe.whitelist()
def sync_biometric_attendance():
    """Main function to fetch and upload attendance data."""
    devices, employees = get_device_and_employee_details()
    for device in devices:
        attendance_logs = get_biometric_attendance(device["device_ip"], device["port"])
        upload_attendance_to_erpnext(attendance_logs, employees)
        frappe.logger().info(f"Attendance synced for device {device['device_ip']}")


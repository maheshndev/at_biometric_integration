import frappe
import requests
import datetime
from zk import ZK

@frappe.whitelist()
def fetch_and_upload_attendance():
    devices = frappe.get_all("Biometric Device Settings", fields=["device_ip", "device_port", "sync_from_date"])
    for device in devices:
        ip, port, sync_date = device["device_ip"], device["device_port"], device["sync_from_date"]
        try:
            conn = ZK(ip, port=int(port), timeout=30).connect()
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
                                    "device_id": ip
                                })
                                checkin_doc.insert()
                                frappe.db.commit()
                    except Exception as e:
                        frappe.log_error(f"Error processing log for user {log.user_id}: {str(e)}", "Biometric Sync Error")
                conn.disconnect()
        except Exception as e:
            frappe.log_error(f"Error connecting to device {ip}: {str(e)}", "Biometric Device Connection Error")     
    return "Attendance Synced Successfully"


@frappe.whitelist()
def test_new():
    return {"message": "Hello from test_new!"}



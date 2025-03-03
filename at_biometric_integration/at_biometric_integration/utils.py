import frappe
import requests
import datetime
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
                                # response["success"].append(f"Attendance recorded for {employee} at {log.timestamp}")
                            # else:
                                # response["errors"].append(f"Duplicate entry for {employee} at {log.timestamp}")
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
    
    return response


@frappe.whitelist()
def test_new():
    return {"message": "Hello from test_new!"}



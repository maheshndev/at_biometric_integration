import frappe
from .biometric_sync import fetch_attendance_from_device, process_attendance_logs
from .checkin_processing import create_frappe_attendance_multi
from .attendance_processing import process_attendance_realtime, auto_submit_due_attendances
from .cleanup import cleanup_old_attendance_logs

@frappe.whitelist()
def fetch_and_upload_attendance():
    """Scheduler: Fetch logs from all devices and update check-ins and attempt auto-submission."""
    devices = frappe.get_all("Biometric Device Settings", ["device_ip", "device_port"])
    if not devices:
        frappe.log_error("No biometric devices found", "Fetch Attendance Scheduler")
        return

    created_total = []
    for device in devices:
        ip, port = device["device_ip"], device.get("device_port", 4370)
        logs = fetch_attendance_from_device(ip, port)
        if logs:
            process_attendance_logs(ip, logs)
            created = create_frappe_attendance_multi([device])  # should return created attendance names if possible
            if created:
                created_total.extend(created)

    cleanup_old_attendance_logs()

    # Recreate/refresh attendance based on checkins and commit
    created_or_updated = process_attendance_realtime()
    frappe.db.commit()

    # Auto-submit new/updated attendances that are eligible now
    try:
        # try to auto-submit those just created or updated
        if created_or_updated:
            from .attendance_processing import auto_submit_new_attendances
            auto_submit_new_attendances(created_or_updated)
    except Exception as e:
        frappe.log_error(f"Auto-submit after scheduler failed: {e}", "Fetch Attendance Scheduler")

    # Additionally, process any attendances that are due (shift_end+4h or reg window expired)
    try:
        submitted_list = auto_submit_due_attendances()
        if submitted_list:
            frappe.logger().info(f"Scheduler auto-submitted attendance: {submitted_list}")
    except Exception as e:
        frappe.log_error(f"Auto-submit due attendances failed: {e}", "Fetch Attendance Scheduler")

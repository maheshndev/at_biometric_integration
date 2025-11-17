import frappe
from at_biometric_integration.utils import biometric_sync, checkin_processing, attendance_processing, cleanup

@frappe.whitelist()
def fetch_and_upload_attendance():
    """
    Controller - called manually via API or scheduler.
    - fetch logs
    - process logs into checkins
    - create Attendance records (via your existing helper)
    - try auto-submitting newly created attendance records
    - run cleanup
    """
    response = {"success": [], "errors": []}
    devices = frappe.get_all("Biometric Device Settings", fields=["device_ip", "device_port"])

    for device in devices:
        ip, port = device.device_ip, device.device_port or 4370
        logs = biometric_sync.fetch_attendance_from_device(ip, port)
        if logs:
            new_records = biometric_sync.process_attendance_logs(ip, logs)
            if new_records:
                # create_frappe_attendance_multi should return list of created attendance names (adapt if it doesn't)
                created = checkin_processing.create_frappe_attendance_multi([device])
                # commit before auto-submit checks
                frappe.db.commit()
                # auto submit those created (if eligible)
                try:
                    submitted = attendance_processing.auto_submit_new_attendances(created)
                    response["success"].append(f"Synced {len(new_records)} records from {ip}. Auto-submitted: {len(submitted)}")
                except Exception as e:
                    frappe.log_error(f"Auto-submit new attendances error: {e}", "Attendance API")
                    response["success"].append(f"Synced {len(new_records)} records from {ip}. Auto-submit failed.")
            else:
                response["success"].append(f"No new logs for {ip}")
        else:
            response["errors"].append(f"Failed to fetch from {ip}")

    cleanup.cleanup_old_attendance_logs()
    return response


@frappe.whitelist()
def mark_attendance():
    """Manual button trigger for marking attendance and running auto-submit pass."""
    try:
        created = attendance_processing.process_attendance_realtime()
        # commit the newly created/updated attendance records
        frappe.db.commit()

        # Try auto-submitting newly created attendances
        try:
            attendance_processing.auto_submit_new_attendances(created)
        except Exception as e:
            frappe.log_error(f"Auto-submit after manual mark failed: {e}", "Mark Attendance")

        return {"message": "Attendance marked successfully"}
    except Exception as e:
        frappe.log_error(f"Error marking attendance: {e}", "Mark Attendance")
        return {"message": f"Error: {e}"}

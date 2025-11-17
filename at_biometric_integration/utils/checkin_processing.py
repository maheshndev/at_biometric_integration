import frappe
from frappe.utils import get_datetime

def create_frappe_attendance_multi(devices):
    """Create Employee Checkins from stored JSON logs for each device."""
    from .biometric_sync import load_attendance_data

    all_logs = []
    for device in devices:
        ip = device["device_ip"]
        logs = load_attendance_data(ip)
        for record in logs:
            record["device_ip"] = ip
        all_logs.extend(logs)

    if not all_logs:
        return

    user_ids = list(set([r["user_id"] for r in all_logs]))
    employees = frappe.get_all(
        "Employee", filters={"attendance_device_id": ["in", user_ids], "status": "Active"},
        fields=["name", "attendance_device_id"]
    )
    emp_map = {e.attendance_device_id: e.name for e in employees}

    timestamps = [r["timestamp"] for r in all_logs]
    existing = {
        (c.employee, c.time.strftime("%Y-%m-%d %H:%M:%S"))
        for c in frappe.get_all("Employee Checkin",
            filters={"time": ["in", timestamps]}, fields=["employee", "time"]
        )
    }

    for r in all_logs:
        emp = emp_map.get(r["user_id"])
        if not emp or (emp, r["timestamp"]) in existing:
            continue

        log_type = "IN" if r["punch"] in [0, 4] else "OUT"
        try:
            frappe.get_doc({
                "doctype": "Employee Checkin",
                "employee": emp,
                "time": r["timestamp"],
                "log_type": log_type,
                "device_id": r["user_id"],
                "device_ip": r.get("device_ip"),
                "latitude": "0.0",
                "longitude": "0.0",
            }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"Failed inserting checkin for {emp}: {e}", "Checkin Creation Error")

    frappe.db.commit()

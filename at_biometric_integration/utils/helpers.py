import frappe
from frappe.utils import get_datetime, time_diff_in_hours

def get_leave_status(employee, date):
    leaves = frappe.get_all("Leave Application",
        filters={"employee": employee, "from_date": ["<=", date], "to_date": [">=", date], "status": "Approved"},
        fields=["name", "leave_type", "half_day"]
    )
    if leaves:
        half = leaves[0].half_day
        return ("Half Day" if half else "On Leave", leaves[0].leave_type, leaves[0].name)
    return (None, None, None)


def is_holiday(employee, date):
    holiday_list = frappe.get_value("Employee", employee, "holiday_list")
    return frappe.db.exists("Holiday", {"parent": holiday_list, "holiday_date": date}) if holiday_list else False


def calculate_working_hours(first, last):
    try:
        return time_diff_in_hours(get_datetime(last.time), get_datetime(first.time))
    except Exception as e:
        frappe.log_error(f"Working hours calc failed: {e}", "Working Hours Error")
        return 0

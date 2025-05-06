import frappe
from frappe.utils import nowdate

@frappe.whitelist()
def check_missing_checkins():
    """
    Log employees with no check-ins today.
    """
    employees = frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "employee_name"])

    for emp in employees:
        checkins = frappe.get_all("Employee Checkin", filters={
            "employee": emp.name,
            "log_date": nowdate()
        })

        if not checkins:
            frappe.log_error(f"Missing check-in for {emp.employee_name} on {nowdate()}", "Attendance Regularization")

from frappe.model.document import Document
import frappe
from datetime import datetime, time, timedelta

class AttendanceRegularization(Document):
    def on_submit(self):
        if self.status != "Approved":
            return

        # Fetch company and shift from Employee
        employee_details = frappe.get_value(
            "Employee",
            self.employee,
            ["company", "default_shift"],
            as_dict=True
        )

        if not employee_details:
            frappe.throw(f"Employee {self.employee} not found.")

        from datetime import datetime, time, timedelta

        def combine_date_time(date, time_obj):
            if isinstance(time_obj, timedelta):
                # Convert timedelta to time
                return datetime.combine(date, (datetime.min + time_obj).time())
            elif isinstance(time_obj, time):
                return datetime.combine(date, time_obj)
            elif isinstance(time_obj, datetime):
                return time_obj
            else:
                frappe.throw("Invalid time format for in_time or out_time.")


        # Create Employee Checkin for IN time
        if self.in_time:
            in_time_dt = combine_date_time(self.date, self.in_time)
            frappe.get_doc({
                "doctype": "Employee Checkin",
                "employee": self.employee,
                "time": in_time_dt,
                "log_type": "IN",
                "company": employee_details.company
            }).insert(ignore_permissions=True)

        # Create Employee Checkin for OUT time
        if self.out_time:
            out_time_dt = combine_date_time(self.date, self.out_time)
            frappe.get_doc({
                "doctype": "Employee Checkin",
                "employee": self.employee,
                "time": out_time_dt,
                "log_type": "OUT",
                "company": employee_details.company
            }).insert(ignore_permissions=True)

        # Check if attendance already exists to prevent duplicates
        existing_attendance = frappe.db.exists("Attendance", {
            "employee": self.employee,
            "attendance_date": self.date
        })

        if not existing_attendance:
            frappe.get_doc({
                "doctype": "Attendance",
                "employee": self.employee,
                "employee_name": self.employee_name,
                "attendance_date": self.date,
                "status": self.attendance_status,
                "company": employee_details.company,
                "shift": employee_details.default_shift
            }).insert(ignore_permissions=True)

from frappe.model.document import Document
import frappe
from datetime import datetime, time, timedelta

class AttendanceRegularization(Document):
    def on_submit(self):
        if self.status != "Approved":
            frappe.throw("Only approved regularization requests can be processed.")

        # Fetch company and shift from Employee
        employee_details = frappe.get_value(
            "Employee",
            self.employee,
            ["company", "default_shift"],
            as_dict=True
        )

        if not employee_details:
            frappe.throw(f"Employee {self.employee} not found.")

        def combine_date_time(date, time_obj):
            """
            Combine date with time or timedelta to form a datetime object.
            Handles time, timedelta, and datetime.
            """
            if isinstance(time_obj, timedelta):
                return datetime.combine(date, (datetime.min + time_obj).time())
            elif isinstance(time_obj, time):
                return datetime.combine(date, time_obj)
            elif isinstance(time_obj, datetime):
                return time_obj
            else:
                frappe.throw("Invalid time format for in_time or out_time.")

        # Create or update Employee Checkin for IN time
        if self.in_time:
            in_time_dt = combine_date_time(self.date, self.in_time)
            self.create_or_update_checkin(self.employee, in_time_dt, "IN", employee_details.company)

        # Create or update Employee Checkin for OUT time
        if self.out_time:
            out_time_dt = combine_date_time(self.date, self.out_time)
            self.create_or_update_checkin(self.employee, out_time_dt, "OUT", employee_details.company)

        # Create or update Attendance record
        self.create_or_update_attendance(employee_details)

    def create_or_update_checkin(self, employee, time, log_type, company):
        """
        Create or update Employee Checkin record.
        """
        existing_checkin = frappe.get_all(
            "Employee Checkin",
            filters={
                "employee": employee,
                "time": time,
                "log_type": log_type
            },
            limit=1
        )

        if existing_checkin:
            frappe.db.set_value("Employee Checkin", existing_checkin[0].name, {
                "time": time
            })
        else:
            frappe.get_doc({
                "doctype": "Employee Checkin",
                "employee": employee,
                "time": time,
                "log_type": log_type,
                "company": company
            }).insert(ignore_permissions=True)

    def create_or_update_attendance(self, employee_details):
        """
        Create or update Attendance record.
        """
        existing_attendance = frappe.db.get_value(
            "Attendance",
            {"employee": self.employee, "attendance_date": self.date},
            "name"
        )

        attendance_data = {
            "employee": self.employee,
            "employee_name": self.employee_name,
            "attendance_date": self.date,
            "status": self.attendance_status,
            "company": employee_details.company,
            "shift": employee_details.default_shift
        }

        if existing_attendance:
            frappe.db.set_value("Attendance", existing_attendance, attendance_data)
        else:
            frappe.get_doc({
                "doctype": "Attendance",
                **attendance_data
            }).insert(ignore_permissions=True)

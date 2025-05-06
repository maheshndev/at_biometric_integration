from frappe.model.document import Document
from frappe.utils import nowdate
from frappe import db, throw, _

class AttendanceRegularization(Document):
    def validate(self):
        # Fetch employee check-ins for the given employee and date
        checkins = db.get_all(
            "Employee Checkin",
            filters={
                "employee": self.employee,
                "date": self.attendance_date
            },
            fields=["time", "log_type"]
        )

        if not checkins:
            throw("No check-ins found for the given employee and date.")

        # Determine the in and out times
        in_time = None
        out_time = None
        for checkin in checkins:
            if checkin["log_type"] == "IN" and (in_time is None or checkin["time"] < in_time):
                in_time = checkin["time"]
            elif checkin["log_type"] == "OUT" and (out_time is None or checkin["time"] > out_time):
                out_time = checkin["time"]

        if not in_time or not out_time:
            throw("Incomplete check-in data for the given employee and date.")

        # Calculate working hours
        working_hours = (out_time - in_time).total_seconds() / 3600

        # Validate against attendance records
        attendance = db.get_value(
            "Attendance",
            filters={
                "employee": self.employee,
                "attendance_date": self.attendance_date
            },
            fieldname=["status"]
        )

        if attendance == "Present" and working_hours < 8:
            throw("Working hours are less than the required minimum for a full day.")
        elif attendance == "Absent" and working_hours >= 8:
            self.status = "Approved"
        else:
            throw("Attendance regularization cannot be processed for the given data.")

    def before_submit(self):
        # Ensure workflow_state is "Approved"
        if self.workflow_state != "Approved":
            throw(_("Attendance Regularization can only be submitted when the workflow state is 'Approved'."))

        # Fetch employee check-ins for the given employee and date
        checkins = db.get_all(
            "Employee Checkin",
            filters={
                "employee": self.employee,
                "log_date": self.date
            },
            fields=["time", "log_type"]
        )

        if not checkins:
            throw(_("No check-ins found for the given employee and date."))

        # Determine the in and out times
        in_time = None
        out_time = None
        for checkin in checkins:
            if checkin["log_type"] == "IN" and (in_time is None or checkin["time"] < in_time):
                in_time = checkin["time"]
            elif checkin["log_type"] == "OUT" and (out_time is None or checkin["time"] > out_time):
                out_time = checkin["time"]

        if not in_time or not out_time:
            throw(_("Incomplete check-in data for the given employee and date."))

        # Create or update the Attendance record
        attendance = db.get_value(
            "Attendance",
            filters={
                "employee": self.employee,
                "attendance_date": self.date
            },
            fieldname="name"
        )

        if attendance:
            # Update existing attendance
            attendance_doc = frappe.get_doc("Attendance", attendance)
            attendance_doc.in_time = in_time
            attendance_doc.out_time = out_time
            attendance_doc.status = "Present"
            attendance_doc.save()
        else:
            # Create new attendance
            attendance_doc = frappe.get_doc({
                "doctype": "Attendance",
                "employee": self.employee,
                "attendance_date": self.date,
                "status": "Present",
                "in_time": in_time,
                "out_time": out_time
            })
            attendance_doc.insert()

        frappe.msgprint(_("Attendance has been successfully generated for the employee."))

    @staticmethod
    def get_regularization_candidates():
        # Fetch attendance records that need regularization
        candidates = db.get_all(
            "Attendance",
            filters={"status": ["in", ["Absent", "Present"]]},
            fields=["employee", "employee_name", "attendance_date", "status"]
        )

        result = []
        for candidate in candidates:
            checkins = db.get_all(
                "Employee Checkin",
                filters={
                    "employee": candidate["employee"],
                    "date": candidate["attendance_date"]
                },
                fields=["time", "log_type"]
            )

            if checkins:
                in_time = min([c["time"] for c in checkins if c["log_type"] == "IN"], default=None)
                out_time = max([c["time"] for c in checkins if c["log_type"] == "OUT"], default=None)

                if in_time and out_time:
                    result.append({
                        "employee": candidate["employee"],
                        "employee_name": candidate["employee_name"],
                        "date": candidate["attendance_date"],
                        "status": candidate["status"],
                        "in_time": in_time,
                        "out_time": out_time,
                        "reason": ""
                    })

        return result


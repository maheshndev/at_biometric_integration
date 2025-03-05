import frappe
from frappe.model.document import Document
from frappe.utils import nowdate

class AttendanceRegularization(Document):
    pass

def check_missing_checkins():
    """
    Checks for missing employee check-ins and logs an error if found.
    Runs as a daily scheduled job.
    """
    employees = frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "employee_name"])
    
    for emp in employees:
        checkins = frappe.get_all("Employee Checkin", 
                                  filters={"employee": emp.name, "log_date": nowdate()},
                                  fields=["log_type", "time"])
        
        if not checkins:
            frappe.log_error(f"Missing check-in for {emp.employee_name} on {nowdate()}", "Attendance Regularization")

def process_regularization():
    """
    Processes approved Attendance Regularization requests and creates Employee Check-in entries.
    """
    requests = frappe.get_all("Attendance Regularization", 
                              filters={"status": "Approved"}, 
                              fields=["employee", "date", "in_time", "out_time"])
    
    for req in requests:
        checkin_data = [
            {"employee": req["employee"], "log_type": "IN", "log_date": req["date"], "time": req["in_time"]},
            {"employee": req["employee"], "log_type": "OUT", "log_date": req["date"], "time": req["out_time"]}
        ]
        
        for checkin in checkin_data:
            if not frappe.db.exists("Employee Checkin", {
                "employee": checkin["employee"], 
                "log_date": checkin["log_date"], 
                "log_type": checkin["log_type"]
            }):
                doc = frappe.get_doc({
                    "doctype": "Employee Checkin",
                    "employee": checkin["employee"],
                    "log_date": checkin["log_date"],
                    "log_type": checkin["log_type"],
                    "time": checkin["time"]
                })
                doc.insert()
                frappe.db.commit()

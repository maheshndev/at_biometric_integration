import frappe

def process_regularization(doc):
    """
    Process the approved Attendance Regularization request
    and update Employee Check-in records.
    """
    if not doc.employee or not doc.date or not doc.in_time or not doc.out_time:
        frappe.throw("Employee, Date, In Time, and Out Time are required.")

    checkin_data = [
        {"employee": doc.employee, "log_type": "IN", "log_date": doc.date, "time": doc.in_time},
        {"employee": doc.employee, "log_type": "OUT", "log_date": doc.date, "time": doc.out_time}
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

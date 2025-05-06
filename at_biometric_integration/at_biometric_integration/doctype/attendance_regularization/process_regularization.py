import frappe
from datetime import datetime, time, timedelta

def process_regularization(doc):
    """
    Create missing Employee Checkin entries for approved regularization.
    """
    if not (doc.employee and doc.date and doc.in_time and doc.out_time):
        frappe.throw("Employee, Date, In Time, and Out Time are required.")

    # Combine date with time if time is timedelta or time object
    def combine_date_time(date, time_obj):
        if isinstance(time_obj, timedelta):
            return datetime.combine(date, (datetime.min + time_obj).time())
        elif isinstance(time_obj, time):
            return datetime.combine(date, time_obj)
        elif isinstance(time_obj, datetime):
            return time_obj
        else:
            frappe.throw("Invalid time format for in_time or out_time.")

    in_datetime = combine_date_time(doc.date, doc.in_time)
    out_datetime = combine_date_time(doc.date, doc.out_time)

    checkin_data = [
        {"employee": doc.employee, "log_type": "IN", "log_date": doc.date, "time": in_datetime},
        {"employee": doc.employee, "log_type": "OUT", "log_date": doc.date, "time": out_datetime}
    ]

    for checkin in checkin_data:
        exists = frappe.db.exists("Employee Checkin", {
            "employee": checkin["employee"],
            "log_date": checkin["log_date"],
            "log_type": checkin["log_type"]
        })

        if not exists:
            frappe.get_doc({
                "doctype": "Employee Checkin",
                **checkin
            }).insert(ignore_permissions=True)

    frappe.db.commit()

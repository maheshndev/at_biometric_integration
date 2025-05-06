import frappe

def process_regularization(doc):
    """
    Create missing Employee Checkin entries for approved regularization.
    """
    if not (doc.employee and doc.date and doc.in_time and doc.out_time):
        frappe.throw("Employee, Date, In Time, and Out Time are required.")

    checkin_data = [
        {"employee": doc.employee, "log_type": "IN", "log_date": doc.date, "time": doc.in_time},
        {"employee": doc.employee, "log_type": "OUT", "log_date": doc.date, "time": doc.out_time}
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

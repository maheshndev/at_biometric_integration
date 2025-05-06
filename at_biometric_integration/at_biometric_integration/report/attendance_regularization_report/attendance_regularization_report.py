import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Data", "width": 120},
        {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
        {"label": _("Date"), "fieldname": "attendance_date", "fieldtype": "Date", "width": 150},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": _("In Time"), "fieldname": "in_time", "fieldtype": "Time", "width": 100},
        {"label": _("Out Time"), "fieldname": "out_time", "fieldtype": "Time", "width": 100},
        {"label": _("Reason"), "fieldname": "reason", "fieldtype": "Data", "width": 150},
        {"label": _("Action"), "fieldname": "action", "fieldtype": "Button", "width": 100, "default": _("Regularize")},
    ]

def get_data(filters=None):
    query = """
        SELECT
            att.employee,
            att.employee_name,
            att.attendance_date,
            att.status,
            ec_in.time AS in_time,
            ec_out.time AS out_time,
            CASE
                WHEN att.status = 'Absent' THEN 'Needs Regularization'
                ELSE ''
            END AS reason
        FROM
            `tabAttendance` att
        LEFT JOIN
            `tabEmployee Checkin` ec_in
            ON att.employee = ec_in.employee AND att.attendance_date = ec_in.log_date
        LEFT JOIN
            `tabEmployee Checkin` ec_out
            ON att.employee = ec_out.employee AND att.attendance_date = ec_out.log_date
        WHERE
            att.attendance_date < CURDATE()
    """
    return frappe.db.sql(query, as_dict=True)

@frappe.whitelist()
def regularize_action(employee, date):
    try:
        # Fetch attendance and checkin details for the employee on the specified date
        attendance_doc = frappe.get_doc("Attendance", {
            "employee": employee,
            "attendance_date": date
        })

        if not attendance_doc or not attendance_doc.name:
            frappe.throw(_("Attendance document not found or is missing the 'name' field."))

        checkin_docs = frappe.get_all(
            "Employee Checkin",
            filters={"employee": employee, "log_date": date},
            fields=["employee_name", "time"]
        )

        if not checkin_docs:
            frappe.throw(_("No Employee Checkin found for the given date."))

        in_time = checkin_docs[0]["time"]
        out_time = checkin_docs[-1]["time"]

        # Create Attendance Regularization request
        regularization = frappe.get_doc({
            "doctype": "Attendance Regularization",
            "employee": employee,
            "employee_name": attendance_doc.employee_name,
            "date": date,
            "status": "Present",  # Assuming it's a regularization of absence to present
            "in_time": in_time,
            "out_time": out_time,
            "reason": "Attendance regularization request"
        })
        regularization.insert(ignore_permissions=True)
        regularization.submit()

        return {"message": "Attendance Regularized"}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Regularization Error"))
        return {"error": str(e)}


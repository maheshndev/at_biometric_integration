import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_attendance_data(filters)
    return columns, data

def get_columns():
    return [
        _("Employee Name") + ":Data:200",
        _("Employee ID") + ":Data:120",  # Adjusted the column name
        _("Date") + ":Date:100",
        _("Status") + ":Data:100",
        _("Regularization Needed") + ":Data:150"
    ]

def get_attendance_data(filters):
    conditions = get_conditions(filters)
    query = """
        SELECT employee_name, employee, attendance_date, status
        FROM `tabAttendance`
        WHERE {conditions}
        ORDER BY attendance_date DESC
    """.format(conditions=conditions)
    return frappe.db.sql(query, filters, as_dict=True)

def get_conditions(filters):
    conditions = []
    if filters.get('period'):
        conditions.append("attendance_period = %(period)s")
    if filters.get('month'):
        conditions.append("MONTH(attendance_date) = %(month)s")
    if filters.get('from_date'):
        conditions.append("attendance_date >= %(from_date)s")
    if filters.get('to_date'):
        conditions.append("attendance_date <= %(to_date)s")
    
    return " AND ".join(conditions) if conditions else "1=1"

import frappe
from frappe.utils import cint, format_time, format_date

def execute(filters=None):
    if not filters:
        filters = {}

    conditions = ""
    if filters.get("employee"):
        conditions += f"AND employee = '{filters.get('employee')}'"

    query = f"""
        SELECT 
            employee, employee_name, log_date,
            MIN(time) AS first_checkin, MAX(time) AS last_checkout,
            TIMEDIFF(MAX(time), MIN(time)) AS working_hours
        FROM (
            SELECT 
                employee, employee_name, DATE(time) AS log_date, time 
            FROM `tabEmployee Checkin`
            WHERE 1=1 {conditions}
        ) AS subquery
        GROUP BY employee, log_date
        ORDER BY log_date DESC, employee
    """

    data = frappe.db.sql(query, as_dict=True)

    columns = [
        {"fieldname": "employee", "label": "Employee", "fieldtype": "Link", "options": "Employee", "width": 150},
        {"fieldname": "employee_name", "label": "Employee Name", "fieldtype": "Data", "width": 200},
        {"fieldname": "log_date", "label": "Date", "fieldtype": "Date", "width": 120},
        {"fieldname": "first_checkin", "label": "First Check-In", "fieldtype": "Time", "width": 120},
        {"fieldname": "last_checkout", "label": "Last Check-Out", "fieldtype": "Time", "width": 120},
        {"fieldname": "working_hours", "label": "Total Working Hours", "fieldtype": "Duration", "width": 150},
    ]

    return columns, data

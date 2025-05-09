# Attendance Regularization Request Report - Python

import frappe
from datetime import datetime, timedelta

def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = [
        {"fieldname": "employee", "label": "Employee", "fieldtype": "Link", "options": "Employee", "width": 150},
        {"fieldname": "employee_name", "label": "Employee Name", "fieldtype": "Data", "width": 200},
        {"fieldname": "attendance_date", "label": "Attendance Date", "fieldtype": "Date", "width": 150},
        {"fieldname": "in_time", "label": "In Time", "fieldtype": "Time", "width": 150},
        {"fieldname": "out_time", "label": "Out Time", "fieldtype": "Time", "width": 150},
        {"fieldname": "working_hours", "label": "Working Hours (Hrs)", "fieldtype": "Float", "width": 150},
        {"fieldname": "status", "label": "Status", "fieldtype": "Select", "options":"", "width": 150},
        {"fieldname": "action", "label": "Action", "fieldtype": "Data", "width": 100}  # New column for the action button
    ]

    data = []

    # Build the filters for fetching attendance records
    conditions = []

    if filters.get("employee"):
        conditions.append(["employee", "=", filters.employee])

    if filters.get("from_date") and filters.get("to_date"):
        conditions.append(["attendance_date", "between", [filters.from_date, filters.to_date]])

    if filters.get("month") and filters.get("year"):
        month = int(filters.month)
        year = int(filters.year)
        from_date = datetime(year, month, 1)
        to_date = datetime(year, month + 1, 1) - timedelta(days=1)
        conditions.append(["attendance_date", "between", [from_date.strftime("%Y-%m-%d"), to_date.strftime("%Y-%m-%d")]])

    attendance_records = frappe.get_all(
        "Attendance",
        filters=conditions,
        fields=["employee", "attendance_date", "TIME(in_time) as in_time", "TIME(out_time) as out_time", "working_hours", "status",],
        order_by="attendance_date asc"
    )

    for record in attendance_records:
        employee_name = frappe.get_value("Employee", record.employee, "employee_name")

        data.append({
            "employee": record.employee,
            "employee_name": employee_name,
            "attendance_date": record.attendance_date,
            "in_time": record.in_time,
            "out_time": record.out_time,
            "working_hours": record.working_hours,
            "status": record.status,
            "action": "Regularize"  # Placeholder for the action button
        })

    # Fetch distinct months and years from Attendance
    months_and_years = frappe.db.sql("""
        SELECT DISTINCT 
            MONTH(attendance_date) AS month, 
            YEAR(attendance_date) AS year 
        FROM `tabAttendance`
        ORDER BY year DESC, month ASC
    """, as_dict=True)

    # Add metadata for months and years
    metadata = {
        "months": [str(row["month"]) for row in months_and_years],
        "years": [str(row["year"]) for row in months_and_years]
    }

    return columns, data, metadata

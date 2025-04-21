import frappe
from frappe.utils import getdate, nowdate
from datetime import datetime, timedelta

def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = [
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 160},
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": "Date", "fieldname": "date", "fieldtype": "Date", "width": 100},
        {"label": "Shift", "fieldname": "shift", "fieldtype": "Data", "width": 100},
        {"label": "Working Hours", "fieldname": "working_hours", "fieldtype": "Float", "width": 120},
        {"label": "Leave Type", "fieldname": "leave_type", "fieldtype": "Link", "options": "Leave Type", "width": 120},
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 120},
        {"label": "In Time", "fieldname": "in_time", "fieldtype": "Time", "width": 100},
        {"label": "Out Time", "fieldname": "out_time", "fieldtype": "Time", "width": 100},
        {"label": "Department", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 120},
    ]

    period = filters.get("period")
    today = getdate(nowdate())

    # Handle monthly period based on selected month
    if period == "Monthly" and filters.get("months"):
        month_str = filters.months
        month_map = {
            "January": 1, "February": 2, "March": 3, "April": 4,
            "May": 5, "June": 6, "July": 7, "August": 8,
            "September": 9, "October": 10, "November": 11, "December": 12
        }
        month = month_map.get(month_str, today.month)
        year = today.year
        filters.from_date = datetime(year, month, 1).date()
        # Next month minus one day
        if month == 12:
            filters.to_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            filters.to_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
    else:
        filters.from_date = getdate(filters.get("from_date") or today)

        if not filters.get("to_date"):
            if period == "Weekly":
                filters.to_date = filters.from_date + timedelta(days=6)
            elif period == "Monthly":
                filters.to_date = filters.from_date + timedelta(days=29)
            else:  # Daily
                filters.to_date = filters.from_date
        else:
            filters.to_date = getdate(filters.to_date)

    conditions = [f"attendance.attendance_date BETWEEN '{filters.from_date}' AND '{filters.to_date}'"]

    if filters.get("status"):
        conditions.append(f"attendance.status = '{filters.status}'")
    if filters.get("employee"):
        conditions.append(f"attendance.employee = '{filters.employee}'")
    if filters.get("company"):
        conditions.append(f"attendance.company = '{filters.company}'")
    if filters.get("department"):
        conditions.append(f"emp.department = '{filters.department}'")
    if filters.get("employee_name"):
        conditions.append(f"emp.employee_name LIKE '%{filters.employee_name}%'")

    condition_str = "WHERE " + " AND ".join(conditions) if conditions else ""

    data = frappe.db.sql(f"""
        SELECT
            attendance.employee,
            emp.employee_name,
            attendance.status,
            attendance.attendance_date AS date,
            attendance.shift,
            attendance.working_hours,
            attendance.leave_type,
            attendance.company,
            TIME(attendance.in_time) AS in_time,
            TIME(attendance.out_time) AS out_time,
            emp.department
        FROM `tabAttendance` attendance
        LEFT JOIN `tabEmployee` emp ON emp.name = attendance.employee
        {condition_str}
        ORDER BY attendance.attendance_date DESC
    """, as_dict=True)

    return columns, data


import frappe
from frappe.utils import getdate, nowdate
from datetime import datetime, timedelta
import calendar

def execute(filters=None):
    filters = frappe._dict(filters or {})

    columns = [
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 160},
        {"label": "Present", "fieldname": "present", "fieldtype": "Int", "width": 100},
        {"label": "Absent", "fieldname": "absent", "fieldtype": "Int", "width": 100},
        {"label": "Leave", "fieldname": "leave", "fieldtype": "Int", "width": 100},
        {"label": "Half Day", "fieldname": "half_day", "fieldtype": "Int", "width": 100},
        {"label": "Work From Home", "fieldname": "wfh", "fieldtype": "Int", "width": 120},
        {"label": "Working Hours", "fieldname": "working_hours", "fieldtype": "Float", "width": 120},
    ]

    today = getdate(nowdate())
    month_str = filters.get("month")
    year = int(filters.get("year") or today.year)

    if month_str:
        month_map = {
            "January": 1, "February": 2, "March": 3, "April": 4,
            "May": 5, "June": 6, "July": 7, "August": 8,
            "September": 9, "October": 10, "November": 11, "December": 12
        }
        month = month_map.get(month_str, today.month)

        # Calculate first and last day numbers
        first_day = "01"
        last_day = str(calendar.monthrange(year, month)[1]).zfill(2)

        filters.from_date = first_day
        filters.to_date = last_day

    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw("Please select either a Month or both From Date and To Date")

    # Convert from and to dates to full format to use in SQL
    full_from_date = datetime(year, month, int(filters.from_date)).date()
    full_to_date = datetime(year, month, int(filters.to_date)).date()

    conditions = [f"att.attendance_date BETWEEN '{full_from_date}' AND '{full_to_date}'"]

    if filters.get("employee"):
        conditions.append(f"att.employee = '{filters.employee}'")
    if filters.get("company"):
        conditions.append(f"att.company = '{filters.company}'")

    condition_str = "WHERE " + " AND ".join(conditions)

    data = frappe.db.sql(f"""
        SELECT
            att.employee,
            emp.employee_name,
            SUM(CASE WHEN att.status = 'Present' THEN 1 ELSE 0 END) AS present,
            SUM(CASE WHEN att.status = 'Absent' THEN 1 ELSE 0 END) AS absent,
            SUM(CASE WHEN att.status = 'On Leave' THEN 1 ELSE 0 END) AS `leave`,
            SUM(CASE WHEN att.status = 'Half Day' THEN 1 ELSE 0 END) AS half_day,
            SUM(CASE WHEN att.status = 'Work From Home' THEN 1 ELSE 0 END) AS wfh,
            SUM(IFNULL(att.working_hours, 0)) AS working_hours
        FROM `tabAttendance` att
        LEFT JOIN `tabEmployee` emp ON emp.name = att.employee
        {condition_str}
        GROUP BY att.employee
        ORDER BY att.employee
    """, as_dict=True)

    totals = {
        "employee": "Total",
        "employee_name": "",
        "present": 0,
        "absent": 0,
        "leave": 0,
        "half_day": 0,
        "wfh": 0,
        "working_hours": 0.0,
    }

    for row in data:
        totals["present"] += row.get("present", 0)
        totals["absent"] += row.get("absent", 0)
        totals["leave"] += row.get("leave", 0)
        totals["half_day"] += row.get("half_day", 0)
        totals["wfh"] += row.get("wfh", 0)
        totals["working_hours"] += row.get("working_hours", 0.0)

    data.append(totals)

    return columns, data

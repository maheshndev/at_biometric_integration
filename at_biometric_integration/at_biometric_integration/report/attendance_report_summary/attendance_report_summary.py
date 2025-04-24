import frappe
from frappe.utils import getdate, nowdate, add_days
from datetime import datetime, timedelta

def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = [
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 160},
        {"label": "Shift", "fieldname": "shift", "fieldtype": "Link", "options": "Shift Type", "width": 120},
        {"label": "Date", "fieldname": "date", "fieldtype": "Date", "width": 100},
        {"label": "In Time", "fieldname": "in_time", "fieldtype": "Time", "width": 100},
        {"label": "Out Time", "fieldname": "out_time", "fieldtype": "Time", "width": 100},
        {"label": "Working Hours", "fieldname": "working_hours", "fieldtype": "Float", "width": 100},
        {"label": "Early Entry", "fieldname": "early_entry", "fieldtype": "Data", "width": 100},
        {"label": "Early Going", "fieldname": "early_going", "fieldtype": "Data", "width": 100},
        {"label": "Late Entry", "fieldname": "late_entry", "fieldtype": "Data", "width": 100},
        {"label": "Late Going", "fieldname": "late_going", "fieldtype": "Data", "width": 100},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 120},
        {"label": "Department", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 120},
    ]

    period = filters.get("period")
    today = getdate(nowdate())

    # Handle different period types
    if period == "Monthly" and filters.get("months"):
        month_str = filters.months
        month_map = {
            "January": 1, "February": 2, "March": 3, "April": 4,
            "May": 5, "June": 6, "July": 7, "August": 8,
            "September": 9, "October": 10, "November": 11, "December": 12
        }
        month = month_map.get(month_str, today.month)
        year = int(filters.get("year", today.year))  # Get year from filters or current year
        filters.from_date = datetime(year, month, 1).date()
        # Next month minus one day
        if month == 12:
            filters.to_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            filters.to_date = datetime(year, month + 1, 1).date() - timedelta(days=1)

    elif period == "Weekly":
        start_of_week = today - timedelta(days=today.weekday())  # Get start of the current week
        filters.from_date = start_of_week
        filters.to_date = start_of_week + timedelta(days=6)  # End of the week

    elif period == "Daily":
        filters.from_date = today
        filters.to_date = today

    else:
        filters.from_date = getdate(filters.get("from_date") or today)
        filters.to_date = getdate(filters.get("to_date") or today)

    conditions = [f"attendance.attendance_date BETWEEN '{filters.from_date}' AND '{filters.to_date}'"]

    if filters.get("status"):
        conditions.append(f"attendance.status = '{filters.status}'")
    if filters.get("employee"):
        conditions.append(f"attendance.employee = '{filters.employee}'")
    if filters.get("company"):
        conditions.append(f"attendance.company = '{filters.company}'")
    if filters.get("department"):
        conditions.append(f"emp.department = '{filters.department}'")

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
            emp.department,
            st.start_time AS shift_start,
            st.end_time AS shift_end
        FROM `tabAttendance` attendance
        LEFT JOIN `tabEmployee` emp ON emp.name = attendance.employee
        LEFT JOIN `tabShift Type` st ON st.name = attendance.shift
        {condition_str}
        ORDER BY attendance.attendance_date DESC
    """, as_dict=True)

    for row in data:
        # Calculate working_hours as H:MM format
        if row.working_hours:
            hours = int(row.working_hours)
            minutes = int((row.working_hours - hours) * 60)
            row["working_hours"] = f"{hours}:{minutes:02d}"

        # Early Entry calculation
        if row.get("shift_start") and row.get("in_time"):
            shift_start = datetime.strptime(str(row.shift_start), "%H:%M:%S").time()
            in_time = datetime.strptime(str(row.in_time), "%H:%M:%S").time()
            if in_time < shift_start:
                early_minutes = (datetime.combine(datetime.today(), shift_start) - datetime.combine(datetime.today(), in_time)).seconds // 60
                row["early_entry"] = f"{early_minutes // 60}:{early_minutes % 60:02d}"
            else:
                row["early_entry"] = "-"
        else:
            row["early_entry"] = "-"

        # Early Going calculation
        if row.get("shift_end") and row.get("out_time"):
            shift_end = datetime.strptime(str(row.shift_end), "%H:%M:%S").time()
            out_time = datetime.strptime(str(row.out_time), "%H:%M:%S").time()
            if out_time < shift_end:
                early_minutes = (datetime.combine(datetime.today(), shift_end) - datetime.combine(datetime.today(), out_time)).seconds // 60
                row["early_going"] = f"{early_minutes // 60}:{early_minutes % 60:02d}"
            else:
                row["early_going"] = "-"
        else:
            row["early_going"] = "-"

        # Late Entry calculation
        if row.get("shift_start") and row.get("in_time"):
            shift_start = datetime.strptime(str(row.shift_start), "%H:%M:%S").time()
            in_time = datetime.strptime(str(row.in_time), "%H:%M:%S").time()
            if in_time > shift_start:
                late_minutes = (datetime.combine(datetime.today(), in_time) - datetime.combine(datetime.today(), shift_start)).seconds // 60
                row["late_entry"] = f"{late_minutes // 60}:{late_minutes % 60:02d}"
            else:
                row["late_entry"] = "-"
        else:
            row["late_entry"] = "-"

        # Late Going calculation
        if row.get("shift_end") and row.get("out_time"):
            shift_end = datetime.strptime(str(row.shift_end), "%H:%M:%S").time()
            out_time = datetime.strptime(str(row.out_time), "%H:%M:%S").time()
            if out_time > shift_end:
                late_minutes = (datetime.combine(datetime.today(), out_time) - datetime.combine(datetime.today(), shift_end)).seconds // 60
                row["late_going"] = f"{late_minutes // 60}:{late_minutes % 60:02d}"
            else:
                row["late_going"] = "-"
        else:
            row["late_going"] = "-"

    return columns, data

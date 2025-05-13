
import frappe
from frappe.utils import getdate, nowdate
from datetime import datetime, timedelta

def actual_working_duration(employee, date):
    """Calculate actual working hours based on alternating IN/OUT checkins (odd as IN, even as OUT) and return in HH:MM format."""
    checkins = frappe.get_all("Employee Checkin",
        filters={
            "employee": employee,
            "time": ["between", [f"{date} 00:00:00", f"{date} 23:59:59"]]
        },
        fields=["time"],
        order_by="time"
    )
    
    total_duration = 0.0
    times = [c.time for c in checkins]

    for i in range(0, len(times) - 1, 2):
        in_time = times[i]
        out_time = times[i + 1]
        if out_time > in_time:
            total_duration += (out_time - in_time).total_seconds()

    if total_duration:
        hours = int(total_duration // 3600)
        minutes = int((total_duration % 3600) // 60)
        return f"{hours:02d}:{minutes:02d}"
    else:
        return "-"

def update_working_hours_from_checkins():
    employees = frappe.get_all("Employee", fields=["name"])

    for emp in employees:
        checkins = frappe.get_all("Employee Checkin",
            filters={"employee": emp.name},
            fields=["time"],
            order_by="time asc"
        )
        # Group checkins by date
        checkins_by_date = {}
        for checkin in checkins:
            date_str = checkin.time.date().isoformat()
            checkins_by_date.setdefault(date_str, []).append(checkin.time)

        for date_str, times in checkins_by_date.items():
            if len(times) < 2:
                continue  # Need both in and out time to compute hours

            in_time = times[0]
            out_time = times[-1]
            working_hours = round((out_time - in_time).total_seconds() / 3600, 2)

            attendance = frappe.get_value("Attendance", {
                "employee": emp.name,
                "attendance_date": date_str
            }, "name")

            if attendance:
                frappe.db.set_value("Attendance", attendance, "working_hours", working_hours)
                frappe.db.commit()

def execute(filters=None):
    filters = frappe._dict(filters or {})
    # update_working_hours_from_checkins()
    columns = [
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 160},
        {"label": "Shift", "fieldname": "shift", "fieldtype": "Link", "options": "Shift Type", "width": 120},
        {"label": "Date", "fieldname": "date", "fieldtype": "Date", "width": 100},
        {"label": "In Time", "fieldname": "in_time", "fieldtype": "Time", "width": 100},
        {"label": "Out Time", "fieldname": "out_time", "fieldtype": "Time", "width": 100},
        {"label": "Actual Work Duration", "fieldname": "working_hours", "fieldtype": "Data", "width": 100},
        {"label": "Total Work Duration", "fieldname": "total_working_hours", "fieldtype": "Data", "width": 100},
        {"label": "Early Entry", "fieldname": "early_entry", "fieldtype": "Data", "width": 100},
        {"label": "Late By", "fieldname": "late_entry", "fieldtype": "Data", "width": 100},
        {"label": "Early Going By", "fieldname": "early_going", "fieldtype": "Data", "width": 100},
        {"label": "Late Going", "fieldname": "late_going", "fieldtype": "Data", "width": 100},
        {"label": "Over Time", "fieldname": "over_time", "fieldtype": "Data", "width": 100},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 120},
        {"label": "Department", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 120},
    ]

    today = getdate(nowdate())

    # Determine date range
    period = filters.get("period")
    if period == "Monthly" and filters.get("months"):
        month_map = {
            "January": 1, "February": 2, "March": 3, "April": 4,
            "May": 5, "June": 6, "July": 7, "August": 8,
            "September": 9, "October": 10, "November": 11, "December": 12
        }
        month = month_map.get(filters.months, today.month)
        year = int(filters.get("year", today.year))
        filters.from_date = datetime(year, month, 1).date()
        filters.to_date = (datetime(year + (month // 12), (month % 12) + 1, 1) - timedelta(days=1)).date()
    elif period == "Weekly":
        start_of_week = today - timedelta(days=today.weekday())
        filters.from_date = start_of_week
        filters.to_date = start_of_week + timedelta(days=6)
    elif period == "Daily":
        filters.from_date = filters.to_date = today
    else:
        filters.from_date = getdate(filters.get("from_date") or today)
        filters.to_date = getdate(filters.get("to_date") or today)

    # Build conditions
    conditions = [f"attendance.attendance_date BETWEEN '{filters.from_date}' AND '{filters.to_date}'"]
    if filters.get("status"):
        conditions.append(f"attendance.status = '{filters.status}'")
    if filters.get("employee"):
        conditions.append(f"attendance.employee = '{filters.employee}'")
    if filters.get("company"):
        conditions.append(f"attendance.company = '{filters.company}'")
    if filters.get("department"):
        conditions.append(f"emp.department = '{filters.department}'")

    condition_str = "WHERE " + " AND ".join(conditions)

    # Main data query
    data = frappe.db.sql(f"""
        SELECT
            attendance.name AS attendance_id,
            attendance.employee,
            emp.employee_name,
            attendance.status,
            attendance.attendance_date AS date,
            attendance.shift,
            attendance.working_hours AS t_working_hours,
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
        # Get actual working hours for the day from checkins
        row["working_hours"] = actual_working_duration(row.employee, row.date)
        total_working_hours = row["t_working_hours"]
        # convert to hours and minutes
        if total_working_hours:
            hours = int(total_working_hours)
            minutes = int((total_working_hours - hours) * 60)
            row["total_working_hours"] = f"{hours:02d}:{minutes:02d}"
        else:
            row["total_working_hours"] = "-"
        # Compute shift duration
        try:
            shift_start = datetime.strptime(str(row.get("shift_start")), "%H:%M:%S")
            shift_end = datetime.strptime(str(row.get("shift_end")), "%H:%M:%S")

            # Handle overnight shifts
            if shift_end < shift_start:
                shift_end += timedelta(days=1)

            shift_duration = (shift_end - shift_start).total_seconds() / 3600
        except:
            shift_duration = 0

        # Calculate Over Time
        ot = row["t_working_hours"] - shift_duration
        if ot > 0:
            hours = int(ot)
            minutes = int((ot - hours) * 60)
            row["over_time"] = f"{hours:02d}:{minutes:02d}"
        else:
            row["over_time"] = "-"

        # Early/Late calculations
        for metric, condition, time_field1, time_field2 in [
            ("early_entry", lambda i, s: i < s, "in_time", "shift_start"),
            ("early_going", lambda o, e: o < e, "out_time", "shift_end"),
            ("late_entry", lambda i, s: i > s, "in_time", "shift_start"),
            ("late_going", lambda o, e: o > e, "out_time", "shift_end"),
        ]:
            try:
                t1 = datetime.strptime(str(row.get(time_field1)), "%H:%M:%S").time()
                t2 = datetime.strptime(str(row.get(time_field2)), "%H:%M:%S").time()
                if condition(t1, t2):
                    delta = abs(datetime.combine(datetime.today(), t1) - datetime.combine(datetime.today(), t2))
                    minutes = delta.seconds // 60
                    row[metric] = f"{minutes // 60:02d}:{minutes % 60:02d}"
                else:
                    row[metric] = "-"
            except:
                row[metric] = "-"


    return columns, data

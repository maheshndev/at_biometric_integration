import frappe
from frappe.utils import getdate, nowdate
from datetime import datetime, timedelta
import calendar

def execute(filters=None):
    filters = frappe._dict(filters or {})

    columns = [
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 160},
        {"label": "Present", "fieldname": "present", "fieldtype": "Float", "width": 100},
        {"label": "Leave", "fieldname": "leave", "fieldtype": "Float", "width": 100},
        {"label": "No Of Weekends", "fieldname": "no_of_weekends", "fieldtype": "Float", "width": 100},
        {"label": "No Of Holidays", "fieldname": "no_of_holidays", "fieldtype": "Float", "width": 100},
        {"label": "Absent", "fieldname": "absent", "fieldtype": "Float", "width": 100},
        {"label": "Half Day", "fieldname": "half_day", "fieldtype": "Float", "width": 100},
        {"label": "Total Absent", "fieldname": "total_absent", "fieldtype": "Float", "width": 100},
        {"label": "Total Working Days", "fieldname": "total_working_days", "fieldtype": "Float", "width": 100},
        {"label": "Work From Home", "fieldname": "wfh", "fieldtype": "Float", "width": 120},
        {"label": "Work Duration", "fieldname": "working_hours", "fieldtype": "Float", "width": 120},
        {"label": "Total Work Duration", "fieldname": "total_working_hours", "fieldtype": "Float", "width": 120},
        {"label": "Payment Days", "fieldname": "payment_days", "fieldtype": "Float", "width": 100},
    ]

    today = getdate(nowdate())
    month_str = filters.get("month")
    year = int(filters.get("year") or today.year)
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    if month_str:
        month = {
            "January": 1, "February": 2, "March": 3, "April": 4,
            "May": 5, "June": 6, "July": 7, "August": 8,
            "September": 9, "October": 10, "November": 11, "December": 12
        }.get(month_str, today.month)

        filters.from_date = datetime(year, month, 1).date()
        filters.to_date = datetime(year, month, calendar.monthrange(year, month)[1]).date()

    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw("Please select either a Month or both From Date and To Date")

    from_date = getdate(filters.from_date)
    to_date = getdate(filters.to_date)

    # Attendance data
    attendance = frappe.db.sql("""
        SELECT employee, attendance_date, status, working_hours
        FROM `tabAttendance`
        WHERE attendance_date BETWEEN %s AND %s
        {condition}
    """.format(condition="AND employee = %s" if filters.get("employee") else ""), 
        (from_date, to_date, filters.get("employee")) if filters.get("employee") else (from_date, to_date), 
        as_dict=True
    )

    attendance_map = frappe._dict()
    for att in attendance:
        attendance_map.setdefault(att.employee, {})[att.attendance_date] = att

    # Employees
    employees = frappe.get_all("Employee", fields=["name", "employee_name", "holiday_list"], filters={
        "status": "Active",
        "name": filters.get("employee") or ["!=", ""]
    })

    result = []
    totals = {
        "employee": "Total",
        "present": 0, "leave": 0, "absent": 0,
        "half_day": 0, "wfh": 0, "working_hours": 0,
        "no_of_weekends": 0, "no_of_holidays": 0,
        "total_absent": 0, "total_working_days": 0,
        "total_working_hours": 0, "payment_days": 0
    }

    all_dates = [from_date + timedelta(days=i) for i in range((to_date - from_date).days + 1)]

    for emp in employees:
        emp_attendance = attendance_map.get(emp.name, {})
        if not emp_attendance:
            continue

        # 1. Identify weekends
        weekend_dates = set([d for d in all_dates if d.weekday() in [5, 6]])

        # 2. Identify holidays from holiday list
        holiday_dates = set()
        if emp.holiday_list:
            holidays = frappe.get_all("Holiday", fields=["holiday_date"], filters={
                "parent": emp.holiday_list,
                "holiday_date": ["between", [from_date, to_date]]
            })
            holiday_dates = set(h.holiday_date for h in holidays)

        # 3. Final holidays excluding overlapping weekends
        final_holidays = holiday_dates - weekend_dates
        valid_working_days = set(all_dates) - weekend_dates - final_holidays

        # 4. Initialize counters
        present = leave = absent = half_day = wfh = working_hours = 0

        for date in all_dates:
            record = emp_attendance.get(date)

            if record and date in valid_working_days:
                status = record.status
                working_hours += record.working_hours or 0
                if status == "Present":
                    present += 1
                elif status == "On Leave":
                    leave += 1
                elif status == "Half Day":
                    half_day += 1
                elif status == "Work From Home":
                    wfh += 1
                elif status == "Absent":
                    absent += 1
            elif not record and date in valid_working_days:
                absent += 1

        row = {
            "employee": emp.name+" "+emp.employee_name,
            "present": present,
            "leave": leave,
            "absent": absent,
            "half_day": half_day,
            "wfh": wfh,
            "working_hours": working_hours,
            "no_of_weekends": len(weekend_dates),
            "no_of_holidays": len(final_holidays),
            "total_absent": absent + leave + (half_day / 2),
            "total_working_days": present + (half_day / 2),
            "total_working_hours": working_hours,
            "payment_days": leave + len(final_holidays) + len(weekend_dates) + absent + present + (half_day / 2) + wfh
        }

        for key in totals:
            if key != "employee":
                totals[key] += row.get(key, 0)

        result.append(row)

    if result:
        result.append(totals)

    return columns, result

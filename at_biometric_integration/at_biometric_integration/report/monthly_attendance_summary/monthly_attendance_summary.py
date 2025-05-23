import frappe
from frappe.utils import getdate, nowdate
from datetime import datetime, timedelta
import calendar

def format_number(val):
    # Return "-" for zero or zero-like values
    if val in [0, 0.0, "0", "00", "0.0", "00.00"]:
        return "-"
    if isinstance(val, int):
        return f"{val:02d}"
    elif isinstance(val, float):
        return f"{val:05.2f}"
    return val

def execute(filters=None):
    try:
        filters = frappe._dict(filters or {})
        result = []

        columns = [
            {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 160},
            {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 160},
            {"label": "Present", "fieldname": "present", "fieldtype": "Data", "width": 100},
            {"label": "Leave", "fieldname": "leave", "fieldtype": "Data", "width": 100},
            {"label": "No Of Weekends", "fieldname": "no_of_weekends", "fieldtype": "Data", "width": 100},
            {"label": "No Of Holidays", "fieldname": "no_of_holidays", "fieldtype": "Data", "width": 100},
            {"label": "Absent", "fieldname": "absent", "fieldtype": "Data", "width": 100},
            {"label": "Half Day", "fieldname": "half_day", "fieldtype": "Data", "width": 100},
            {"label": "Earned Leave Taken", "fieldname": "earned_leave_taken", "fieldtype": "Data", "width": 140},
            {"label": "Earned Leave Balance", "fieldname": "earned_leave_balance", "fieldtype": "Data", "width": 140},
            {"label": "Work From Home", "fieldname": "wfh", "fieldtype": "Data", "width": 120},
            {"label": "Total Absent", "fieldname": "total_absent", "fieldtype": "Data", "width": 100},
            {"label": "Total Working Days", "fieldname": "total_working_days", "fieldtype": "Data", "width": 100},
            {"label": "Payment Days", "fieldname": "payment_days", "fieldtype": "Data", "width": 100},
            
        ]

        today = getdate(nowdate())
        month_str = filters.get("month")
        year = int(filters.get("year") or today.year)

        # Handle date range
        if month_str:
            try:
                month = {
                    "January": 1, "February": 2, "March": 3, "April": 4,
                    "May": 5, "June": 6, "July": 7, "August": 8,
                    "September": 9, "October": 10, "November": 11, "December": 12
                }.get(month_str, today.month)
                from_date = datetime(year, month, 1).date()
                to_date = datetime(year, month, calendar.monthrange(year, month)[1]).date()
            except Exception as e:
                frappe.throw(f"Invalid month or year: {e}")
        else:
            try:
                from_date = getdate(filters.get("from_date"))
                to_date = getdate(filters.get("to_date"))
            except Exception as e:
                frappe.throw(f"Invalid date range: {e}")

        if not from_date or not to_date:
            frappe.throw("Please select either a Month or both From Date and To Date")

        # Attendance data
        att_filters = [from_date, to_date]
        att_query = """
            SELECT employee, attendance_date, status
            FROM `tabAttendance`
            WHERE attendance_date BETWEEN %s AND %s
        """
        if filters.get("employee"):
            att_query += " AND employee = %s"
            att_filters.append(filters.get("employee"))

        try:
            attendance = frappe.db.sql(att_query, tuple(att_filters), as_dict=True)
        except Exception as e:
            frappe.throw(f"Error fetching attendance data: {e}")

        attendance_map = {}
        for att in attendance:
            attendance_map.setdefault(att.employee, {})[att.attendance_date] = att

        # Employees
        emp_filters = {"status": "Active"}
        if filters.get("employee"):
            emp_filters["name"] = filters.get("employee")
        try:
            employees = frappe.get_all("Employee", fields=["name", "employee_name", "holiday_list"], filters=emp_filters)
        except Exception as e:
            frappe.throw(f"Error fetching employees: {e}")

        # Earned leave types
        try:
            earned_leave_types = [lt.name for lt in frappe.get_all("Leave Type", filters={"is_earned_leave": 1})]
        except Exception as e:
            frappe.throw(f"Error fetching leave types: {e}")
        if not earned_leave_types:
            earned_leave_types = [""]  # Avoid SQL error if empty

        # Earned leave taken
        try:
            leave_applications = frappe.db.sql("""
                SELECT employee, leave_type, SUM(total_leave_days) as total_leave_days
                FROM `tabLeave Application`
                WHERE status = 'Approved'
                AND leave_type IN %(earned_leave_types)s
                AND from_date <= %(to_date)s
                AND to_date >= %(from_date)s
                GROUP BY employee, leave_type
            """, {
                "earned_leave_types": tuple(earned_leave_types),
                "from_date": from_date,
                "to_date": to_date
            }, as_dict=True)
        except Exception as e:
            frappe.throw(f"Error fetching leave applications: {e}")

        # Earned leave allocations
        try:
            leave_allocations = frappe.db.sql("""
                SELECT employee, leave_type, SUM(total_leaves_allocated) as total_allocated
                FROM `tabLeave Allocation`
                WHERE leave_type IN %(earned_leave_types)s
                AND from_date <= %(to_date)s
                AND to_date >= %(from_date)s
                GROUP BY employee, leave_type
            """, {
                "earned_leave_types": tuple(earned_leave_types),
                "from_date": from_date,
                "to_date": to_date
            }, as_dict=True)
        except Exception as e:
            frappe.throw(f"Error fetching leave allocations: {e}")

        # Maps for quick lookup
        earned_leave_taken_map = {(la.employee, la.leave_type): la.total_leave_days for la in leave_applications}
        leave_allocation_map = {(alloc.employee, alloc.leave_type): alloc.total_allocated for alloc in leave_allocations}

        totals = {
            "employee": "Total",
            "present": 0, "leave": 0, "absent": 0,
            "half_day": 0, "wfh": 0,
            "no_of_weekends": 0, "no_of_holidays": 0,
            "total_absent": 0, "total_working_days": 0,
            "payment_days": 0,
            "earned_leave_taken": 0,
            "earned_leave_balance": 0,
        }

        all_dates = [from_date + timedelta(days=i) for i in range((to_date - from_date).days + 1)]

        for emp in employees:
            emp_attendance = attendance_map.get(emp.name, {})
            weekend_dates = set(d for d in all_dates if d.weekday() in [5, 6])

            # Holidays
            holiday_dates = set()
            if emp.holiday_list:
                try:
                    holidays = frappe.get_all("Holiday", fields=["holiday_date"], filters={
                        "parent": emp.holiday_list,
                        "holiday_date": ["between", [from_date, to_date]]
                    })
                    holiday_dates = set(h.holiday_date for h in holidays)
                except Exception as e:
                    frappe.throw(f"Error fetching holidays for {emp.name}: {e}")

            final_holidays = holiday_dates - weekend_dates
            valid_working_days = set(all_dates) - weekend_dates - final_holidays

            present = leave = absent = half_day = wfh = 0

            for date in all_dates:
                record = emp_attendance.get(date)
                if date in valid_working_days:
                    if record:
                        status = record.status
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
                    else:
                        absent += 1

            # Earned leave taken and balance
            earned_leave_taken = sum(
                v for (ename, _), v in earned_leave_taken_map.items() if ename == emp.name
            )
            total_allocated = sum(
                v for (ename, _), v in leave_allocation_map.items() if ename == emp.name
            )
            earned_leave_balance = total_allocated - earned_leave_taken

            row = {
                "employee": emp.name,
                "employee_name": emp.employee_name,
                "present": present,
                "leave": leave,
                "absent": absent,
                "half_day": half_day,
                "wfh": wfh,
                "no_of_weekends": len(weekend_dates),
                "no_of_holidays": len(final_holidays),
                "total_absent": absent + leave + (half_day / 2),
                "total_working_days": present + (half_day / 2),
                "payment_days": leave + len(final_holidays) + len(weekend_dates) + absent + present + (half_day / 2) + wfh,
                "earned_leave_taken": earned_leave_taken,
                "earned_leave_balance": earned_leave_balance,
            }

            for key in totals:
                if key != "employee":
                    totals[key] += row.get(key, 0)

            if present + leave + absent + half_day + wfh > 0:
                # Format numbers
                formatted_row = {}
                for col in columns:
                    fname = col["fieldname"]
                    val = row.get(fname)
                    if fname == "employee":
                        formatted_row[fname] = val
                    else:
                        formatted_row[fname] = format_number(val)
                result.append(formatted_row)

        if result:
            # Format totals row
            formatted_totals = {}
            for col in columns:
                fname = col["fieldname"]
                val = totals.get(fname)
                if fname == "employee":
                    formatted_totals[fname] = val
                else:
                    formatted_totals[fname] = format_number(val)
            result.append(formatted_totals)

        return columns, result

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Monthly Attendance Summary Error")
        frappe.throw(f"An error occurred while generating the report: {e}")

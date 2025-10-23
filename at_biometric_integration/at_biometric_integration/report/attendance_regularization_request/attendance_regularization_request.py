# Attendance Regularization Request Report - Fixed & Enhanced (Auto Load)
import frappe
from datetime import datetime, timedelta, date
from frappe.utils import getdate, format_time


def execute(filters=None):
    filters = frappe._dict(filters or {})

    # ---------------- Load Settings ----------------
    settings = frappe.get_single("Attendance Regularization Settings", None) if frappe.db.exists("DocType", "Attendance Regularization Settings") else None
    enable_feature = getattr(settings, "enable_regularization", True) if settings else True
    min_delay_hours = int(getattr(settings, "minimum_delay_hours", getattr(settings, "minimum_delay", 24) if settings else 24))
    # ✅ Changed from 72 → 42 hours
    max_delay_hours = int(getattr(settings, "maximum_delay_hours", getattr(settings, "maximum_delay", 42) if settings else 42))
    # ✅ Changed from 5 → 3 per month
    max_requests_per_month = int(getattr(settings, "max_requests_per_month", 3) if settings else 3)
    exclude_weekends = bool(getattr(settings, "exclude_weekends", True) if settings else True)
    exclude_holidays = bool(getattr(settings, "exclude_holidays", True) if settings else True)

    # ---------------- Define Columns ----------------
    columns = [
        {"fieldname": "employee", "label": "Employee", "fieldtype": "Link", "options": "Employee", "width": 150},
        {"fieldname": "employee_name", "label": "Employee Name", "fieldtype": "Data", "width": 200},
        {"fieldname": "attendance_date", "label": "Attendance Date", "fieldtype": "Date", "width": 120},
        {"fieldname": "shift_start", "label": "Shift Start", "fieldtype": "Data", "width": 100},
        {"fieldname": "shift_end", "label": "Shift End", "fieldtype": "Data", "width": 100},
        {"fieldname": "in_time", "label": "In Time", "fieldtype": "Data", "width": 130},
        {"fieldname": "out_time", "label": "Out Time", "fieldtype": "Data", "width": 130},
        {"fieldname": "working_hours", "label": "Working Hours (HH:MM)", "fieldtype": "Data", "width": 140},
        {"fieldname": "status", "label": "Status", "fieldtype": "Select", "options": "Present\nAbsent\nOn Leave\nHalf Day\nMissed Punch", "width": 120},
        {"fieldname": "missed_punch", "label": "Missed Punch", "fieldtype": "Data", "width": 100},
        {"fieldname": "regularization_count", "label": "Regularization Count (Month)", "fieldtype": "Int", "width": 160},
        {"fieldname": "regularization_eligible", "label": "Regularization Eligible", "fieldtype": "Data", "width": 140},
        {"fieldname": "action", "label": "Action", "fieldtype": "Data", "width": 120},
        {"fieldname": "remarks", "label": "Remarks", "fieldtype": "Data", "width": 200}
    ]

    data = []

    # ---------------- Build Filters ----------------
    conditions = []
    if filters.get("employee"):
        conditions.append(["employee", "=", filters.employee])

    if filters.get("from_date") and filters.get("to_date"):
        conditions.append(["attendance_date", "between", [filters.from_date, filters.to_date]])
    else:
        # Default to last 7 days if not provided
        to_date = date.today()
        from_date = to_date - timedelta(days=7)
        conditions.append(["attendance_date", "between", [from_date, to_date]])

    # ---------------- Fetch Attendance ----------------
    attendance_records = frappe.get_all(
        "Attendance",
        filters=conditions,
        fields=["name", "employee", "attendance_date", "in_time", "out_time", "working_hours", "status"],
        order_by="attendance_date asc"
    )

    today_dt = datetime.now()

    for record in attendance_records:
        emp = record.employee
        employee_name = frappe.get_value("Employee", emp, "employee_name") or ""
        att_date = getdate(record.attendance_date)

        # Get shift start and end from Employee's default shift
        shift_start, shift_end = get_shift_from_default_shift(emp)

        # Format in_time and out_time (remove date)
        in_time = format_time_only(record.in_time)
        out_time = format_time_only(record.out_time)

        # Working hours formatting
        formatted_working_hours = "-"
        if record.working_hours:
            try:
                wh = float(record.working_hours)
                hrs = int(wh)
                mins = int(round((wh - hrs) * 60))
                formatted_working_hours = f"{hrs:02d}:{mins:02d}"
            except:
                formatted_working_hours = str(record.working_hours)

        # Determine missed punch
        missed_punch = "-"
        if not in_time and not out_time:
            missed_punch = "BOTH"
        elif not in_time:
            missed_punch = "IN"
        elif not out_time:
            missed_punch = "OUT"

        # Status
        status = record.status or ("Missed Punch" if missed_punch != "-" else "Present")

        remarks, eligible, disable_action = [], False, False

        # Feature enabled check
        if not enable_feature:
            remarks.append("Regularization Disabled")

        # Weekends & holidays
        if exclude_weekends and att_date.weekday() >= 5:
            remarks.append("Weekend")
        if exclude_holidays and is_holiday(emp, att_date):
            remarks.append("Holiday")

        # Leave check
        if frappe.db.exists("Leave Application", {
            "employee": emp,
            "from_date": ["<=", att_date],
            "to_date": [">=", att_date],
            "status": "Approved"
        }):
            remarks.append("On Leave")

        # Hours passed
        hours_passed = hours_since_excluding(att_date, today_dt.date(), emp, exclude_weekends, exclude_holidays)

        # Eligibility
        if enable_feature and not remarks:
            if hours_passed < min_delay_hours:
                remarks.append(f"Wait {min_delay_hours}h")
            elif hours_passed > max_delay_hours:
                remarks.append("Window Expired")
            else:
                # Count approved regularizations
                month_start = att_date.replace(day=1)
                month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
                completed_requests = frappe.db.count("Attendance Regularization", {
                    "employee": emp,
                    "date": ["between", [month_start, month_end]],
                    "workflow_state": "Approved"
                })
                if completed_requests >= max_requests_per_month:
                    disable_action = True
                    remarks.append(f"Monthly limit reached ({max_requests_per_month})")
                else:
                    eligible = True

        # Action
        action_label = "Regularize" if eligible and not disable_action else ("Max Requests Reached" if disable_action else "-")

        data.append({
            "employee": emp,
            "employee_name": employee_name,
            "attendance_date": att_date,
            "shift_start": shift_start or "-",
            "shift_end": shift_end or "-",
            "in_time": in_time or "-",
            "out_time": out_time or "-",
            "working_hours": formatted_working_hours,
            "status": status,
            "missed_punch": missed_punch,
            "regularization_count": completed_requests if 'completed_requests' in locals() else 0,
            "regularization_eligible": "Yes" if eligible and not disable_action else "No",
            "action": action_label,
            "remarks": "; ".join(remarks) if remarks else ""
        })

    return columns, data


# ---------------- Helper Functions ----------------
def is_holiday(employee, chk_date):
    """Check if the date is a holiday for the employee."""
    if not chk_date:
        return False
    holiday_list = frappe.db.get_value("Employee", employee, "holiday_list") or frappe.db.get_single_value("HR Settings", "default_holiday_list")
    if holiday_list:
        return frappe.db.exists("Holiday", {"parent": holiday_list, "holiday_date": chk_date})
    return False


def hours_since_excluding(att_date, current_date, employee, exclude_weekends=True, exclude_holidays=True):
    """Calculate hours passed excluding weekends/holidays."""
    att_date, current_date = getdate(att_date), getdate(current_date)
    if current_date < att_date:
        return 0
    days = 0
    while att_date < current_date:
        if not (exclude_weekends and att_date.weekday() >= 5) and not (exclude_holidays and is_holiday(employee, att_date)):
            days += 1
        att_date += timedelta(days=1)
    return days * 24


def get_shift_from_default_shift(employee):
    """Fetch shift start and end time from Employee's default shift."""
    try:
        default_shift = frappe.db.get_value("Employee", employee, "default_shift")
        if default_shift:
            st = frappe.get_doc("Shift Type", default_shift)
            return (
                st.start_time if st.start_time else "-",
                st.end_time if st.end_time else "-"
            )
    except Exception:
        pass
    return (None, None)


def format_time_only(dt_value):
    """Return only the time (HH:MM) from a datetime string or object."""
    if not dt_value:
        return ""
    try:
        if isinstance(dt_value, str):
            dt_obj = frappe.utils.get_datetime(dt_value)
        else:
            dt_obj = dt_value
        return format_time(dt_obj.time(), "HH:mm")
    except Exception:
        return str(dt_value)

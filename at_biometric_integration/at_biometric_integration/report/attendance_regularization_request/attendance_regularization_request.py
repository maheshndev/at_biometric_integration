# Attendance Regularization Request Report - Updated Logic
import frappe
from datetime import datetime, timedelta, date
from frappe.utils import getdate, format_time


def execute(filters=None):
    filters = frappe._dict(filters or {})

    # ---------------- Load Settings ----------------
    settings = frappe.get_single("Attendance Settings") if frappe.db.exists("DocType", "Attendance Settings") else None

    enable_feature = getattr(settings, "enable_regularization", True) if settings else True
    min_delay_hours = getattr(settings, "regularization_from_hours", 24) or 24
    max_delay_hours = getattr(settings, "regularization_to_hours", 48) or 48
    max_requests_per_month = getattr(settings, "max_requests_per_month", 3) or 3

    min_delay_hours = int(min_delay_hours)
    max_delay_hours = int(max_delay_hours)
    max_requests_per_month = int(max_requests_per_month)

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
        {"fieldname": "remarks", "label": "Remarks", "fieldtype": "Data", "width": 250},
    ]

    data = []

    # ---------------- Build Filters ----------------
    conditions = []
    if filters.get("employee"):
        conditions.append(["employee", "=", filters.employee])

    if filters.get("from_date") and filters.get("to_date"):
        conditions.append(["attendance_date", "between", [filters.from_date, filters.to_date]])
    else:
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
        shift_start, shift_end = get_shift_from_default_shift(emp)

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

        # Missed punch
        missed_punch = "-"
        if not in_time and not out_time:
            missed_punch = "BOTH"
        elif not in_time:
            missed_punch = "IN"
        elif not out_time:
            missed_punch = "OUT"

        status = record.status or ("Missed Punch" if missed_punch != "-" else "Present")
        remarks = []
        eligible = False
        disable_action = False

        # ---------------- Regularization Logic ----------------
        if not enable_feature:
            remarks.append("Regularization Disabled")

        # Check if on leave
        if frappe.db.exists("Leave Application", {
            "employee": emp,
            "from_date": ["<=", att_date],
            "to_date": [">=", att_date],
            "status": "Approved"
        }):
            remarks.append("On Leave")

        # Calculate hours since attendance date
        hours_passed = (today_dt - datetime.combine(att_date, datetime.min.time())).total_seconds() / 3600

        # Get count of approved requests in the same month
        month_start = att_date.replace(day=1)
        month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        completed_requests = frappe.db.count("Attendance Regularization", {
            "employee": emp,
            "date": ["between", [month_start, month_end]],
            "workflow_state": "Approved"
        })

        # Apply new logic
        if enable_feature and "On Leave" not in remarks:
            if hours_passed < min_delay_hours:
                remarks.append(f"Wait for {min_delay_hours} Hours to Regularize")
                disable_action = True
            elif min_delay_hours <= hours_passed <= max_delay_hours:
                eligible = True
                remarks.append("Eligible for Regularization")
            elif hours_passed > max_delay_hours:
                remarks.append(f"{max_delay_hours} Hours Exceeded - Regularization Not Allowed")
                disable_action = True

            # Monthly limit check
            if completed_requests >= max_requests_per_month:
                remarks.append(f"Monthly Limit Reached ({max_requests_per_month})")
                disable_action = True
                eligible = False

        # Set Action button
        if eligible and not disable_action:
            action_label = "Regularize"
        elif disable_action:
            action_label = "Disabled"
        else:
            action_label = "-"

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
            "regularization_count": completed_requests,
            "regularization_eligible": "Yes" if eligible and not disable_action else "No",
            "action": action_label,
            "remarks": "; ".join(remarks) if remarks else ""
        })

    return columns, data


# ---------------- Helper Functions ----------------
def get_shift_from_default_shift(employee):
    try:
        default_shift = frappe.db.get_value("Employee", employee, "default_shift")
        if default_shift:
            st = frappe.get_doc("Shift Type", default_shift)
            return st.start_time or "-", st.end_time or "-"
    except:
        pass
    return "-", "-"


def format_time_only(dt_value):
    if not dt_value:
        return ""
    try:
        dt_obj = frappe.utils.get_datetime(dt_value)
        return format_time(dt_obj.time(), "HH:mm")
    except:
        return str(dt_value)

import frappe
from datetime import datetime, timedelta
from frappe.utils import get_datetime, now_datetime

# helpers expected to exist in your repo (you referenced them before)
from .helpers import get_leave_status, is_holiday, calculate_working_hours

# ------------------
# ASSUMPTIONS / TODO
# - Attendance doc has fields: employee, attendance_date (date), in_time (datetime/time), out_time (datetime/time),
#   working_hours (float), status (Present/Half Day/etc.), shift (name of Shift Type or string).
# - Shift information (if used) is in a doctype called "Shift Type" with fields start_time and end_time (HH:MM or time)
#   If your shift model differs, change get_shift_end_datetime().
# - Attendance Settings single doctype contains the keys you listed (names used exactly as fields).
# - calculate_working_hours(first_checkin, last_checkin) returns float hours.
# ------------------


def get_attendance_settings():
    """Fetch settings from single doctype. Provide defaults when missing."""
    try:
        s = frappe.get_single("Attendance Settings")
    except Exception:
        # Return sensible defaults if the doctype doesn't exist
        return frappe._dict({
            "enable_regularization": False,
            "regularization_from_hours": 0,
            "regularization_to_hours": 24,
            "min_working_hours": 4,
            "checkin_grace_start_minutes": 0,
            "checkout_grace_end_minutes": 0,
            "attendance_grace_start_mins": 0,
            "attendance_grace_end_mins": 0,
        })

    return frappe._dict({
        "enable_regularization": getattr(s, "enable_regularization", False),
        "regularization_from_hours": getattr(s, "regularization_from_hours", 0),
        "regularization_to_hours": getattr(s, "regularization_to_hours", 24),
        "min_working_hours": getattr(s, "min_working_hours", 4),
        "checkin_grace_start_minutes": getattr(s, "checkin_grace_start_minutes", 0),
        "checkout_grace_end_minutes": getattr(s, "checkout_grace_end_minutes", 0),
        "attendance_grace_start_mins": getattr(s, "attendance_grace_start_mins", 0),
        "attendance_grace_end_mins": getattr(s, "attendance_grace_end_mins", 0),
    })


def get_shift_end_datetime(employee, attendance_date, shift_name):
    """
    Try to determine the expected shift end datetime for this employee on attendance_date.
    - First try to read Shift Type (end_time) by name
    - If shift_name absent or Shift Type missing, fall back to using attendance.out_time (if exists)
    - If still missing, assume a default shift end at 18:30 (6:30pm) local date (adjustable)
    """
    # try Shift Type
    try:
        if shift_name:
            # Shift Type might store times as strings or time objects; we try common fields
            shift = frappe.get_doc("Shift Type", shift_name)
            end_time = getattr(shift, "end_time", None) or getattr(shift, "end", None)
            start_time = getattr(shift, "start_time", None) or getattr(shift, "start", None)
            if end_time:
                # combine date + end_time
                dt = get_datetime(f"{attendance_date} {str(end_time)}")
                return dt
    except Exception:
        # no shift found, continue to fallback
        pass

    # fallback: try to use any existing attendance out_time
    att = frappe.get_all("Attendance",
                         filters={"employee": employee, "attendance_date": attendance_date},
                         fields=["out_time"], limit_page_length=1)
    if att and att[0].get("out_time"):
        return get_datetime(att[0].out_time)

    # final fallback: assume 18:30 local time
    fallback = get_datetime(f"{attendance_date} 18:30:00")
    return fallback


def auto_submit_attendance_doc(att_doc, settings):
    """
    Submit a single attendance document if it meets submission criteria.
    Returns True if submitted.
    """
    try:
        # Skip already submitted
        if att_doc.docstatus == 1:
            return False

        # compute working_hours if missing
        working_hours = getattr(att_doc, "working_hours", None)
        if working_hours is None:
            # try to compute from in_time/out_time if available
            if att_doc.in_time and att_doc.out_time:
                working_hours = calculate_working_hours(att_doc.in_time, att_doc.out_time)
            else:
                working_hours = 0.0

        # Rule: require at least min_working_hours
        if working_hours < settings.min_working_hours:
            # Not enough hours to be auto-submitted as Present / Half-day
            return False

        # If reached here, submit
        doc = frappe.get_doc("Attendance", att_doc.name)
        # update working_hours and status to reflect calculation (defensive)
        doc.working_hours = working_hours
        # choose status based on hours (same logic you used earlier)
        doc.status = "Present" if working_hours >= settings.min_working_hours else "Half Day"

        # Submit with ignore permissions to allow scheduler/whitelisted calls to submit
        doc.submit(ignore_permissions=True)
        frappe.db.commit()
        frappe.publish_realtime(event="attendance_auto_submitted", message={"name": doc.name})
        return True
    except Exception as e:
        frappe.log_error(f"Auto-submit error for {getattr(att_doc, 'name', '')}: {e}", "Attendance Auto Submit")
        return False


def auto_submit_due_attendances():
    """
    Find attendance records that are due for auto-submission and submit them.
    Two triggers:
    1) shift end + 4 hours have passed
    2) regularization period ended (using regularization_to_hours from settings)
    This function can be invoked from scheduler periodically (eg: every 30 minutes).
    """
    settings = get_attendance_settings()
    now = now_datetime()

    # query open attendance records (docstatus = 0)
    open_att = frappe.get_all("Attendance", filters={"docstatus": 0}, fields=[
        "name", "employee", "attendance_date", "in_time", "out_time", "working_hours", "shift"
    ])

    submitted_any = []
    for a in open_att:
        try:
            # compute expected shift end datetime
            shift_end_dt = get_shift_end_datetime(a.employee, a.attendance_date, a.get("shift"))

            # condition 1: 4 hours after shift end
            if now >= (shift_end_dt + timedelta(hours=4)):
                # submit if meets working hours rule
                if (a.working_hours or 0) >= settings.min_working_hours:
                    if auto_submit_attendance_doc(frappe._dict(a), settings):
                        submitted_any.append(a.name)
                    continue

            # condition 2: regularization window passed
            if settings.enable_regularization:
                # Interpret regularization_to_hours as hours after shift_end allowed for regularization.
                # Once that window expires, auto-submit if working_hours >= min_working_hours.
                reg_to = float(settings.regularization_to_hours or 0)
                if now >= (shift_end_dt + timedelta(hours=reg_to)):
                    if (a.working_hours or 0) >= settings.min_working_hours:
                        if auto_submit_attendance_doc(frappe._dict(a), settings):
                            submitted_any.append(a.name)
                        continue
        except Exception as e:
            frappe.log_error(f"Error evaluating auto-submit for attendance {a.get('name')}: {e}", "Attendance Auto Submit")

    return submitted_any


# ------------------------
# Realtime processing (when checkins exist)
# ------------------------
def process_attendance_realtime():
    """
    Recreates the attendance records from Employee Checkin table per employee per date (first and last).
    This function:
    - groups checkins by date
    - calculates working_hours using calculate_working_hours()
    - inserts or updates Attendance records (docstatus 0)
    - DOES NOT auto-submit here; returning the list of created/updated attendances for caller to decide.
    """
    employees = frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "default_shift"])
    created_or_updated = []

    for emp in employees:
        try:
            process_employee_attendance_realtime(emp.name, emp.default_shift or "", created_or_updated)
        except Exception as e:
            frappe.log_error(f"{emp.name} attendance error: {e}", "Realtime Attendance Error")

    frappe.db.commit()
    return created_or_updated


def process_employee_attendance_realtime(employee, shift, created_list=None):
    checkins = frappe.get_all(
        "Employee Checkin",
        filters={"employee": employee},
        fields=["name", "time", "log_type"],
        order_by="time asc"
    )

    by_date = {}
    for c in checkins:
        d = get_datetime(c.time).date()
        by_date.setdefault(d, []).append(c)

    for date, daily in by_date.items():
        if not daily:
            continue
        first, last = daily[0], daily[-1]
        hours = calculate_working_hours(first.time, last.time)
        status = "Present" if hours >= 4 else "Half Day"

        existing_name = frappe.db.exists("Attendance", {"employee": employee, "attendance_date": date})
        if existing_name:
            frappe.db.set_value("Attendance", existing_name, {
                "in_time": first.time,
                "out_time": last.time,
                "working_hours": hours,
                "status": status,
                "shift": shift
            })
            if created_list is not None:
                created_list.append(existing_name)
        else:
            doc = frappe.get_doc({
                "doctype": "Attendance",
                "employee": employee,
                "attendance_date": date,
                "shift": shift,
                "in_time": first.time,
                "out_time": last.time,
                "working_hours": hours,
                "status": status
            })
            doc.insert(ignore_permissions=True)
            if created_list is not None:
                created_list.append(doc.name)

    # no commit here: caller should commit once for batch operations


def auto_submit_new_attendances(attendance_names):
    """
    Called after new Attendance docs are created. This checks each new attendance doc
    and auto-submits immediately if it meets the rules (e.g. created after checkins and already
    has enough working hours AND either shift_end+4h already passed or regularization window expired).
    """
    if not attendance_names:
        return []

    settings = get_attendance_settings()
    submitted = []
    for name in attendance_names:
        try:
            doc = frappe.get_doc("Attendance", name)
            # re-use the logic in auto_submit_due_attendances by wrapping doc into a dict
            # We'll check: if now >= shift_end+4h or regularization expired, submit.
            shift_end_dt = get_shift_end_datetime(doc.employee, doc.attendance_date, doc.shift)
            now = now_datetime()

            if now >= (shift_end_dt + timedelta(hours=4)):
                if (doc.working_hours or 0) >= settings.min_working_hours:
                    doc.submit(ignore_permissions=True)
                    submitted.append(name)
                    continue

            if settings.enable_regularization:
                reg_to = float(settings.regularization_to_hours or 0)
                if now >= (shift_end_dt + timedelta(hours=reg_to)):
                    if (doc.working_hours or 0) >= settings.min_working_hours:
                        doc.submit(ignore_permissions=True)
                        submitted.append(name)
                        continue
        except Exception as e:
            frappe.log_error(f"Error in auto_submit_new_attendances for {name}: {e}", "Attendance Auto Submit")

    if submitted:
        frappe.db.commit()
    return submitted

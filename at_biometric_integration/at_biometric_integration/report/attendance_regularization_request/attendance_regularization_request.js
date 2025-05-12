// Attendance Regularization Request - JavaScript

frappe.query_reports["Attendance Regularization Request"] = {
    "filters": [
        {
            "fieldname": "period",
            "label": "Period",
            "fieldtype": "Select",
            "options": "Daily\nWeekly\nMonthly",
            "default": "Daily",
            "reqd": 1,
            "on_change": function() {
                setDefaultDates();
                frappe.query_report.refresh();
            }
        },
        {
            "fieldname": "from_date",
            "label": "From Date",
            "fieldtype": "Date"
        },
        {
            "fieldname": "to_date",
            "label": "To Date",
            "fieldtype": "Date"
        },
        {
            "fieldname": "employee",
            "label": "Employee",
            "fieldtype": "Link",
            "options": "Employee"
        },
        {
            "fieldname": "month",
            "label": "Month",
            "fieldtype": "Select"
        },
        {
            "fieldname": "year",
            "label": "Year",
            "fieldtype": "Select"
        }
    ],

    onload: function(report) {
        setDefaultDates();
        frappe.query_report.refresh();
    },

    formatter: function(value, row, column, data, default_formatter) {
        if (column.fieldname === "action") {
            value = `<button class="btn btn-primary btn-sm" onclick="openAttendanceRegularizationForm('${data.employee}', '${data.employee_name}', '${data.in_time}', '${data.out_time}', '${data.attendance_date}', '${data.working_hours}', '${data.status}')">
                        Regularize
                     </button>`;
            return value;
        }
        return default_formatter(value, row, column, data);
    }
};

// Function to set default dates based on the selected period
function setDefaultDates() {
    const period = frappe.query_report.get_filter_value("period");
    const today = frappe.datetime.get_today();
    let from_date, to_date;

    if (period === "Daily") {
        from_date = today;
        to_date = today;
    } else if (period === "Weekly") {
        const startOfWeek = frappe.datetime.add_days(today, -frappe.datetime.get_day_diff(today, frappe.datetime.week_start(today)));
        const endOfWeek = frappe.datetime.add_days(startOfWeek, 6);
        from_date = startOfWeek;
        to_date = endOfWeek;
    } else if (period === "Monthly") {
        const startOfMonth = frappe.datetime.month_start(today);
        const endOfMonth = frappe.datetime.month_end(today);
        from_date = startOfMonth;
        to_date = endOfMonth;
    }

    frappe.query_report.set_filter_value("from_date", from_date);
    frappe.query_report.set_filter_value("to_date", to_date);
}

// Function to open Attendance Regularization form with pre-filled values
function openAttendanceRegularizationForm(employee, employee_name, in_time, out_time, attendance_date, working_hours, status) {
    frappe.new_doc("Attendance Regularization", {
        employee: employee,
        employee_name: employee_name,
        in_time: in_time,
        out_time: out_time,
        date: attendance_date,
        reason: "Regularization requested via report",
        attendance_status: status
    });
}

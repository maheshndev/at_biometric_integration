frappe.query_reports["Attendance Regularization Request"] = {
    filters: [
        {
            fieldname: "period",
            label: "Period",
            fieldtype: "Select",
            options: "Daily\nWeekly\nMonthly",
            default: "Daily",
            reqd: 1,
            on_change: function () {
                setDefaultDates();
                frappe.query_report.refresh();
            }
        },
        { fieldname: "from_date", label: "From Date", fieldtype: "Date" },
        { fieldname: "to_date", label: "To Date", fieldtype: "Date" },
        { fieldname: "employee", label: "Employee", fieldtype: "Link", options: "Employee" },
        {
            fieldname: "month",
            label: "Month",
            fieldtype: "Select",
            options: "\nJanuary\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember"
        },
        {
            fieldname: "year",
            label: "Year",
            fieldtype: "Select",
            options: "\n2023\n2024\n2025\n2026"
        }
    ],

    // Auto-load report on open
    onload: function (report) {
        setDefaultDates();
        frappe.query_report.refresh();
    },

    // Refresh on reload as well
    onrefresh: function (report) {
        if (!frappe.query_report.get_filter_value("from_date") || !frappe.query_report.get_filter_value("to_date")) {
            setDefaultDates();
        }
    },

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (!data) return value;

        switch (column.fieldname) {
            case "action":
                if (data.action === "Regularize") {
                    return `
                        <button class="btn btn-primary btn-sm"
                            style="font-weight:500;"
                            onclick="openAttendanceRegularizationForm(
                                '${data.employee}',
                                '${data.employee_name}',
                                '${data.attendance_date}',
                                '${data.shift_start}',
                                '${data.shift_end}',
                                '${data.in_time}',
                                '${data.out_time}',
                                '${data.status}'
                            )">
                            Regularize
                        </button>`;
                } else if (data.action === "Max Requests Reached") {
                    return `<button class="btn btn-secondary btn-sm" disabled>Max Limit</button>`;
                } else {
                    return `<button class="btn btn-light btn-sm" disabled>-</button>`;
                }

            case "regularization_eligible":
                return `<span style="color:${data.regularization_eligible === "Yes" ? "green" : "red"};font-weight:600;">${value}</span>`;

            case "missed_punch":
                if (data.missed_punch !== "-") {
                    return `<span style="color:orange;font-weight:600;">${value}</span>`;
                }
                break;

            case "remarks":
                if (data.remarks && data.remarks.includes("Alert")) {
                    return `<span style="color:#0055aa;">${data.remarks}</span>`;
                }
                break;
        }

        return value;
    }
};

// ---------------- Helper Functions ---------------- //

function setDefaultDates() {
    const period = frappe.query_report.get_filter_value("period");
    const today = frappe.datetime.get_today();
    let from_date = today;
    let to_date = today;

    if (period === "Weekly") {
        from_date = frappe.datetime.week_start(today);
        to_date = frappe.datetime.week_end(today);
    } else if (period === "Monthly") {
        from_date = frappe.datetime.month_start(today);
        to_date = frappe.datetime.month_end(today);
    }

    frappe.query_report.set_filter_value("from_date", from_date);
    frappe.query_report.set_filter_value("to_date", to_date);
}

function openAttendanceRegularizationForm(employee, employee_name, attendance_date, shift_start, shift_end, in_time, out_time, status) {
    frappe.new_doc("Attendance Regularization", {
        employee: employee,
        employee_name: employee_name,
        date: attendance_date,
        shift_start: shift_start,
        shift_end: shift_end,
        in_time: in_time,
        out_time: out_time,
        attendance_status: status,
        reason: "Requested via Attendance Regularization Report"
    });
}

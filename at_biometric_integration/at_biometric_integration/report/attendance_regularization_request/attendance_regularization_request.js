// ---------------- Attendance Regularization Request Report ---------------- //
frappe.query_reports["Attendance Regularization Request"] = {
    filters: [
        {
            fieldname: "period",
            label: "Period",
            fieldtype: "Select",
            options: ["Daily", "Weekly", "Monthly"],
            default: "Daily",
            reqd: 1,
            on_change: function () {
                setDefaultDates();
                frappe.query_report.refresh();
            },
        },
        { fieldname: "from_date", label: "From Date", fieldtype: "Date" },
        { fieldname: "to_date", label: "To Date", fieldtype: "Date" },
        { fieldname: "employee", label: "Employee", fieldtype: "Link", options: "Employee" },
        {
            fieldname: "month",
            label: "Month",
            fieldtype: "Select",
            options: ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
        },
        {
            fieldname: "year",
            label: "Year",
            fieldtype: "Select",
            options: ["", "2023", "2024", "2025", "2026"],
        },
    ],

    onload: function (report) {
        setDefaultDates();
        frappe.query_report.refresh();

        // Attach global click handler (to ensure button clicks work)
        attachRegularizeButtonHandler();
    },

    onrefresh: function (report) {
        if (!frappe.query_report.get_filter_value("from_date") || !frappe.query_report.get_filter_value("to_date")) {
            setDefaultDates();
        }

        // Re-attach handlers every refresh
        setTimeout(() => attachRegularizeButtonHandler(), 300);
    },

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (!data) return value;

        switch (column.fieldname) {
            case "action":
                if (data.action === "Regularize") {
                    const buttonId = `reg-btn-${data.employee}-${data.attendance_date}`;
                    return `<button id="${buttonId}" class="btn btn-primary btn-sm reg-btn"
                        data-employee='${data.employee}'
                        data-employee_name='${data.employee_name}'
                        data-date='${data.attendance_date}'
                        data-shift_start='${data.shift_start}'
                        data-shift_end='${data.shift_end}'
                        data-in_time='${data.in_time}'
                        data-out_time='${data.out_time}'
                        data-status='${data.status}'
                        style="font-weight:500;">
                        Regularize
                    </button>`;
                } else if (data.action === "Disabled") {
                    return `<button class="btn btn-secondary btn-sm" disabled>Disabled</button>`;
                } else {
                    return `<button class="btn btn-light btn-sm" disabled>-</button>`;
                }

            case "regularization_eligible":
                const eligibleColor = data.regularization_eligible === "Yes" ? "green" : "red";
                return `<span style="color:${eligibleColor};font-weight:600;">${value}</span>`;

            case "missed_punch":
                if (data.missed_punch !== "-") {
                    return `<span style="color:orange;font-weight:600;">${value}</span>`;
                }
                break;

            case "remarks":
                let color = "#000";
                if (data.remarks.includes("Wait")) color = "#f39c12";
                else if (data.remarks.includes("Eligible")) color = "#27ae60";
                else if (data.remarks.includes("Exceeded") || data.remarks.includes("Limit")) color = "#e74c3c";
                return `<span style="color:${color};font-weight:500;">${frappe.utils.escape_html(data.remarks)}</span>`;
        }

        return value;
    },
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

// ---------------- Button Handler ---------------- //

function attachRegularizeButtonHandler() {
    // Prevent duplicate bindings
    $(document).off("click", ".reg-btn");

    $(document).on("click", ".reg-btn", function () {
        const btn = $(this);
        openAttendanceRegularizationForm(
            btn.data("employee"),
            btn.data("employee_name"),
            btn.data("date"),
            btn.data("shift_start"),
            btn.data("shift_end"),
            btn.data("in_time"),
            btn.data("out_time"),
            btn.data("status")
        );
    });
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
        reason: "Requested via Attendance Regularization Report",
    });
}

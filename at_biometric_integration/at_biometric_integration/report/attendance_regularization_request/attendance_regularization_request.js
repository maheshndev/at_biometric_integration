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
                updateVisibility();
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
        // Fetch metadata (months and years) from the backend
        frappe.call({
            method: "frappe.desk.query_report.run",
            args: {
                report_name: "Attendance Regularization Request",
                filters: {}
            },
            callback: function(response) {
                if (response.message) {
                    let metadata = response.message.metadata;

                    // Populate the "Month" filter
                    let monthField = frappe.query_report.get_filter("month");
                    const monthNames = [
                        "January", "February", "March", "April", "May", "June",
                        "July", "August", "September", "October", "November", "December"
                    ];
                    monthField.df.options = metadata.months
                        .map(m => monthNames[parseInt(m) - 1])
                        .join("\n");
                    monthField.refresh();

                    // Populate the "Year" filter
                    let yearField = frappe.query_report.get_filter("year");
                    yearField.df.options = metadata.years.join("\n");
                    yearField.refresh();
                }
            }
        });

        updateVisibility();
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

function updateVisibility() {
    let period = frappe.query_report.get_filter_value("period");
    let month = frappe.query_report.get_filter("month");
    let year = frappe.query_report.get_filter("year");

    if (period === "Monthly") {
        month.df.hidden = 0;
        year.df.hidden = 0;
    } else {
        month.df.hidden = 1;
        year.df.hidden = 1;
    }

    month.refresh();
    year.refresh();
}

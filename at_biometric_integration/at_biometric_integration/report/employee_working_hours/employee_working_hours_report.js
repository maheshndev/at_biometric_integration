frappe.query_reports["Employee Daily Working Hours"] = {
    filters: [
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee",
            reqd: 0
        },
        {
            fieldname: "log_date",
            label: __("Date"),
            fieldtype: "Date",
            reqd: 0,
            default: frappe.datetime.get_today()
        }
    ],
    onload: function(report) {
        report.page.add_inner_button(__("Reload"), function() {
            report.refresh();
        });
    }
};

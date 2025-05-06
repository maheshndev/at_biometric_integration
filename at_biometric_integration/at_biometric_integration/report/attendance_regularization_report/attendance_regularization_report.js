frappe.query_reports["Attendance Regularization Report"] = {
    onload: function (report) {
        // Add a custom button to handle regularization
        report.page.add_inner_button(__("Regularize Attendance"), function () {
            let selected_rows = frappe.query_report.get_selected_rows();
            if (selected_rows.length === 0) {
                frappe.msgprint(__("Please select at least one row to regularize attendance."));
                return;
            }

            selected_rows.forEach(row => {
                if (!row.employee || !row.date) {
                    frappe.msgprint(__("Selected row is missing required fields (employee or date)."));
                    return;
                }

                frappe.call({
                    method: "at_biometric_integration.at_biometric_integration.report.attendance_regularization_report.attendance_regularization_report.regularize_action",
                    args: {
                        employee: row.employee,
                        date: row.date
                    },
                    callback: function (response) {
                        if (response.message) {
                            frappe.msgprint(response.message);
                        } else if (response.error) {
                            frappe.msgprint({
                                title: __("Error"),
                                indicator: "red",
                                message: response.error
                            });
                        }
                    }
                });
            });
        });
    }
};


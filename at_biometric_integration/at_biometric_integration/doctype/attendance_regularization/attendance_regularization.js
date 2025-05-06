frappe.ui.form.on("Attendance Regularization", {
    refresh: function(frm) {
        frm.add_custom_button(__('Regularize Attendance'), function() {
            frappe.prompt([
                {
                    label: 'Employee',
                    fieldname: 'employee',
                    fieldtype: 'Link',
                    options: 'Employee',
                    reqd: 1
                },
                {
                    label: 'Date',
                    fieldname: 'date',
                    fieldtype: 'Date',
                    reqd: 1
                }
            ], function(values) {
                frappe.call({
                    method: 'at_biometric_integration.at_biometric_integration.doctype.attendance_regularization.attendance_regularization.regularize_action',
                    args: {
                        employee: values.employee,
                        date: values.date
                    },
                    callback: function(response) {
                        if (response.message === "Attendance Regularized") {
                            frappe.msgprint(__('Attendance has been regularized successfully.'));
                        } else {
                            frappe.msgprint(__('Failed to regularize attendance.'));
                        }
                    }
                });
            }, __('Regularize Attendance'), __('Submit'));
        });
    }
});

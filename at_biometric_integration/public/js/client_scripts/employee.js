frappe.ui.form.on('Employee', {
    refresh: function(frm) {
        frm.add_custom_button(__('Sync Attendance'), function() {
            frappe.call({
                method: "at_biometric_integration.api.sync_biometric_attendance",
                args: { employee: frm.doc.name },
                callback: function(response) {
                    frappe.msgprint(__('Attendance Synced Successfully'));
                    frm.reload_doc();
                }
            });
        }, __("Actions"));
    }
});

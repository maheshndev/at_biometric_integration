// frappe.ui.form.on('Employee Checkin', {
//     refresh: function(frm) {
//         frm.add_custom_button(__('Sync All Attendance'), function() {
//             frappe.call({
//                 method: "at_biometric_integration.api.sync_biometric_attendance",
//                 callback: function(response) {
//                     frappe.msgprint(__('All Employees\' Attendance Synced Successfully'));
//                     frm.reload_doc();
//                 }
//             });
//         }, __("Actions"));
//     }
// });

frappe.listview_settings['Employee Checkin'] = {
    onload: function(listview) {
        listview.page.add_inner_button(__('Sync All Attendance'), function() {
            frappe.call({
                method: "at_biometric_integration.at_biometric_integration.api.sync_biometric_attendance",
                freeze: true,
                callback: function(r) {
                    if (!r.exc) {
                        frappe.msgprint(__("Attendance Sync Successful!"));
                        listview.refresh();
                    }
                }
            });
        });
    } 
};

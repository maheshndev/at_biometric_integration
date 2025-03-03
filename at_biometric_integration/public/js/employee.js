// frappe.ui.form.on('Employee', {
//     refresh: function(frm) {
//         frm.add_custom_button(__('Sync Attendance'), function() {
//             frappe.call({
//                 method: "at_biometric_integration.at_biometric_integration.utils.fetch_and_upload_attendance",
//                 // args: { employee: frm.doc.name },
//                 callback: function(response) {
//                     frappe.msgprint(__(response.message));
//                     frm.reload_doc();
//                 }
//             });
//         });
//     }
// });

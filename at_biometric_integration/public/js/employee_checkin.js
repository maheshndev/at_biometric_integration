
frappe.listview_settings['Employee Checkin'] = {
    onload: function(listview) {
        listview.page.add_inner_button(__('Sync Biometric Data'), function() {
            frappe.msgprint({
                title: __('Wait'),
                message: __('<b>Wait: </b> Sync in background progress ....  <br><br>'),
                indicator: 'blue'
            });
            setTimeout(() => {
                frappe.hide_msgprint();
            }, 10000);
            frappe.call({
                method: "at_biometric_integration.at_biometric_integration.utils.fetch_and_upload_attendance",
                callback: function(response) {
                    if (response.message) {
                        let msg = "";
                        if (response.message.success.length > 0) {
                            msg += `<b>Success: </b> ${response.message.success.join('<br>')}<br><br>`;
                        }
                        if (response.message.errors.length > 0) {
                            msg += `<b>Errors: </b> ${response.message.errors.join('<br>')}`;
                        }
                        frappe.msgprint(__(msg));
                    }
                }
            });
        }).addClass("btn-secondary");
        listview.page.add_inner_button(__('Mark Attendance'), function() {
            frappe.msgprint({
                title: __('Wait'),
                message: __('<b>Wait: </b>Mark Attendance in progress ....  <br><br>'),
                indicator: 'blue'
            });
            setTimeout(() => {
                frappe.hide_msgprint();
            }, 5000);
            frappe.call({
                method: "at_biometric_integration.at_biometric_integration.utils.mark_attendance",
                callback: function(response) {
                    if (response.message) {
                        let msg = "";
                        if (response.message.success.length > 0) {
                            msg += `<b>Success: </b> ${response.message.success.join('<br>')}<br><br>`;
                        }
                        if (response.message.errors.length > 0) {
                            msg += `<b>Errors: </b> ${response.message.errors.join('<br>')}`;
                        }
                        frappe.msgprint(__(msg));
                    }
                }
            });
        }).addClass("btn-secondary");

    }
};



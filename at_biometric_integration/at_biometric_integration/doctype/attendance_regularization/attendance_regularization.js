frappe.ui.form.on("Attendance Regularization", {
    refresh: function(frm) {
        // Add custom button to validate check-in/out records
        frm.add_custom_button("Validate Checkin/Out", function() {
            validate_checkin_out(frm);
        });

        // Disable time fields if the document is not Draft or Rejected
        if (["Approved", "Rejected", "Cancelled"].includes(frm.doc.status)) {
            frm.set_df_property("in_time", "read_only", 1);
            frm.set_df_property("out_time", "read_only", 1);
        } else {
            frm.set_df_property("in_time", "read_only", 0);
            frm.set_df_property("out_time", "read_only", 0);
        }
    },

    in_time: function(frm) {
        update_attendance_status(frm);
    },

    out_time: function(frm) {
        update_attendance_status(frm);
    }
});

// Function to automatically update attendance status
function update_attendance_status(frm) {
    if (frm.doc.in_time && frm.doc.out_time) {
        frm.set_value("attendance_status", "Present");
    } else if (!frm.doc.in_time && !frm.doc.out_time) {
        frm.set_value("attendance_status", "Absent");
    } else if (frm.doc.in_time || frm.doc.out_time) {
        frm.set_value("attendance_status", "Partial");
    } else {
        frm.set_value("attendance_status", "");
    }
}

// Function to validate if check-in/out records already exist
function validate_checkin_out(frm) {
    if (!frm.doc.employee || !frm.doc.date) {
        frappe.msgprint("Please enter Employee and Date.");
        return;
    }

    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Employee Checkin",
            filters: {
                employee: frm.doc.employee,
                time: [">=", frm.doc.date + " 00:00:00", "<=", frm.doc.date + " 23:59:59"]
            },
            fields: ["name", "log_type", "time"]
        },
        callback: function(response) {
            if (response.message.length > 0) {
                let message = "Existing Checkins:<br>";
                response.message.forEach(checkin => {
                    message += `- ${checkin.log_type} at ${checkin.time}<br>`;
                });
                frappe.msgprint(message);
            } else {
                frappe.msgprint("No existing check-in/out records found for this date.");
            }
        }
    });
}

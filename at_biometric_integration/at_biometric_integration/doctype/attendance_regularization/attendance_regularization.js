frappe.ui.form.on("Attendance Regularization", {
    employee(frm) {
        if (frm.doc.employee) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Employee",
                    filters: { name: frm.doc.employee },
                    fieldname: ["employee_name"]
                },
                callback(r) {
                    frm.set_value("employee_name", r.message.employee_name);
                }
            });
        }
    },
    date(frm) {
        if (frm.doc.date) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Attendance",
                    filters: {
                        employee: frm.doc.employee,
                        attendance_date: frm.doc.date
                    },
                    fieldname: ["attendance_status"]
                },
                callback(r) {
                    if (r.message) {
                        frm.set_value("attendance_status", r.message.attendance_status);
                    }
                }
            });
        }
    },
    in_time(frm) {
        if (frm.doc.in_time && frm.doc.out_time) {
            // Ensure that in-time is before out-time
            if (frm.doc.in_time >= frm.doc.out_time) {
                frappe.throw("In Time must be before Out Time.");
            }
        }
    },
    out_time(frm) {
        if (frm.doc.in_time && frm.doc.out_time) {
            // Ensure that out-time is after in-time
            if (frm.doc.out_time <= frm.doc.in_time) {
                frappe.throw("Out Time must be after In Time.");
            }
        }
    }
});

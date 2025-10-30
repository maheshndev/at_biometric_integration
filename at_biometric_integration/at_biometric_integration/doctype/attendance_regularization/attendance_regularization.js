// ---------------- List View Settings ----------------
frappe.listview_settings['Attendance Regularization'] = {
    onload(listview) {
        // Only apply for Employee role
        if (!frappe.user.has_role("Employee")) return;

        // Get Attendance Settings
        frappe.db.get_value("Attendance Settings", null, ["enable_regularization", "max_requests_per_month"])
            .then(({ message }) => {
                if (!message || !message.enable_regularization) return;

                const max_requests = message.max_requests_per_month || 3;
                const start_date = frappe.datetime.month_start(frappe.datetime.get_today());
                const end_date = frappe.datetime.month_end(frappe.datetime.get_today());

                // Count approved Attendance Regularizations for the current month
                frappe.db.count("Attendance Regularization", {
                    filters: {
                        employee: frappe.session.user,
                        workflow_state: "Approved By HR",
                        date: ["between", [start_date, end_date]]
                    }
                }).then(count => {
                    if (count >= max_requests) {
                        // Disable "New" button
                        listview.page.set_primary_action(null);

                        frappe.msgprint({
                            title: "Monthly Limit Reached",
                            message: `You have already reached the maximum limit of ${max_requests} approved Attendance Regularizations for this month. You cannot create new ones until next month.`,
                            indicator: "orange"
                        });
                    }
                });
            });
    }
};

// ---------------- Form Script ----------------
frappe.ui.form.on("Attendance Regularization", {
    refresh(frm) {
        // Add Validate Checkin/Out button for employees only
        if (frappe.user.has_role("Employee")) {
            frm.add_custom_button("Validate Checkin/Out", () => validate_checkin_out(frm));
        }

        // Disable in/out fields if workflow is approved or rejected
        const read_only = ["Approved By HR", "Rejected By HR"].includes(frm.doc.workflow_state);
        frm.set_df_property("in_time", "read_only", read_only);
        frm.set_df_property("out_time", "read_only", read_only);

        // Apply role restrictions
        apply_role_restrictions(frm);

        // Check monthly limit for selected employee
        if (frm.doc.employee) check_employee_monthly_limit(frm);
    },

    employee(frm) {
        if (frm.doc.employee) check_employee_monthly_limit(frm);
    },

    validate(frm) {
        return enforce_regularization_limit(frm);
    },

    in_time(frm) { update_attendance_status(frm); },
    out_time(frm) { update_attendance_status(frm); },
});

// ---------------- Check Employee Monthly Limit ----------------
function check_employee_monthly_limit(frm) {
    frappe.db.get_value("Attendance Settings", null, ["enable_regularization", "max_requests_per_month"])
        .then(({ message }) => {
            if (!message || !message.enable_regularization) return;

            const max_requests = message.max_requests_per_month || 3;
            const start = frappe.datetime.month_start(frappe.datetime.get_today());
            const end = frappe.datetime.month_end(frappe.datetime.get_today());

            frappe.db.count("Attendance Regularization", {
                filters: {
                    employee: frm.doc.employee,
                    workflow_state: "Approved By HR",
                    date: ["between", [start, end]]
                }
            }).then(count => {
                if (count >= max_requests) {
                    frappe.msgprint({
                        title: "Monthly Limit Reached",
                        message: `This employee already has ${count} approved Attendance Regularizations this month. Maximum allowed is ${max_requests}.`,
                        indicator: "orange"
                    });
                    frm.disable_save();
                } else {
                    frm.enable_save();
                }
            });
        });
}

// ---------------- Enforce Monthly Limit Before Save ----------------
function enforce_regularization_limit(frm) {
    return new Promise((resolve, reject) => {
        if (!frm.doc.employee || !frm.doc.date) {
            frappe.msgprint("Please select Employee and Date before saving.");
            reject();
            return;
        }

        frappe.db.get_value("Attendance Settings", null, ["enable_regularization", "max_requests_per_month"])
            .then(({ message }) => {
                if (!message || !message.enable_regularization) return resolve();

                const max_requests = message.max_requests_per_month || 3;
                const start = frappe.datetime.month_start(frm.doc.date);
                const end = frappe.datetime.month_end(frm.doc.date);

                frappe.db.count("Attendance Regularization", {
                    filters: {
                        employee: frm.doc.employee,
                        workflow_state: "Approved By HR",
                        date: ["between", [start, end]],
                    }
                }).then(count => {
                    if (count >= max_requests) {
                        frappe.msgprint({
                            title: "Limit Exceeded",
                            message: `You have already submitted ${count} approved Attendance Regularizations this month. Maximum allowed is ${max_requests}.`,
                            indicator: "red"
                        });
                        frm.disable_save();
                        frappe.validated = false;
                        reject();
                    } else resolve();
                });
            });
    });
}

// ---------------- Attendance Status Update ----------------
function update_attendance_status(frm) {
    const { in_time, out_time } = frm.doc;
    let status = "";
    if (in_time && out_time) status = "Present";
    else if (!in_time && !out_time) status = "Absent";
    else status = "Partial";
    frm.set_value("attendance_status", status);
}

// ---------------- Validate Checkin/Out ----------------
function validate_checkin_out(frm) {
    if (!frm.doc.employee || !frm.doc.date) {
        frappe.msgprint("Please enter Employee and Date.");
        return;
    }

    frappe.db.get_list("Employee Checkin", {
        filters: {
            employee: frm.doc.employee,
            time: ["between", [frm.doc.date + " 00:00:00", frm.doc.date + " 23:59:59"]],
        },
        fields: ["log_type", "time"]
    }).then(records => {
        if (records.length) {
            const msg = records.map(c => `- ${c.log_type} at ${frappe.datetime.str_to_user(c.time)}`).join("<br>");
            frappe.msgprint(`Existing Checkins:<br>${msg}`);
        } else {
            frappe.msgprint("No existing check-in/out records found for this date.");
        }
    });
}


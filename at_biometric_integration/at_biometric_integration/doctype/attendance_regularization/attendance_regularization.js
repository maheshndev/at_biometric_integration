// -------------------- Attendance Regularization Client Script --------------------
frappe.ui.form.on("Attendance Regularization", {
    onload: async function (frm) {
        // Make fields read-only when Approved or Rejected
        const read_only = ["Approved By HR", "Rejected By HR"].includes(frm.doc.workflow_state);
        frm.set_df_property("in_time", "read_only", read_only);
        frm.set_df_property("out_time", "read_only", read_only);

        // Auto-set employee if current user is Employee and employee not filled
        if (frappe.user.has_role("Employee") && !frm.doc.employee) {
            const res = await frappe.db.get_value("Employee", { user_id: frappe.session.user }, "name");
            if (res?.message?.name) {
                frm.set_value("employee", res.message.name);
            }
        }

        // Run monthly check and system checkins if both available
        if (frm.doc.employee && frm.doc.date) {
            await check_employee_monthly_limit(frm);
            fetch_system_checkin_times(frm);
        }
    },

    refresh: async function (frm) {
        if (frm.doc.employee && frm.doc.date) {
            await check_employee_monthly_limit(frm);
            fetch_system_checkin_times(frm);
        }
    },

    employee: async function (frm) {
        if (frm.doc.employee && frm.doc.date) {
            await check_employee_monthly_limit(frm);
            fetch_system_checkin_times(frm);
        }
    },

    date: async function (frm) {
        if (frm.doc.employee && frm.doc.date) {
            await check_employee_monthly_limit(frm);
            fetch_system_checkin_times(frm);
        }
    },

    validate: function (frm) {
        // Block saving if limit exceeded
        if (frm.doc.__disable_save_by_limit) {
            frappe.validated = false;
            frappe.msgprint({
                title: "Save prevented",
                message: "You have reached the monthly Attendance Regularization limit.",
                indicator: "red"
            });
        }
    }
});

// -------------------- Check Monthly Limit --------------------
async function check_employee_monthly_limit(frm) {
    const settings_res = await frappe.db.get_value("Attendance Settings", null, ["enable_regularization", "max_requests_per_month"]);
    const settings = settings_res?.message || {};
    const enabled = cint(settings.enable_regularization);
    const max_requests = settings.max_requests_per_month || 3;

    // Skip if feature disabled
    if (!enabled) {
        frm.__disable_save_by_limit = false;
        frm.enable_save();
        frm.set_intro("");
        return;
    }

    const employee_to_check = frm.doc.employee;
    if (!employee_to_check) return;

    const date_to_check = frm.doc.date || frappe.datetime.get_today();
    const start = frappe.datetime.month_start(date_to_check);
    const end = frappe.datetime.month_end(date_to_check);

    // Count approved and submitted records in current month
    const count = await frappe.db.count("Attendance Regularization", {
        filters: {
            employee: employee_to_check,
            docstatus: 1,
            workflow_state: "Approved By HR",
            date: ["between", [start, end]]
        }
    });

    if (count >= max_requests) {
        // Show warning and disable save
        frappe.msgprint({
            title: "Monthly Limit Reached",
            message: `⚠️ <b>${employee_to_check}</b> already has <b>${count}</b> approved Attendance Regularizations this month (limit: ${max_requests}). You cannot create more for this month.`,
            indicator: "red"
        });

        frm.__disable_save_by_limit = true;
        frm.disable_save();
        frm.set_intro("You have reached the monthly Attendance Regularization limit.", "red");

        // Hide save/submit buttons visually
        if (frm.page?.hide_save_button) frm.page.hide_save_button();
        if (frm.page?.hide_actions_menu_item) frm.page.hide_actions_menu_item("Submit");
    } else {
        // Enable saving again if under limit
        frm.__disable_save_by_limit = false;
        frm.enable_save();
        frm.set_intro("");
        if (frm.page?.show_save_button) frm.page.show_save_button();
    }
}

// -------------------- Fetch System Checkin Times --------------------
function fetch_system_checkin_times(frm) {
    if (!frm.doc.employee || !frm.doc.date) {
        frm.set_value("system_in_time", null);
        frm.set_value("system_out_time", null);
        return;
    }

    const start_time = `${frm.doc.date} 00:00:00`;
    const end_time = `${frm.doc.date} 23:59:59`;

    frappe.db.get_list("Employee Checkin", {
        filters: {
            employee: frm.doc.employee,
            time: ["between", [start_time, end_time]]
        },
        fields: ["time"],
        order_by: "time asc",
        limit: 1000
    }).then(records => {
        if (!records?.length) {
            frm.set_value("system_in_time", null);
            frm.set_value("system_out_time", null);
            return;
        }

        const first = records[0].time;
        const last = records[records.length - 1].time;

        const extract_time = (dt) => {
            if (!dt) return null;
            if (dt.includes(" ")) return dt.split(" ")[1].split(".")[0];
            const m = dt.match(/T?(\d{2}:\d{2}:\d{2})/);
            return m ? m[1] : null;
        };

        frm.set_value("system_in_time", extract_time(first));
        frm.set_value("system_out_time", extract_time(last));
    }).catch(err => {
        console.error("Error fetching Employee Checkin:", err);
        frm.set_value("system_in_time", null);
        frm.set_value("system_out_time", null);
    });
}

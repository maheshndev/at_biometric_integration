frappe.query_reports["Attendance Regularization Request"] = {
    "filters": {
      "period": {
        "label": __("Period"),
        "fieldtype": "Select",
        "options": ["Daily", "Weekly", "Monthly"],
        "default": "Daily"
      },
      "month": {
        "label": __("Month"),
        "fieldtype": "Date"
      },
      "from_date": {
        "label": __("From Date"),
        "fieldtype": "Date"
      },
      "to_date": {
        "label": __("To Date"),
        "fieldtype": "Date"
      }
    },
  
    onload: function(report) {
      report.page.set_title(__('Attendance Regularization Request'));
    },
  
    refresh: function(report) {
      // Logic to refresh the report if needed
    }
  };
  
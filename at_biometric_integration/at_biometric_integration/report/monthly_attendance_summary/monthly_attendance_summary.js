frappe.query_reports["Monthly Attendance Summary"] = {
  filters: [
    {
      fieldname: "month",
      label: "Month",
      fieldtype: "Select",
      options: [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
      ].join("\n"),
      reqd: 1,
      on_change: function () {
        setDatesFromMonthYear();
        frappe.query_report.refresh();
      }
    },
    {
      fieldname: "year",
      label: "Year",
      fieldtype: "Select",
      on_change: function () {
        setDatesFromMonthYear();
        frappe.query_report.refresh();
      }
    },
    {
      fieldname: "from_date",
      label: "From Date",
      fieldtype: "Date"
    },
    {
      fieldname: "to_date",
      label: "To Date",
      fieldtype: "Date"
    },
    {
      fieldname: "employee",
      label: "Employee",
      fieldtype: "Link",
      options: "Employee"
    },
    {
      fieldname: "company",
      label: "Company",
      fieldtype: "Link",
      options: "Company"
    }
  ],

  onload: function (report) {
    updateYearOptions();
    setCurrentMonthAndYear();
  }
};

// Format date as "YYYY-MM-DD"
function formatDateToYYYYMMDD(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function setDatesFromMonthYear() {
  const month = frappe.query_report.get_filter_value("month");
  const year = frappe.query_report.get_filter_value("year");

  if (!month || !year) return;

  const monthMap = {
    "January": 0, "February": 1, "March": 2, "April": 3,
    "May": 4, "June": 5, "July": 6, "August": 7,
    "September": 8, "October": 9, "November": 10, "December": 11
  };

  const start = new Date(year, monthMap[month], 1);
  const end = new Date(year, monthMap[month] + 1, 0);

  frappe.query_report.set_filter_value("from_date", formatDateToYYYYMMDD(start));
  frappe.query_report.set_filter_value("to_date", formatDateToYYYYMMDD(end));
}

function setCurrentMonthAndYear() {
  const currentDate = new Date();
  const currentMonth = currentDate.toLocaleString('default', { month: 'long' });
  const currentYear = currentDate.getFullYear();

  frappe.query_report.get_filter("month").set_input(currentMonth);
  frappe.query_report.get_filter("year").set_input(currentYear.toString());

  setDatesFromMonthYear();
  frappe.query_report.refresh();
}

function updateYearOptions() {
  const yearField = frappe.query_report.get_filter("year");

  frappe.call({
    method: "frappe.client.get_list",
    args: {
      doctype: "Attendance",
      fields: ["YEAR(attendance_date) as year"],
      group_by: "YEAR(attendance_date)",
      order_by: "year desc"
    },
    callback: function (response) {
      if (response && response.message) {
        const currentYear = new Date().getFullYear();
        const years = response.message
          .map(entry => entry.year && entry.year.toString())
          .filter(Boolean)
          .filter(year => parseInt(year) >= currentYear - 5);

        if (years.length) {
          yearField.df.options = years.join("\n");
          yearField.set_input(currentYear.toString());
          yearField.refresh();
        }
      }
    }
  });
}

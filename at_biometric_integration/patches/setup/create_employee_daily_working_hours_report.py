import frappe

def execute():
    if not frappe.db.exists("Report", "Employee Daily Working Hours"):
        report = frappe.get_doc({
            "doctype": "Report",
            "report_name": "Employee Daily Working Hours",
            "ref_doctype": "Employee Checkin",
            "report_type": "Query Report",
            "is_standard": "No",
            "module": "At Biometric Integration"
        })
        report.insert()

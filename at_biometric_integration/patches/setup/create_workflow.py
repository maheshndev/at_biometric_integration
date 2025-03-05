import frappe
import json

def execute():
    if not frappe.db.exists("Workflow", "Attendance Regularization Approval"):
        with open(frappe.get_app_path("at_biometric_integration", "fixtures/workflows/attendance_regularization_approval.json")) as f:
            workflow_data = json.load(f)
            workflow = frappe.get_doc(workflow_data)
            workflow.insert(ignore_permissions=True)
            frappe.db.commit()
        frappe.msgprint("Attendance Regularization Approval Workflow has been created successfully.", alert=True)

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate
from at_biometric_integration.at_biometric_integration.doctype.attendance_regularization.process_regularization import process_regularization

class AttendanceRegularization(Document):
    def on_submit(self):
        """
        Trigger when the regularization request is submitted.
        If approved, process regularization by creating missing check-ins.
        """
        if self.status == "Approved":
            process_regularization(self)
        elif self.status == "Rejected":
            frappe.msgprint(f"Regularization for {self.employee_name} on {self.date} has been rejected.")
            
    def validate(self):
        """
        Validation method to ensure all required fields are provided.
        """
        if not (self.employee and self.date and self.in_time and self.out_time):
            frappe.throw("Employee, Date, In Time, and Out Time are required.")

from frappe.tests.utils import FrappeTestCase
import frappe
class TestAttendanceRegularization(FrappeTestCase):
   def test_generate_attendance(self):
        # Create a test Attendance Regularization document
        doc = frappe.get_doc({
            "doctype": "Attendance Regularization",
            "employee": "EMP-0001",
            "date": "2025-05-06",
            "workflow_state": "Approved"
        })
        doc.insert()
        doc.submit()

        # Check if Attendance was created
        attendance = frappe.get_doc("Attendance", {
            "employee": "EMP-0001",
            "attendance_date": "2025-05-06"
        })
        self.assertEqual(attendance.status, "Present")

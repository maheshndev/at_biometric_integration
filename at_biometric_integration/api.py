import frappe

@frappe.whitelist()
def test_new():
    return {"message": "Hello from test_new!"}


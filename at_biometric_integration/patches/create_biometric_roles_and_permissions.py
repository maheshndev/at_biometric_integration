import frappe

def execute():
    # Define roles and doctypes
    roles = ["Biometric Integration Manager", "Biometric Integration User"]
    doctypes = [
        "Attendance Regularization",
        "Attendance Settings",
        "Biometric Device Settings"
    ]
    permissions = ["read", "write", "create", "delete", "submit", "cancel", "amend"]

    # 1️⃣ Create Roles if not exist
    for role_name in roles:
        if not frappe.db.exists("Role", role_name):
            role = frappe.new_doc("Role")
            role.role_name = role_name
            role.desk_access = 1
            role.save(ignore_permissions=True)
            frappe.logger().info(f"Created role: {role_name}")
        else:
            frappe.logger().info(f"Role already exists: {role_name}")

    # 2️⃣ Assign Doctype Permissions for each role
    for doctype in doctypes:
        for role_name in roles:
            # Skip if permission already exists
            existing = frappe.get_all(
                "Custom DocPerm",
                filters={"parent": doctype, "role": role_name},
                fields=["name"]
            )
            if existing:
                frappe.logger().info(f"Permission already exists for {doctype} - {role_name}")
                continue

            # Create Custom DocPerm entry
            perm = frappe.new_doc("Custom DocPerm")
            perm.parent = doctype
            perm.parentfield = "permissions"
            perm.parenttype = "DocType"
            perm.role = role_name
            perm.permlevel = 0

            # Assign all permissions
            for p in permissions:
                setattr(perm, p, 1)

            perm.save(ignore_permissions=True)
            frappe.logger().info(f"Added permission for {doctype} - {role_name}")

    frappe.db.commit()

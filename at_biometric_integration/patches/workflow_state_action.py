import frappe

def execute():
    """Create workflow states and actions for Attendance Regularization Approval workflow."""
    
    # Define workflow states
    states = [
        {"workflow_state_name": "Draft", "doc_status": 0, "is_optional_state": 0},
        {"workflow_state_name": "Pending Manager Approval", "doc_status": 0, "is_optional_state": 0},
        {"workflow_state_name": "Manager Approved", "doc_status": 0, "is_optional_state": 0},
        {"workflow_state_name": "Rejected By Manager", "doc_status": 1, "is_optional_state": 0},
        {"workflow_state_name": "Pending For HR Approval", "doc_status": 0, "is_optional_state": 0},
        {"workflow_state_name": "Approved By HR", "doc_status": 1, "is_optional_state": 0},
        {"workflow_state_name": "Rejected By HR", "doc_status": 1, "is_optional_state": 0},
        {"workflow_state_name": "Canceled", "doc_status": 2, "is_optional_state": 0},
    ]

    # Define workflow actions
    actions = [
        "Submit To Manager",
        "Manager Approve",
        "Manager Reject",
        "Submit To HR",
        "HR Approve",
        "HR Reject"
    ]

    created_states = []
    created_actions = []

    # Create workflow states
    for state in states:
        if not frappe.db.exists("Workflow State", state["workflow_state_name"]):
            frappe.get_doc({
                "doctype": "Workflow State",
                "workflow_state_name": state["workflow_state_name"],
                "doc_status": state["doc_status"],
                "is_optional_state": state["is_optional_state"]
            }).insert(ignore_permissions=True)
            created_states.append(state["workflow_state_name"])

    # Create workflow actions
    for action in actions:
        if not frappe.db.exists("Workflow Action Master", {"workflow_name": workflow_name, "action": action}):
            frappe.get_doc({
                "doctype": "Workflow Action Master",
                "workflow_name": workflow_name,
                "action": action
            }).insert(ignore_permissions=True)
            created_actions.append(action)

    frappe.db.commit()

    # Log summary
    if created_states:
        frappe.logger().info(f"Created workflow states: {', '.join(created_states)}")
    else:
        frappe.logger().info("No new workflow states created.")

    if created_actions:
        frappe.logger().info(f"Created workflow actions for {workflow_name}: {', '.join(created_actions)}")
    else:
        frappe.logger().info("No new workflow actions created.")

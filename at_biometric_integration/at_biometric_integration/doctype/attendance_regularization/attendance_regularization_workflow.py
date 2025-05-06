import frappe
from frappe.model.document import Document

def create_attendance_regularization_workflow():
    # Step 1: Create Workflow Document
    workflow = frappe.get_doc({
        'doctype': 'Workflow',
        'workflow_name': 'Attendance Regularization Approval',
        'document_type': 'Attendance Regularization',
        'is_active': 1,
        'override_status': 0,
        'send_email_alert': 0,
        'workflow_state_field': 'workflow_state',
    })
    workflow.insert()

    # Step 2: Define Workflow States
    states = [
        {
            'state': 'Draft',
            'allow_edit': 'All',
            'doc_status': '0',
            'is_optional_state': 0,
            'avoid_status_override': 0,
            'send_email': 0,
        },
        {
            'state': 'Pending',
            'allow_edit': 'Employee',
            'doc_status': '0',
            'is_optional_state': 0,
            'avoid_status_override': 0,
            'send_email': 0,
            'update_field': 'status',
            'update_value': 'Pending',
        },
        {
            'state': 'Approved',
            'allow_edit': 'HR Manager',
            'doc_status': '1',
            'is_optional_state': 0,
            'avoid_status_override': 0,
            'send_email': 0,
            'update_field': 'status',
            'update_value': 'Approved',
        },
        {
            'state': 'Rejected',
            'allow_edit': 'HR Manager',
            'doc_status': '0',
            'is_optional_state': 0,
            'avoid_status_override': 0,
            'send_email': 0,
        }
    ]

    for state in states:
        workflow.append('states', state)

    # Step 3: Define Workflow Transitions
    transitions = [
        {
            'action': 'Submit for Approval',
            'allow_self_approval': 1,
            'allowed': 'Employee',
            'condition': None,
            'next_state': 'Pending',
            'state': 'Draft',
        },
        {
            'action': 'Approve',
            'allow_self_approval': 1,
            'allowed': 'HR Manager',
            'condition': None,
            'next_state': 'Approved',
            'state': 'Pending',
        },
        {
            'action': 'Reject',
            'allow_self_approval': 1,
            'allowed': 'HR Manager',
            'condition': None,
            'next_state': 'Rejected',
            'state': 'Pending',
        }
    ]

    for transition in transitions:
        workflow.append('transitions', transition)

    # Step 4: Workflow Diagram Data (Optional, for visualization purposes)
    workflow.workflow_data = '[{"type":"state","dimensions":{"width":84,"height":52},"id":"1","position":{"x":550,"y":100}}, {"type":"state","dimensions":{"width":106,"height":52},"id":"2","position":{"x":950,"y":100}}, {"type":"state","dimensions":{"width":116,"height":52},"id":"3","position":{"x":1337,"y":12}}, {"type":"state","dimensions":{"width":110,"height":52},"id":"4","position":{"x":1379.4,"y":232}}, {"type":"action","dimensions":{"width":154,"height":32},"id":"action-1","position":{"x":769,"y":108}}, {"type":"action","dimensions":{"width":78,"height":32},"id":"action-2","position":{"x":1173,"y":22}}, {"type":"action","dimensions":{"width":63,"height":32},"id":"action-3","position":{"x":1155,"y":242}}]'

    # Step 5: Save Workflow
    workflow.save()
    frappe.db.commit()

# Run the function to create the workflow
create_attendance_regularization_workflow()

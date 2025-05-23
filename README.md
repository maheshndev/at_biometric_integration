## AT Biometric Integration

AT Biometric Integration is a Frappe application that seamlessly connects your ERPNext/Frappe system with ESSL biometric devices. Leveraging the `pyzk` library, it enables real-time attendance data collection and automates employee check-ins, streamlining HR operations.

### Project Overview

This app bridges your biometric attendance devices with Frappe/ERPNext, automating the retrieval of attendance logs, mapping them to employee records, and generating detailed attendance reports. Its modular architecture allows for easy extension to support additional device models and custom HR workflows.

### Key Features

- **Biometric Device Connectivity:** Integrates with ESSL biometric devices using the `pyzk` library for reliable data synchronization.
- **Automated Employee Check-ins:** Creates Employee Checkin records in Frappe directly from biometric logs.
- **Comprehensive Attendance Reporting:** Generate daily, weekly, and monthly attendance reports for HR and payroll analysis.
- **User-Friendly Configuration:** Simple setup for device connection and employee mapping.
- **Robust Error Handling & Logging:** Advanced mechanisms for troubleshooting and monitoring.
- **Highly Extensible:** Easily adaptable to support new device models or custom business requirements.

### Requirements

- **Python:** 3.6+
- **Frappe:** v13+
- **ERPNext:** v13+ (for HR and attendance modules)
- **Frappe HRMS:** v13+ (optional, for advanced HR features)
- **ESSL Biometric Device:** Compatible with `pyzk`
- **Python Library:** `pyzk` (`pip install pyzk`)

### Installation

1. **Install the App:**
    ```bash
    cd /home/ubuntu/frappe-bench
    bench get-app at_biometric_integration
    bench --site your-site-name install-app at_biometric_integration
    ```
2. **Install Dependencies:**
    ```bash
    pip install pyzk
    ```
3. **Configure Device Settings:**
    - Go to the app configuration page in your Frappe/ERPNext site.
    - Enter your ESSL device IP address and credentials.
    - Map device user IDs to employee records.

4. **Schedule Attendance Fetch:**
    - Set up a scheduled job using the Frappe Scheduler, or run the fetch job manually as needed.

5. **Access Attendance Reports:**
    - Use the app dashboard to view, analyze, and export attendance reports.

### Attendance Reports

- **Daily Report:** Shows check-in and check-out times for each employee on a specific day.
- **Weekly Report:** Summarizes attendance, absences, and late arrivals for each employee over a week.
- **Monthly Report:** Provides a comprehensive overview for payroll and HR analysis, including total present days, absences, and overtime.

### License

MIT
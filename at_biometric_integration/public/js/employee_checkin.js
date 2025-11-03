frappe.listview_settings['Employee Checkin'] = {
    onload: function(listview) {
        listview.page.add_inner_button(__('Sync Biometric Data'), function() {
            // Show progress bar in msgprint
            let progress_html = `
                <div>
                    <b>Wait: </b> Sync in background progress ....
                    <br><br>
                    <div class="progress" style="height: 10px;">
                        <div class="progress-bar progress-bar-striped progress-bar-animated" 
                             role="progressbar" style="width: 100%"></div>
                    </div>
                </div>
            `;
            frappe.msgprint({
                title: __('Wait'),
                message: progress_html,
                indicator: 'blue'
            });
            setTimeout(() => {
                frappe.hide_msgprint();
            }, 10000);
            frappe.call({
                method: "at_biometric_integration.at_biometric_integration.utils.fetch_and_upload_attendance",
                callback: function(response) {
                    if (response.message) {
                        let msg = "";
                        if (response.message.success.length > 0) {
                            msg += `<b>Success: </b> ${response.message.success.join('<br>')}<br><br>`;
                        }
                        if (response.message.errors.length > 0) {
                            msg += `<b>Errors: </b> ${response.message.errors.join('<br>')}`;
                        }
                        frappe.msgprint(__(msg));
                    }
                }
            });
        },"Tools");

        listview.page.add_inner_button(__('Mark Attendance'), function() {
            // Show progress bar in msgprint
            let progress_html = `
                <div>
                    <b>Wait: </b>Mark Attendance in progress ....
                    <br><br>
                    <div class="progress" style="height: 10px;">
                        <div class="progress-bar progress-bar-striped progress-bar-animated" 
                             role="progressbar" style="width: 100%"></div>
                    </div>
                </div>
            `;
            frappe.msgprint({
                title: __('Wait'),
                message: progress_html,
                indicator: 'blue'
            });
            setTimeout(() => {
                frappe.hide_msgprint();
            }, 5000);
            frappe.call({
                method: "at_biometric_integration.at_biometric_integration.utils.mark_attendance",
                callback: function(response) {
                    if (response.message) {
                        let msg = "";
                        if (response.message.success.length > 0) {
                            msg += `<b>Success: </b> ${response.message.success.join('<br>')}<br><br>`;
                        }
                        if (response.message.errors.length > 0) {
                            msg += `<b>Errors: </b> ${response.message.errors.join('<br>')}`;
                        }
                        frappe.msgprint(__(msg));
                    }
                }
            });
        },"Tools");
           listview.page.add_inner_button('Import Checkins', () => {
            let $input = $('<input type="file" accept=".csv,.xls,.xlsx" style="display:none">');
            $('body').append($input);

            $input.on('change', function(e) {
                const file = e.target.files[0];
                if (!file) return;

                const fileExt = file.name.split('.').pop().toLowerCase();
                const reader = new FileReader();

                if (['xls', 'xlsx'].includes(fileExt)) {
                    reader.onload = function(e) {
                        const data = new Uint8Array(e.target.result);
                        const workbook = XLSX.read(data, { type: 'array' });
                        const sheet = workbook.Sheets[workbook.SheetNames[0]];
                        const csvData = XLSX.utils.sheet_to_csv(sheet);
                        parseCSVAndImport(csvData);
                    };
                    reader.readAsArrayBuffer(file);
                } else {
                    reader.onload = function(e) {
                        parseCSVAndImport(e.target.result);
                    };
                    reader.readAsText(file);
                }
            });

            $input.click();
        }, "Tools");
    }
};

function parseCSVAndImport(csvText) {
    frappe.confirm(
        'This will import Employee Checkins from the selected file. Continue?',
        () => {
            // Split lines and trim empty ones
            let rows = csvText.split(/\r?\n/).map(r => r.trim()).filter(r => r);
            // Find actual header (starts with "No")
            const headerIdx = rows.findIndex(r => r.startsWith('No'));
            if (headerIdx === -1) {
                frappe.msgprint('❌ Could not find header row (must start with "No.")');
                return;
            }

            // Extract only data section
            const tableRows = rows.slice(headerIdx);
            const dataRows = tableRows.map(r => r.split(/[\t,]+/));
            const headers = dataRows.shift().map(h => h.trim());

            const dateIdx = headers.indexOf('Date');
            const timeIdx = headers.indexOf('Time');
            const empIdIdx = headers.indexOf('Employee ID');
            const punchIdx = headers.indexOf('Punch State');

            if (dateIdx === -1 || timeIdx === -1 || empIdIdx === -1 || punchIdx === -1) {
                frappe.msgprint('❌ Missing required columns: Date, Time, Employee ID, Punch State');
                return;
            }

            frappe.show_progress('Importing Checkins...', 0, dataRows.length, 'Processing records');
            let count = 0;

            const processRow = (i) => {
                if (i >= dataRows.length) {
                    frappe.hide_progress();
                    frappe.msgprint(`✅ Import completed. ${count} check-ins created.`);
                    return;
                }

                const r = dataRows[i].map(v => v.trim());
                const deviceId = r[empIdIdx];
                const date = r[dateIdx];
                const time = r[timeIdx];
                const punch = r[punchIdx];

                if (!deviceId || !date || !time) {
                    processRow(i + 1);
                    return;
                }

                frappe.db.get_value('Employee', { attendance_device_id: deviceId }, 'name')
                    .then(emp => {
                        if (!emp || !emp.message.name) {
                            console.warn(`⚠️ Employee not found for device ID: ${deviceId}`);
                            processRow(i + 1);
                            return;
                        }

                        // Convert 30-10-2025 to 2025-10-30 format
                        let formattedDatetime;
                        try {
                            const [day, month, year] = date.split('-');
                            formattedDatetime = `${year}-${month}-${day} ${time}`;
                        } catch {
                            console.error('⚠️ Invalid date format:', date);
                            processRow(i + 1);
                            return;
                        }

                        frappe.call({
                            method: 'frappe.client.insert',
                            args: {
                                doc: {
                                    doctype: 'Employee Checkin',
                                    employee: emp.message.name,
                                    time: formattedDatetime,
                                    log_type: punch == '255' ? 'IN' : 'OUT',
                                    device_id: deviceId,
                                    latitude: "0.0",
                                    longitude: "0.0",
                                    skip_auto_attendance: 0
                                }
                            },
                            callback: function(r) {
                                if (!r.exc) count++;
                                frappe.show_progress('Importing Checkins...', i + 1, dataRows.length);
                                processRow(i + 1);
                            },
                            error: function(err) {
                                console.error('Insert error:', err);
                                processRow(i + 1);
                            }
                        });
                    });
            };

            processRow(0);
        }
    );
}

// Load XLSX library dynamically (for .xlsx file reading)
frappe.require('https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js');

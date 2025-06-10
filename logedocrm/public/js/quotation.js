frappe.ui.form.on('Quotation', {
    refresh: function(frm) {
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Generate Share Link'), function() {
                frappe.call({
                    method: 'logedocrm.www.quotation.index.generate_quotation_link',
                    args: {
                        quotation_name: frm.doc.name
                    },
                    callback: function(r) {
                        if (r.message && r.message.url) {
                            navigator.clipboard.writeText(r.message.url);
                            frappe.show_alert({
                                message: 'Link copied to clipboard!',
                                indicator: 'green'
                            });
                        }
                    }
                });
            }, __('Actions'));
        }
    }
});

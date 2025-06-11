// Basit clipboard kopyalama fonksiyonu
function copyToClipboard(text) {
    // Modern tarayıcılar için
    if (navigator.clipboard) {
        return navigator.clipboard.writeText(text);
    }
    
    // Eski tarayıcılar için fallback
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    return Promise.resolve();
}

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
                            copyToClipboard(r.message.url)
                                .then(function() {
                                    frappe.show_alert({
                                        message: __('Link copied to clipboard!'),
                                        indicator: 'green'
                                    });
                                })
                                .catch(function() {
                                    // Kopyalama başarısız - basit prompt göster
                                    frappe.prompt({
                                        label: __('Share Link'),
                                        fieldname: 'url',
                                        fieldtype: 'Data',
                                        default: r.message.url,
                                        read_only: 1
                                    }, function() {}, __('Copy this link manually'));
                                });
                        }
                    }
                });
            }, __('Actions'));
        }
    }
});
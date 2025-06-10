import frappe
from frappe import _
from frappe.utils.pdf import get_pdf
from frappe.utils import get_url

@frappe.whitelist(allow_guest=True)
def download_quotation_pdf():
    """Download PDF for quotation with access key verification - kept for backward compatibility"""
    
    quotation_name = frappe.form_dict.get('name')
    access_key = frappe.form_dict.get('key')
    
    if not quotation_name or not access_key:
        frappe.throw(_("Invalid parameters"), frappe.PermissionError)
    
    # Verify access key
    if not verify_access_key(quotation_name, access_key):
        frappe.throw(_("Invalid access key"), frappe.PermissionError)
    
    try:
        # Get quotation document
        quotation = frappe.get_doc("Quotation", quotation_name)
        
        if quotation.docstatus != 1:
            frappe.throw(_("Quotation not found or not submitted"))
        
        # Generate PDF
        html = frappe.render_template("templates/print_formats/quotation_guest.html", {
            "doc": quotation,
            "company": frappe.get_doc("Company", quotation.company)
        })
        
        pdf = get_pdf(html)
        
        # Set response headers for download
        frappe.local.response.filename = f"Quotation_{quotation_name}.pdf"
        frappe.local.response.filecontent = pdf
        frappe.local.response.type = "download"
        
    except Exception as e:
        frappe.log_error(f"PDF download error: {str(e)}")
        frappe.throw(_("Error generating PDF"))

@frappe.whitelist(allow_guest=True)
def download_quotation_pdf_by_hash():
    """Download PDF for quotation using hash"""
    
    logedo_hash = frappe.form_dict.get('hash')
    
    if not logedo_hash:
        frappe.throw(_("Invalid parameters"), frappe.PermissionError)
    
    # Get quotation by hash
    quotation_name = get_quotation_by_hash(logedo_hash)
    if not quotation_name:
        frappe.throw(_("Invalid hash"), frappe.PermissionError)
    
    try:
        # Get quotation document
        quotation = frappe.get_doc("Quotation", quotation_name)
        
        if quotation.docstatus != 1:
            frappe.throw(_("Quotation not found or not submitted"))
        
        # Generate PDF using the web template for full page view
        html = frappe.render_template("route/www/quotation/index.html", {
            "quotation": quotation,
            "company": frappe.get_doc("Company", quotation.company),
            "items": quotation.items,
            "taxes": quotation.taxes,
            "show_downloads": False,  # PDF'de download butonlarını gösterme
            "title": f"Quotation {quotation_name}",
            "is_pdf_view": True
        })
        
        pdf = get_pdf(html, {
            "page-size": "A4",
            "margin-top": "0.75in",
            "margin-right": "0.75in",
            "margin-bottom": "0.75in",
            "margin-left": "0.75in",
            "encoding": "UTF-8",
            "no-outline": None
        })
        
        # Set response headers for download
        frappe.local.response.filename = f"Quotation_{quotation_name}.pdf"
        frappe.local.response.filecontent = pdf
        frappe.local.response.type = "download"
        
    except Exception as e:
        frappe.log_error(f"PDF download error: {str(e)}")
        frappe.throw(_("Error generating PDF"))

def get_quotation_by_hash(logedo_hash):
    """Get quotation name by hash"""
    try:
        result = frappe.db.get_value("Quotation", {"custom_logedo_crm_hash": logedo_hash}, "name")
        return result
    except:
        return None

def verify_access_key(quotation_name, provided_key):
    """Verify access key - kept for backward compatibility"""
    try:
        quotation = frappe.get_doc("Quotation", quotation_name)
        stored_key = quotation.get("custom_access_key")
        return stored_key and stored_key == provided_key
    except:
        return False

@frappe.whitelist()
def get_quotation_share_link(quotation_name):
    """Generate shareable link for quotation - call from client side"""
    
    # Check permissions
    if not frappe.has_permission("Quotation", "read", quotation_name):
        frappe.throw(_("Permission Denied"))
    
    # Import the function from web route
    from route.www.quotation.index import generate_quotation_link
    return generate_quotation_link(quotation_name)

def create_quotation_hash(doc, method):
    """Create hash when quotation is submitted"""
    if not doc.get("custom_logedo_crm_hash"):
        from route.www.quotation.index import generate_logedo_hash
        generate_logedo_hash(doc.name)

# Backward compatibility
def create_quotation_access_key(doc, method):
    """Create access key when quotation is submitted - kept for backward compatibility"""
    create_quotation_hash(doc, method)
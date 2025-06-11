
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

import frappe
from frappe import _
from frappe.utils import get_url, now_datetime, generate_hash
from frappe.www.printview import get_rendered_template, get_print_format_doc, get_print_style
import hashlib
import time

# Guest erişimi için gerekli
no_cache = 1

def get_context(context):
    """
    URL format: /logedocrm/HASH_VALUE
    """
    
    # Get hash from URL path
    path_parts = frappe.local.request.path.strip('/').split('/')
    if len(path_parts) < 2 or path_parts[0] != 'logedocrm':
        frappe.throw(_("Invalid URL format"), frappe.PermissionError)
    
    logedo_hash = path_parts[1]
    
    if not logedo_hash:
        frappe.throw(_("Invalid URL parameters"), frappe.PermissionError)
    
    # Find quotation by hash
    quotation_name = get_quotation_by_hash(logedo_hash)
    if not quotation_name:
        frappe.throw(_("Invalid or expired link"), frappe.PermissionError)
    
    try:
        # Guest erişimi için permission kontrolünü bypass et
        frappe.set_user("Administrator")
        
        # Get quotation data
        quotation = frappe.get_doc("Quotation", quotation_name)
        
        # Check if quotation exists and is submitted
        if quotation.docstatus != 1:
            frappe.throw(_("Quotation not found or not submitted"), frappe.DoesNotExistError)

        # 📌 Loglama burada gerçekleşiyor:
        log_quotation_view(quotation, logedo_hash)

        # Get Frappe's official print format
        meta = frappe.get_meta("Quotation")
        print_format = get_print_format_doc(None, meta=meta)
        
        # Get rendered body using Frappe's method - ignore permissions
        frappe.flags.ignore_permissions = True
        body = get_rendered_template(
            quotation,
            print_format=print_format,
            meta=meta,
            trigger_print=False,
            no_letterhead=False,
            letterhead=None,
            settings={}
        )
        
        # Get print style
        print_style = get_print_style(None, print_format)
        
        # Reset user back to Guest
        frappe.set_user("Guest")

        # Prepare context for template
        context.update({
            "body": body,
            "print_style": print_style,
            "title": f"Quotation {quotation_name}",
            "lang": frappe.local.lang or "en",
            "layout_direction": "ltr",
            "doctype": "Quotation",
            "name": quotation_name,
            "key": logedo_hash,
            "print_format": getattr(print_format, "name", None),
            "letterhead": None,
            "no_letterhead": False,
            "pdf_url": get_pdf_url(logedo_hash),
            "show_downloads": True,
            "comment": frappe.session.user,
        })
        
    except frappe.DoesNotExistError:
        frappe.set_user("Guest")  # Reset user on error
        frappe.throw(_("Quotation not found"), frappe.DoesNotExistError)
    except Exception as e:
        frappe.set_user("Guest")  # Reset user on error
        frappe.log_error(f"Error in quotation web view: {str(e)}")
        frappe.throw(_("An error occurred while loading the quotation"))

def generate_logedo_hash(quotation_name):
    """Generate hash using Frappe's generate_hash utility with dash format"""
    
    # Quotation name + timestamp ile unique hash oluştur
    base_string = f"{quotation_name}:{now_datetime()}"
    hash_full = generate_hash(base_string, 20).upper()
    
    hash_part1 = hash_full[:4]   # 4 karakter
    hash_part2 = hash_full[4:6]  # 2 karakter  
    hash_part3 = hash_full[6:8]  # 2 karakter
    hash_part4 = hash_full[8:10] # 2 karakter
    hash_part5 = hash_full[10:16] # 6 karakter
    
    logedo_hash = f"{hash_part1}-{hash_part2}-{hash_part3}-{hash_part4}-{hash_part5}"
    
    frappe.db.set_value("Quotation", quotation_name, "custom_logedo_crm_hash", logedo_hash)
    frappe.db.commit()
    
    return logedo_hash

def get_quotation_by_hash(logedo_hash):
    try:
        result = frappe.db.get_value("Quotation", {"custom_logedo_crm_hash": logedo_hash}, "name")
        return result
    except:
        return None

def verify_access_key(quotation_name, provided_key):
    return True

def get_pdf_url(logedo_hash):
    return f"/api/method/logedocrm.api.download_quotation_pdf_by_hash?hash={logedo_hash}"

@frappe.whitelist(allow_guest=True)
def generate_quotation_link(quotation_name):
    if frappe.session.user == "Guest":
        frappe.throw(_("Permission Denied"), frappe.PermissionError)
    
    if not frappe.has_permission("Quotation", "read", quotation_name):
        frappe.throw(_("Permission Denied"), frappe.PermissionError)
    
    existing_hash = frappe.db.get_value("Quotation", quotation_name, "custom_logedo_crm_hash")
    
    if not existing_hash:
        logedo_hash = generate_logedo_hash(quotation_name)
    else:
        logedo_hash = existing_hash
    
    base_url = get_url()
    shareable_url = f"{base_url}/logedocrm/{logedo_hash}"
    
    return {
        "url": shareable_url,
        "hash": logedo_hash,
        "quotation_name": quotation_name
    }

import traceback

def log_quotation_view(quotation, logedo_hash):
    try:
        doc = frappe.get_doc({
            "doctype": "DataViewLog",
            "quotation": quotation.name,
            "hash_value": logedo_hash,
            "viewed_at": now_datetime(),
            "ip_address": frappe.local.request_ip,
            "user_agent": frappe.local.request.headers.get("User-Agent", ""),
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "❌ DataViewLog insert error")

# Guest access için gerekli permission fonksiyonu
def has_website_permission(doc, ptype, user, verbose=False):
    """Web sayfası için guest erişim izni"""
    return True
# -*- coding: utf-8 -*-
# Copyright (c) 2017, masonarmani38@gmail.com and, mymi14s@gmail.com [anthony Emmanuel] contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import random
import frappe
import json

from frappe import share, _

def update_customer_folder_structure(customer):
    customer_email = customer.get('email')
    if customer_email is None:
        frappe.errprint("User information not provided for client ")

    root = create_client_root_folder(customer_email)
    folders, client_name = [], customer.name
    folder_structure = get_structure()

    if folder_structure is []:
        frappe.throw("Sorry, No folder structure found")


    if(folder_structure.get('apply_on'))  == "Client":
        client_structure = get_structure(client=client_name)
        folders.append({"parent": root, "folder_name": str(client_name.replace('/', '-')).replace('"', '')})

        for (key, client) in client_structure.items():
            if isinstance(client, dict):
                for (k, v) in client.items():
                    parent = "{0}/{1}".format(root, key)
                    folders.append({"parent": parent, "folder_name": str(k.replace('/', '-')).replace('"', '')})

                    if isinstance(v, list):
                        for i in v:
                            folders.append({"parent": "{0}/{1}".format(parent, str(k.replace('/', '-')).replace('"', '')), "folder_name": str(i.replace('/', '-')).replace('"', '')})

        for folder in folders:
            create_new_folder(folder.get('folder_name'), folder.get('parent'), customer_email)


def update_customer_matter_folder_structure(matter, customer):
    customer_email = customer.get('email')
    root = create_client_root_folder(customer_email)
    folders, client_name = [], customer.name
    folder_structure = get_structure()

    if folder_structure is []:
        frappe.throw("Sorry, No folder structure found")

    if folder_structure.get('apply_on') == "Matter":
        client_structure = get_structure(client=client_name)
        folders.append({"parent": root, "folder_name": client_name})
        folders.append({"parent": "{0}/{1}".format(root, client_name), "folder_name": str(matter.name.replace('/', '-')).replace('"', '')})

        for (key, client) in client_structure.items():
            if isinstance(client, dict):
                for (k, v) in client.items():
                    parent = "{0}/{1}/{2}".format(root, key, str(matter.name.replace('/', '-')).replace('"', ''))
                    folders.append({"parent": parent, "folder_name": str(k.replace('/', '-')).replace('"', '')})

                    if isinstance(v, list):
                        for i in v:
                            folders.append({"parent": "{0}/{1}".format(parent, str(k.replace('/', '-')).replace('"', '')), "folder_name": str(i.replace('/', '-')).replace('"', '')})

        for folder in folders:
            create_new_folder(folder.get('folder_name'), folder.get('parent'), customer_email)

def get_structure(client=None):
    if client is None:
        structure = frappe.db.sql(
            "select apply_on from `tabFolder Structure` fs where  fs.is_default=1", as_dict=1)
        return structure[0] if len(structure) else []

    def get_children(parent):
        if parent != "root":
            ls = frappe.db.sql(
                "select fsi.child from `tabFolder Structure` fs inner join `tabFolder Structure Item` fsi "
                "where (fsi.parent = fs.name) and fsi.parent_folder='{parent}' and fs.is_default=1"
                    .format(parent=parent), as_list=1)

        else:
            ls = frappe.db.sql(
                "select fsi.child from `tabFolder Structure` fs inner join `tabFolder Structure Item` fsi "
                "where (fsi.parent = fs.name) and fsi.is_root=1 and fs.is_default=1", as_list=1)


        #if not len(ls):
            #frappe.throw("Sorry, No folder structure found for %s" % parent)

        return [x[0] for x in ls]

    ls = {}
    for child in get_children("root"):
        children = get_children(child)
        if children == []:
            x = child
        else:
            x = children
        ls.update({child: x})

    return {client: ls}


def create_client_root_folder(customer_email):
    name = "{0}/{1}".format("Home", "Clients")
    #frappe.errprint("creating root %s" % name)
    if not frappe.db.exists("File", name):
        file = frappe.get_doc({
            "doctype": "File",
            "file_name": "Clients",
            "is_folder": 1,
            "folder": "Home"
        })

        file.save(ignore_permissions=True)
        frappe.db.commit()

        return file.name

    share_file_with_customer_user_top(name, customer_email, notify=0)
    share_file_with_customer_user_top("Home", customer_email, notify=0)

    return name


def create_new_folder(file_name, folder, user):
    name = "{0}/{1}".format(folder, file_name)
    if not frappe.db.exists("File", name):
        file = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "is_folder": 1,
            "folder": folder
        })

        file.save(ignore_permissions=True)
        frappe.db.commit()
    if user is not None and str(user):
        share_file_with_customer_user(name, user)

    sub = 0
    if isinstance(folder,dict) and folder.get('parent') not in ("Home", "Home/Clients"):
        sub = 1


    if user is not None and str(user):
        add_user_icon("File", user, label=file_name, link="List/File/%s" % name, standard=0, is_sub=sub)


def check_standard_user_module(user, module):
    return frappe.db.sql("select count(*) from `tabDesktop Icon` where owner = '%s' "
                         "and module_name = '%s'" % (user, module))[0][0] > 0

def share_file_with_customer_user(file, user, notify=0):
    share.add("File", file, user=user, read=1, write=0, share=0, everyone=0,
              flags=None, notify=notify)
    share_all_children(file, user)



def share_file_with_customer_user_top(file, user, notify=0):
    if user == None:
        return

    share.add("File", file, user=user, read=1, write=0, share=0, everyone=0,
              flags=None, notify=notify)


def share_all_children(file,user):
    children = frappe.db.sql("select name from `tabFile` where is_folder = 0 and folder = '%s'" % file, as_list=1)
    #frappe.errprint(children)
    for child in children:
        share.add("File", child[0], user=user, read=1, write=0, share=0, everyone=0, flags = None, notify = 0)

def create_customer_user(customer):
    email = customer.email
    fullname = customer.full_name

    if email is None or frappe.db.exists("User", email):
        return

    user = frappe.get_doc({
        "doctype": "User",
        "user_type": "System User",
        "email": email,
        "send_welcome_email": 1,
        "first_name": fullname or email.split("@")[0],
        "is_customer_user": 1,
        "background_image": "/files/2fa9b6fdd1288238d7100f345617f522.jpg",
        "background_style": "Fill Screen"
    })
    user.add_roles('File User')
    user.save(ignore_permissions=True)


@frappe.whitelist()
def update_all(customer, trigger=""):
    try:
        create_customer_user(customer)
        update_customer_folder_structure(customer)
    except Exception as err:
        frappe.errprint(err)


@frappe.whitelist()
def update_all_matter(matter, trigger=""):
    try:
        customer = frappe.get_doc("Customer",matter.get('client'))
        update_customer_matter_folder_structure(matter, customer)
    except Exception as err:
        frappe.errprint(err)



@frappe.whitelist()
def append_permission(doc, trigger=""):
    # frappe.errprint("doc folder %s and  is folder is %s" % (doc.folder, doc.is_folder))
    if not doc.is_folder:
        users = []
        docshares = share.get_users("File", doc.folder)

        for docshare in docshares:
            try:
                users.index(docshare.user)
            except ValueError:
                share_file_with_customer_user(doc.name, docshare.user, 0)
                users.append(docshare.user)

def add_user_icon(_doctype, user, _report=None, label=None, link=None, type='link', standard=0, is_sub=0):
    '''Add a new user desktop icon to the desktop'''

    if user is None or not str(user) or check_standard_user_module(user=user, module=label):
        return

    if not label:
        label = _doctype or _report

    if not link:
        link = 'List/{0}'.format(_doctype)

    #frappe.errprint("attempt to add desktop to user  %s" % user)

    # find if a standard icon exists
    icon_name = frappe.db.exists('Desktop Icon', {'standard': standard, 'link': link,
                                                  'owner': user})

    if icon_name:
        if frappe.db.get_value('Desktop Icon', icon_name, 'hidden'):
            # if it is hidden, unhide it
            frappe.db.set_value('Desktop Icon', icon_name, 'hidden', 0)
            clear_desktop_icons_cache()

    else:
        idx = frappe.db.sql('select max(idx) from `tabDesktop Icon` where owner=%s', user)[0][0] or \
              frappe.db.sql('select count(*) from `tabDesktop Icon` where standard=1')[0][0]

        """"
        if not frappe.db.get_value("Report", _report):
            _report = None
            userdefined_icon = frappe.db.get_value('DocType', _doctype, ['icon', 'module'], as_dict=True)
        else:
            userdefined_icon = frappe.db.get_value('Report', _report, ['icon', 'module'], as_dict=True)
        """


        module_icon = frappe._dict()
        module_icon.color = random.choice(["#41a2a9", "#f39c12", "#528a44", "#943c3c", "#5d62ad"])
        module_icon.reverse = 0
        icon = "octicon octicon-file-directory"
        if is_sub:
            icon = "octicon octicon-file-submodule"


        try:
            new_icon = frappe.get_doc({
                'doctype': 'Desktop Icon',
                'label': label,
                'module_name': label,
                'link': link,
                'type': type,
                '_doctype': _doctype,
                '_report': _report,
                'icon': icon,
                'color': module_icon.color,
                'reverse': module_icon.reverse,
                'idx': idx + 1,
                'custom': 1,
                'hidden': 0,
                'standard': standard,
                'user':user
            })
            new_icon.owner = user
            new_icon.link = link
            new_icon.insert(ignore_permissions=True)
            clear_desktop_icons_cache(user)

            icon_name = new_icon.name

        except Exception as e:
            frappe.errprint(_('Desktop Icon already exists %s' % e))

    return icon_name

def get_all_icons():
    return [d.module_name for d in frappe.get_all('Desktop Icon',
                                                  filters={'standard': 1}, fields=['module_name'])]

def clear_desktop_icons_cache(user=None):
    frappe.cache().hdel('desktop_icons', user or frappe.session.user)
    frappe.cache().hdel('bootinfo', user or frappe.session.user)


def get_modules():
    modules = [m.module_name for m in frappe.db.get_all('Desktop Icon',
                                                        fields=['module_name'], filters={'standard': 1},
                                                        order_by="module_name")]

    return modules


def block(user, module):
    block_module = frappe.db.new_doc({
        "doctype": "Block Module",
        "module": module,
        "owner": user
    })
    block_module.insert()


def block_modules_for_user(user):
    for module in get_modules():
        block(module, user)

@frappe.whitelist()
def recursive_delete_items():
	items = sorted(json.loads(frappe.form_dict.get('items')), reverse=True)
	doctype = frappe.form_dict.get('doctype')

	if len(items) > 10:
		frappe.enqueue('frappe.desk.reportview.delete_bulk_force',
			doctype=doctype, items=items)
	else:
		delete_bulk_force(doctype, items, True)

@frappe.whitelist()
def toggle_lock():
    # get by share name and update the share user and then check if the person is not an employee
    # then remove the read and write permission for the user

    files = sorted(json.loads(frappe.form_dict.get('items')), reverse=True)
    doctype = frappe.form_dict.get('doctype')
    lock = True if frappe.form_dict.get('lock') == 'true' else False

    for file in files:
        docshares = share.get_users(doctype, file)
        for docshare in docshares:
            if not frappe.db.exists("Employee", {"user_id": docshare.get('user')}):
                share_name = share.get_share_name(doctype, file, docshare.get('user'), False)
                if share_name:
                    doc = frappe.get_doc("DocShare", share_name)
                    doc.update({
                        "read": 1 if lock else 0,
                        "write": 0,
                        "share": 0
                    })

                    file = frappe.get_doc("File", file)
                    file.update({"access_blocked": 1 if lock else 0 })

                    file.save(ignore_permissions=True)
                    doc.save(ignore_permissions=True)



def delete_bulk_force(doctype, items, recursive =False):
	failed = []
	for i, d in enumerate(items):
		if recursive:
			children = get_children(doctype,d)
			for child in children:
				delete_bulk_force(doctype,[child.get('name')])
		try:
			frappe.delete_doc(doctype, d, force=1, ignore_on_trash=1)

			if len(items) >= 5:
				frappe.publish_realtime("progress",
					dict(progress=[i+1, len(items)], title=_('Deleting {0}').format(doctype), description=d),
						user=frappe.session.user)
		except Exception:
			failed.append(d)

def get_children(doctype, parent):
	return frappe.db.sql ("select name from `tab{0}` where name like '%{1}%' "
						  "and name != '{1}'".format(doctype,parent), as_dict=1)


# unprivate files in File
# def is_private_0_before_insert(file, trigger=""):
#     if file.is_folder == 0:
#         file.is_private = 0


def validate_update_tabfile_private(doc, event):
    if(doc.is_folder==False):
        doc.is_private= False

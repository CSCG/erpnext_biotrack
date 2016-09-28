from __future__ import unicode_literals
import frappe
from datetime import date
from frappe.defaults import get_defaults
from erpnext_biotrack.utils import make_log
from .client import get_data


def sync():
	biotrack_employee_list = []
	biotrack_settings = frappe.get_doc("BioTrack Settings")
	company = biotrack_settings.custom_company or get_defaults().get("company")

	for biotrack_employee in get_biotrack_employees():
		sync_employee(biotrack_employee, company, biotrack_employee_list)

	return len(biotrack_employee_list)


def sync_employee(biotrack_employee, company, biotrack_employee_list):
	employee_name = biotrack_employee.get("employee_name")
	employee_id = biotrack_employee.get("employee_id")
	transactionid = biotrack_employee.get("transactionid")

	employee = lookup_employee(employee_name, employee_id)
	if employee:
		if not (frappe.flags.force_sync or False) and employee.external_transaction_id == transactionid:
			return False

	else:
		employee = frappe.get_doc({'doctype': 'Employee'})

	date_of_birth = date(
		int(biotrack_employee.get("birthyear")),
		int(biotrack_employee.get("birthmonth")),
		int(biotrack_employee.get("birthday"))
	)

	date_of_joining = date(
		int(biotrack_employee.get("hireyear")),
		int(biotrack_employee.get("hiremonth")),
		int(biotrack_employee.get("hireday"))
	)

	naming_series = frappe.get_meta("Employee").get_options("naming_series") or "EMP/"

	try:
		employee.update({
			"naming_series": naming_series,
			"employee_name": employee_name,
			"status": "Active",
			"external_id": employee_id,
			"external_transaction_id": transactionid,
			"company": company,
			"date_of_birth": date_of_birth,
			"date_of_joining": date_of_joining,
		})

		employee.flags.ignore_mandatory = True
		employee.save()

		biotrack_employee_list.append(biotrack_employee.get("employee_id"))
		frappe.db.commit()

	except Exception as e:
		make_log(title=e.message, status="Error", method="sync_employee", message=frappe.get_traceback(),
				 request_data=biotrack_employee, exception=True)


def lookup_employee(name, external_id):
	"""Lookup by name or BioTrack ID"""
	conditions, values = frappe.db.build_conditions({"external_id": external_id, "employee_name": name})
	conditions = " or ".join(conditions.split(" and "))
	result = frappe.db.sql("""select `name`
					from `tab%s` where %s""" % ("Employee", conditions), values, as_dict=True)

	if result:
		return frappe.get_doc("Employee", result[0])

	return None


def get_biotrack_employees(active=1):
	data = get_data('sync_employee', {'active': active})

	return data.get('employee') if bool(data.get('success')) else []
# -*- coding: utf-8 -*-
# Copyright (c) 2020, Aakvatech and contributors
# For license information, please see license.txt

from __future__ import unicode_literals 
import frappe
from frappe import _
# from frappe.utils import nowdate, get_year_start, getdate
# import datetime


def create_therapy_plan(encounter):
  if len(encounter.therapies):
    doc = frappe.new_doc('Therapy Plan')
    doc.patient = encounter.patient
    doc.start_date = encounter.encounter_date
    for entry in encounter.therapies:
      doc.append('therapy_plan_details', {
        'therapy_type': entry.therapy_type,
        'no_of_sessions': entry.no_of_sessions
      })
    doc.save(ignore_permissions=True)
    if doc.get('name'):
      encounter.db_set('therapy_plan', doc.name)
      frappe.msgprint(_('Therapy Plan {0} created successfully.').format(frappe.bold(doc.name)), alert=True)



def create_healthcare_docs(doc, method):
    for item in doc.items:
        if item.reference_dt:
            if item.reference_dt == "Healthcare Service Order":
                hso_doc = frappe.get_doc("Healthcare Service Order", item.reference_dn)
                if hso_doc.order_doctype == "Lab Test Template":
                    create_lab_test(item, hso_doc)
                elif hso_doc.order_doctype == "Radiology Examination Template":
                    create_radiology_examination(item, hso_doc)



def create_lab_test(item, hso_doc):
    if not hso_doc.order:
        return
    ltt_doc = frappe.get_doc("Lab Test Template", hso_doc.order)
    patient_sex = frappe.get_value("Patient", hso_doc.patient, "sex")

    doc = frappe.new_doc('Lab Test')
    doc.patient = hso_doc.patient
    doc.patient_sex = patient_sex
    doc.company = hso_doc.company
    doc.template = ltt_doc.name
    doc.practitioner = hso_doc.ordered_by
    doc.source = hso_doc.source

    for entry in ltt_doc.lab_test_groups:
      doc.append('normal_test_items', {
        'lab_test_name': entry.lab_test_description,
      })

    doc.save(ignore_permissions=True)
    if doc.get('name'):
      frappe.msgprint(_('Lab Test {0} created successfully.').format(frappe.bold(doc.name)), alert=True)



def create_radiology_examination(item, hso_doc):
    pass

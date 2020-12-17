# -*- coding: utf-8 -*-
# Copyright (c) 2020, Aakvatech and contributors
# For license information, please see license.txt

from __future__ import unicode_literals 
import frappe
from frappe import _
from frappe.model.document import Document
import uuid
from csf_tz.nhif.api.token import get_claimsservice_token
import json
import requests
from frappe.utils.background_jobs import enqueue
from frappe.utils import now, now_datetime, nowdate
from csf_tz.nhif.doctype.nhif_response_log.nhif_response_log import add_log
from csf_tz import console

class NHIFPatientClaim(Document):
	def validate(self):
		self.set_claim_values()


	def set_claim_values(self):
		if not self.folio_id:
			self.folio_id = str(uuid.uuid1())
		self.facility_code = frappe.get_value("Company NHIF Settings", self.company, "facility_code")
		self.posting_date = now()
		self.claim_year = int(now_datetime().strftime("%Y"))
		self.claim_month = int(now_datetime().strftime("%m"))
		self.folio_no = int(self.name[-9:])
		self.created_by = frappe.get_value("User", frappe.session.user, "full_name")
		final_patient_encounter = self.get_final_patient_encounter()
		self.practitioner_no = frappe.get_value("Healthcare Practitioner", final_patient_encounter.practitioner, "tz_mct_code")
		if not self.practitioner_no:
			frappe.throw(_("There no TZ MCT Code for Practitioner {0}").format(final_patient_encounter.practitioner))
		self.date_discharge = final_patient_encounter.encounter_date
		self.date_admitted = frappe.get_value("Patient Appointment", self.patient_appointment, "appointment_date")
		self.attendance_date = frappe.get_value("Patient Appointment", self.patient_appointment, "appointment_date")
		appointment_type = frappe.get_value("Patient Appointment", self.patient_appointment, "appointment_type")
		self.patient_type_code = "OUTPATIENT" if appointment_type != "In Patient" else "IN PATIENT"
		self.patient_file_no = self.get_patient_file_no()
		self.set_patient_claim_disease()


	def get_patient_encounters(self):
		patient_encounters = frappe.get_all("Patient Encounter",
		 filters = {
			"appointment": self.patient_appointment,
			"docstatus": 1,
		 }
		)
		return patient_encounters


	def set_patient_claim_disease(self):
		patient_encounters = self.get_patient_encounters()
		self.nhif_patient_claim_disease = []
		diagnosis_list = []
		for encounter in patient_encounters:
			encounter_doc = frappe.get_doc("Patient Encounter", encounter.name)
			for row in encounter_doc.patient_encounter_preliminary_diagnosis:
				if row.code in diagnosis_list:
					continue
				diagnosis_list.append(row.code)
				new_row = self.append("nhif_patient_claim_disease", {})
				new_row.diagnosis_type = "Preliminary Diagnosis"
				new_row.patient_encounter = encounter.name
				new_row.codification_table = row.name
				new_row.folio_disease_id = str(uuid.uuid1())
				new_row.folio_id = self.folio_id
				new_row.medical_code = row.medical_code
				new_row.disease_code = row.code
				new_row.description = row.description
				new_row.created_by = frappe.get_value("User", row.modified_by, "full_name")
				new_row.date_created = row.modified.strftime("%Y-%m-%d")
			for row in encounter_doc.patient_encounter_final_diagnosis:
				if row.code in diagnosis_list:
					continue
				diagnosis_list.append(row.code)
				new_row = self.append("nhif_patient_claim_disease", {})
				new_row.diagnosis_type = "Final Diagnosis"
				new_row.patient_encounter = encounter.name
				new_row.codification_table = row.name
				new_row.folio_disease_id = str(uuid.uuid1())
				new_row.folio_id = self.folio_id
				new_row.medical_code = row.medical_code
				new_row.disease_code = row.code
				new_row.description = row.description
				new_row.created_by = frappe.get_value("User", row.modified_by, "full_name")
				new_row.date_created = row.modified.strftime("%Y-%m-%d")

	
	def get_final_patient_encounter(self):
		patient_encounter_list = frappe.get_all("Patient Encounter",
		 filters = {
			"appointment": self.patient_appointment,
			"docstatus": 1,
			"encounter_type": "Final",
		 },
		 fields = {"*"}
		)
		if len(patient_encounter_list) == 0:
			frappe.throw(_("There no Final Patient Encounter for this Appointment"))
		return patient_encounter_list[0]


	def get_patient_file_no(self):
		patient_encounters = self.get_patient_encounters()
		patient_file_no = ""
		for encounter in patient_encounters:
			patient_file_no += encounter.name + " "
		return patient_file_no
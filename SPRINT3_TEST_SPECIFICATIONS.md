# Sprint 3 — Test Case Specifications

**Sprint:** Sprint 3  

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Scope](#2-scope)
3. [Test Environment](#3-test-environment)
4. [Requirement-to-Test Case Traceability Matrix](#4-requirement-to-test-case-traceability-matrix)
5. [Test Cases — Pharmacy & Medication Module](#5-test-cases--pharmacy--medication-module)
   - [FR-Ph-1: View Medication Orders](#fr-ph-1-pharmacy-personnel-can-view-medication-orders)
   - [FR-Ph-2: Medication Order Display & Dosage Notes](#fr-ph-2-medication-order-display--dosage-notes)
   - [FR-Ph-3: Allergy Information View](#fr-ph-3-patient-allergy-information-view)
   - [FR-Ph-4: Automatic Allergy Conflict Flagging](#fr-ph-4-automatic-allergy-conflict-flagging)
   - [FR-Ph-5: Allergy Conflict Warning Display](#fr-ph-5-allergy-conflict-warning-display)
   - [FR-D-5: Doctor Prescription Workflow](#fr-d-5-doctor-prescription-workflow)
6. [Test Cases — Appointment Module](#6-test-cases--appointment-module)
   - [PBI-S3-08: Appointment Data Model](#pbi-s3-08-appointment-data-model)
   - [FR-P-4 / FR-P-5: Patient Appointment Views](#fr-p-4--fr-p-5-patient-appointment-views)
   - [Admin Appointment Interface](#admin-appointment-scheduling-interface)
   - [FR-D-2: Doctor Appointment Management](#fr-d-2-doctor-appointment-management)
   - [FR-N-1: Nurse Appointment View](#fr-n-1-nurse-appointment-view)
6. [Test Summary](#7-test-summary)

---

## 1. Introduction

This document defines the complete test case specifications for all requirements included in the Sprint 3 backlog of the Patient Monitoring System. Each test case is mapped to one or more functional requirements (FRs) from the Functional Requirements document to provide full traceability from requirement to verification.

Test cases are written in the Given-When-Then style and cover positive paths, negative paths (access control), boundary conditions, and system behavior under error conditions.

---

## 2. Scope

Sprint 3 introduces two major feature areas:

**A. Pharmacy & Medication Enhancements**
- Structured allergy conflict detection against active medication orders (FR-Ph-4, FR-Ph-5)
- Pharmacy-specific admin interface with dosage notes (FR-Ph-1, FR-Ph-2, FR-Ph-3)
- Doctor-to-pharmacy prescription fulfillment workflow (FR-D-5, FR-Ph-1)

**B. Appointment Management System**
- `Appointment` data model (new — prerequisite PBI-S3-08)
- Admin scheduling interface with status management (FR-P-4, FR-P-5)
- Patient-facing appointment views (FR-P-4, FR-P-5)
- Doctor and nurse appointment access for assigned patients (FR-D-2, FR-N-1)

**Requirements NOT in scope for Sprint 3** (covered in previous sprints):
- FR-AA-1 through FR-AA-4 (Authentication — Sprint 1)
- FR-P-1, FR-P-2, FR-P-3 (Lab test results — Sprint 2)
- FR-P-6, FR-P-7, FR-P-8 (Personal information — Sprint 2)
- FR-D-1, FR-D-3, FR-D-4, FR-D-6 (Doctor test/history views — Sprint 2)
- FR-N-2, FR-N-3 (Nurse medication/contact views — Sprint 2)
- FR-A-1 through FR-A-12 (Admin CRUD — Sprint 2)

---

## 3. Test Environment

| Item | Value |
|------|-------|
| Framework | Django 4.x with pytest-django |
| Test runner | `pytest` with `pytest-django` |
| Database | SQLite (in-memory for tests) |
| Settings module | `patient_monitoring_system.settings_test` |
| Fixtures location | `app/tests/conftest.py` |
| Test file location | `app/tests/` |
| Coverage target | ≥ 80% per new module |

**Reusable Fixtures (from `conftest.py`):**
- `admin_user` — Admin role, `is_staff=True`
- `doctor_user` — Doctor role with license/department
- `nurse_user` — Nurse role with license/department
- `patient_user` — Patient role, linked `Patient` record auto-created
- `pharmacy_user` — Pharmacy Personnel role (new fixture required for Sprint 3)

---

## 4. Requirement-to-Test Case Traceability Matrix

| Requirement ID | Requirement Summary | Sprint 3 PBI | Test Case IDs |
|---------------|---------------------|--------------|---------------|
| FR-Ph-1 | Pharmacy personnel can view medication orders for patients | PBI-S3-01 | TC-S3-001, TC-S3-002, TC-S3-003 |
| FR-Ph-2 | Display medication name, dosage, prescribing doctor, date prescribed; dosage notes | PBI-S3-01, PBI-S3-02 | TC-S3-004, TC-S3-005, TC-S3-006, TC-S3-007 |
| FR-Ph-3 | Pharmacy personnel can view patient allergy information | PBI-S3-03 | TC-S3-008, TC-S3-009, TC-S3-010 |
| FR-Ph-4 | Automatically flag medication orders conflicting with recorded allergies | PBI-S3-04 | TC-S3-011, TC-S3-012, TC-S3-013, TC-S3-014 |
| FR-Ph-5 | Display warning message when allergy conflict is detected | PBI-S3-05 | TC-S3-015, TC-S3-016, TC-S3-017 |
| FR-D-5 | Doctor can view current and past medications of assigned patients | PBI-S3-06 | TC-S3-018, TC-S3-019, TC-S3-020 |
| PBI-S3-08 | Appointment data model (technical prerequisite) | PBI-S3-08 | TC-S3-021, TC-S3-022, TC-S3-023, TC-S3-024, TC-S3-025 |
| FR-P-4 | Patient can view upcoming appointments | PBI-S3-10 | TC-S3-026, TC-S3-027, TC-S3-028, TC-S3-029 |
| FR-P-5 | Display appointment details (date, time, doctor, location) | PBI-S3-10 | TC-S3-030, TC-S3-031 |
| Admin Scheduling | Admin can create/edit/delete appointments with status management | PBI-S3-09 | TC-S3-032, TC-S3-033, TC-S3-034, TC-S3-035, TC-S3-036 |
| FR-D-2 | Doctor can view list of all patients assigned to them (incl. appointments) | PBI-S3-11 | TC-S3-037, TC-S3-038, TC-S3-039 |
| FR-N-1 | Nurse can view list of patients assigned to them (incl. appointments) | PBI-S3-12 | TC-S3-040, TC-S3-041, TC-S3-042 |

---

## 5. Test Cases — Pharmacy & Medication Module

---

### FR-Ph-1: Pharmacy Personnel Can View Medication Orders

---

#### TC-S3-001 — Pharmacy User Accesses Medication Orders List

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-001 |
| **Requirement** | FR-Ph-1 |
| **PBI** | PBI-S3-01 |
| **Priority** | High |
| **Type** | Functional — Access Control |

**Preconditions:**
- A pharmacy user account exists (`role = "pharmacy"`, `is_staff = True`)
- At least one `Medication` record exists in the database

**Test Steps:**
1. Log in to the Django admin with the pharmacy user credentials
2. Navigate to the Medication Orders section in the admin interface
3. Observe the displayed records

**Expected Result:**
- The pharmacy user can access the medication orders list without a 403/redirect
- All medication records visible are returned
- The list view loads successfully (HTTP 200)

**Pass Criteria:** HTTP 200; medication order records are displayed

---

#### TC-S3-002 — Non-Pharmacy User Cannot Access Pharmacy Medication Interface

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-002 |
| **Requirement** | FR-Ph-1 |
| **PBI** | PBI-S3-01 |
| **Priority** | High |
| **Type** | Functional — Negative / Access Control |

**Preconditions:**
- A patient user account exists (`role = "patient"`)

**Test Steps:**
1. Log in to the Django admin with the patient user credentials
2. Attempt to navigate directly to the pharmacy medication orders URL

**Expected Result:**
- The patient is denied access (HTTP 302 redirect to login or HTTP 403 Forbidden)
- No medication order data is exposed

**Pass Criteria:** Response is NOT HTTP 200; no medication data rendered

---

#### TC-S3-003 — Pharmacy User Cannot See Medications for Unrelated Patients

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-003 |
| **Requirement** | FR-Ph-1 |
| **PBI** | PBI-S3-01 |
| **Priority** | Medium |
| **Type** | Functional — Data Isolation |

**Preconditions:**
- Two `Patient` records exist: `patient_A` and `patient_B`
- A `Medication` record exists for `patient_A`
- Pharmacy user is scoped to view only patients with active orders

**Test Steps:**
1. Log in as the pharmacy user
2. Navigate to the medication orders list
3. Filter or search for records belonging to `patient_B` (who has no medication orders)

**Expected Result:**
- No records for `patient_B` appear in the pharmacy orders view

**Pass Criteria:** Queryset returns zero records for `patient_B`

---

### FR-Ph-2: Medication Order Display & Dosage Notes

---

#### TC-S3-004 — Medication Order Displays All Required Fields

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-004 |
| **Requirement** | FR-Ph-2 |
| **PBI** | PBI-S3-01 |
| **Priority** | High |
| **Type** | Functional — UI/Data Completeness |

**Preconditions:**
- A `Medication` record exists with: `medication_name`, `dosage`, `prescribing_doctor`, `start_date`, `frequency`, `status`

**Test Steps:**
1. Log in as a pharmacy user
2. Navigate to the medication orders list
3. Observe the columns/fields shown for the medication record

**Expected Result:**
- The following fields are visible: medication name, dosage, prescribing doctor full name, date prescribed (`start_date`), frequency, status

**Pass Criteria:** All four FR-Ph-2 required fields (name, dosage, prescribing doctor, date) are present in the admin list display or detail view

---

#### TC-S3-005 — Pharmacy User Can Add Dosage Notes to a Medication Order

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-005 |
| **Requirement** | FR-Ph-2 |
| **PBI** | PBI-S3-02 |
| **Priority** | High |
| **Type** | Functional — Write Access |

**Preconditions:**
- A `Medication` record exists
- Pharmacy user has edit access to medication records

**Test Steps:**
1. Log in as the pharmacy user
2. Navigate to the medication order detail page
3. Enter text in the `notes` field: `"Dispense with food. Verify allergy to penicillin."`
4. Save the record

**Expected Result:**
- The record saves successfully
- Re-opening the record shows the entered notes text persisted

**Pass Criteria:** `Medication.notes` equals the entered string after save

---

#### TC-S3-006 — Dosage Notes Persist After Save

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-006 |
| **Requirement** | FR-Ph-2 |
| **PBI** | PBI-S3-02 |
| **Priority** | High |
| **Type** | Functional — Data Persistence |

**Preconditions:**
- A `Medication` record exists with `notes` already populated

**Test Steps:**
1. Retrieve the `Medication` record from the database via ORM: `Medication.objects.get(pk=...)`
2. Assert the `notes` field matches the previously saved value

**Expected Result:**
- `notes` field value is identical to what was saved

**Pass Criteria:** `medication.notes == expected_notes_string`

---

#### TC-S3-007 — Patient Role Cannot View Dosage Notes

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-007 |
| **Requirement** | FR-Ph-2 |
| **PBI** | PBI-S3-02 |
| **Priority** | High |
| **Type** | Functional — Negative / Access Control |

**Preconditions:**
- A `Medication` record exists with `notes` populated
- A patient user is logged in who is the subject of the medication record

**Test Steps:**
1. Log in as the patient user
2. Navigate to the patient's own admin view
3. Check whether the `notes` field is exposed in the patient-facing UI

**Expected Result:**
- The `notes` field is NOT visible in the patient-facing admin view
- The patient sees their medication list but dosage notes are hidden

**Pass Criteria:** `notes` column/field does not appear in patient-accessible template context

---

### FR-Ph-3: Patient Allergy Information View

---

#### TC-S3-008 — Pharmacy User Can View Patient Allergy Field

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-008 |
| **Requirement** | FR-Ph-3 |
| **PBI** | PBI-S3-03 |
| **Priority** | High |
| **Type** | Functional — Data Access |

**Preconditions:**
- A `Patient` record exists with `allergies = "Penicillin, Sulfa drugs"`
- A pharmacy user account exists

**Test Steps:**
1. Log in as the pharmacy user
2. Navigate to the patient record or medication orders view that surfaces allergy info
3. Observe whether the allergy information is visible

**Expected Result:**
- The `allergies` field value is displayed to the pharmacy user
- The allergy information is prominently shown alongside or near the medication order

**Pass Criteria:** Allergy text `"Penicillin, Sulfa drugs"` is rendered in the pharmacy-accessible page

---

#### TC-S3-009 — Patient Role Cannot See Their Own Allergy Field

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-009 |
| **Requirement** | FR-Ph-3 |
| **PBI** | PBI-S3-03 |
| **Priority** | High |
| **Type** | Functional — Negative / Privacy |

**Preconditions:**
- A `Patient` record exists with allergies populated
- The patient user is logged in

**Test Steps:**
1. Log in as the patient user
2. Navigate to the patient's personal record view in the admin interface
3. Inspect the rendered fields

**Expected Result:**
- The `allergies` field is NOT shown to the patient (hidden per model help_text annotation)

**Pass Criteria:** `allergies` field absent from patient-role admin fieldsets

---

#### TC-S3-010 — Allergy Field Visible to Doctor, Nurse, and Admin Roles

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-010 |
| **Requirement** | FR-Ph-3 |
| **PBI** | PBI-S3-03 |
| **Priority** | Medium |
| **Type** | Functional — Role Access Matrix |

**Preconditions:**
- A `Patient` record with allergies populated exists
- Doctor, nurse, and admin user accounts exist

**Test Steps:**
1. Log in as doctor; navigate to assigned patient record; check for `allergies` field — **Expected: visible**
2. Log in as nurse; navigate to assigned patient record; check for `allergies` field — **Expected: visible**
3. Log in as admin; navigate to patient record; check for `allergies` field — **Expected: visible**

**Expected Result:**
- All three roles can see the `allergies` field

**Pass Criteria:** For each role, HTTP 200 and allergy text rendered in response

---

### FR-Ph-4: Automatic Allergy Conflict Flagging

---

#### TC-S3-011 — System Flags Medication That Matches Patient Allergy

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-011 |
| **Requirement** | FR-Ph-4 |
| **PBI** | PBI-S3-04 |
| **Priority** | High |
| **Type** | Functional — Business Logic |

**Preconditions:**
- A `Patient` record exists with `allergies = "Penicillin, Amoxicillin"`
- A `Medication` record is created for this patient with `medication_name = "Amoxicillin"`

**Test Steps:**
1. Save the `Medication` record (via admin form or direct model save)
2. Check the conflict flag on the medication record (or check admin warning)

**Expected Result:**
- The `allergy_conflict` flag is set to `True` on the `Medication` record (or equivalent indicator)
- OR: the model's `clean()` / `save()` raises a warning-level validation message

**Pass Criteria:** `medication.allergy_conflict == True` (or equivalent conflict indicator is truthy)

---

#### TC-S3-012 — System Does Not Flag Non-Conflicting Medication

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-012 |
| **Requirement** | FR-Ph-4 |
| **PBI** | PBI-S3-04 |
| **Priority** | High |
| **Type** | Functional — Negative Path |

**Preconditions:**
- A `Patient` record with `allergies = "Penicillin"` exists
- A `Medication` record is created for this patient with `medication_name = "Metformin"`

**Test Steps:**
1. Save the `Medication` record
2. Check the conflict flag

**Expected Result:**
- `allergy_conflict` flag is `False`
- No warning is triggered

**Pass Criteria:** `medication.allergy_conflict == False`

---

#### TC-S3-013 — Conflict Check Is Case-Insensitive

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-013 |
| **Requirement** | FR-Ph-4 |
| **PBI** | PBI-S3-04 |
| **Priority** | Medium |
| **Type** | Functional — Boundary / Case Sensitivity |

**Preconditions:**
- A `Patient` with `allergies = "penicillin"` (lowercase) exists
- A `Medication` is created with `medication_name = "PENICILLIN"` (uppercase)

**Test Steps:**
1. Save the `Medication` record
2. Check the conflict flag

**Expected Result:**
- `allergy_conflict == True` despite differing case

**Pass Criteria:** Conflict detected regardless of case variation

---

#### TC-S3-014 — Conflict Check With Empty Allergy Field Returns No Conflict

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-014 |
| **Requirement** | FR-Ph-4 |
| **PBI** | PBI-S3-04 |
| **Priority** | Medium |
| **Type** | Functional — Edge Case |

**Preconditions:**
- A `Patient` with `allergies = ""` (blank) exists
- A `Medication` is created for this patient

**Test Steps:**
1. Save the `Medication` record
2. Check the conflict flag

**Expected Result:**
- `allergy_conflict == False`
- No false positives when allergy field is empty

**Pass Criteria:** `medication.allergy_conflict == False`

---

### FR-Ph-5: Allergy Conflict Warning Display

---

#### TC-S3-015 — Admin Interface Shows Warning Banner for Conflict

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-015 |
| **Requirement** | FR-Ph-5 |
| **PBI** | PBI-S3-05 |
| **Priority** | High |
| **Type** | Functional — UI |

**Preconditions:**
- A `Medication` record exists with `allergy_conflict = True`
- A pharmacy or admin user is logged in

**Test Steps:**
1. Log in as pharmacy user
2. Navigate to the medication order detail or list view for the conflicting record
3. Observe the UI for any warning indicator

**Expected Result:**
- A visible warning message/banner is displayed (e.g., "⚠ Allergy conflict detected")
- The warning includes the conflicting medication name and/or the conflicting allergy entry

**Pass Criteria:** Warning message element is present in the HTTP response body

---

#### TC-S3-016 — No Warning Shown for Non-Conflicting Medication

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-016 |
| **Requirement** | FR-Ph-5 |
| **PBI** | PBI-S3-05 |
| **Priority** | Medium |
| **Type** | Functional — Negative Path |

**Preconditions:**
- A `Medication` record exists with `allergy_conflict = False`

**Test Steps:**
1. Log in as pharmacy user
2. Navigate to the medication order for the non-conflicting record
3. Observe the UI

**Expected Result:**
- No warning banner is displayed for a non-conflicting medication

**Pass Criteria:** Warning message element is absent from the HTTP response body

---

#### TC-S3-017 — Warning Is Surfaced to Doctor Role as Well

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-017 |
| **Requirement** | FR-Ph-5 |
| **PBI** | PBI-S3-05 |
| **Priority** | Medium |
| **Type** | Functional — Role |

**Preconditions:**
- A `Medication` record with `allergy_conflict = True` exists for a patient assigned to a doctor

**Test Steps:**
1. Log in as the assigned doctor
2. Navigate to the patient's medication list
3. Observe the UI for the conflicting record

**Expected Result:**
- Doctor also sees the allergy conflict warning for the relevant medication

**Pass Criteria:** Warning indicator rendered in doctor's view of the medication

---

### FR-D-5: Doctor Prescription Workflow

---

#### TC-S3-018 — Doctor Can Create a New Medication Prescription

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-018 |
| **Requirement** | FR-D-5, FR-Ph-1 |
| **PBI** | PBI-S3-06 |
| **Priority** | High |
| **Type** | Functional — Write Access |

**Preconditions:**
- A doctor user is logged in
- An assigned patient record exists

**Test Steps:**
1. Log in as the doctor user
2. Navigate to the Medication section in the admin interface
3. Create a new `Medication` record: fill `patient`, `medication_name`, `dosage`, `frequency`, `start_date`, `status = "current"`
4. Save the record

**Expected Result:**
- Medication record is created successfully (HTTP 302 redirect after save)
- The new medication appears in the medication list
- The medication is now visible in the pharmacy queue

**Pass Criteria:** `Medication.objects.filter(prescribing_doctor=doctor_profile).count() == 1`

---

#### TC-S3-019 — Medication Created by Doctor Appears in Pharmacy Queue

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-019 |
| **Requirement** | FR-D-5, FR-Ph-1 |
| **PBI** | PBI-S3-06 |
| **Priority** | High |
| **Type** | Functional — Integration |

**Preconditions:**
- A doctor has created a `Medication` record with `fulfillment_status = "pending"` (or `status = "current"`)

**Test Steps:**
1. Log in as pharmacy user
2. Navigate to the medication orders list
3. Check for the medication created by the doctor

**Expected Result:**
- The medication is listed in the pharmacy orders view with fulfillment status = "pending" (awaiting fulfillment)

**Pass Criteria:** Medication record appears in pharmacy changelist queryset

---

#### TC-S3-020 — Non-Doctor / Non-Admin User Cannot Create Prescriptions

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-020 |
| **Requirement** | FR-D-5 |
| **PBI** | PBI-S3-06 |
| **Priority** | High |
| **Type** | Functional — Negative / Access Control |

**Preconditions:**
- A nurse user or patient user exists

**Test Steps:**
1. Log in as the nurse user
2. Attempt to navigate to the "Add Medication" page in admin
3. Attempt to POST a new medication record

**Expected Result:**
- The nurse is denied add access (no "Add" button shown; POST returns 403 or redirect)

**Pass Criteria:** Nurse cannot create `Medication` records; HTTP response is not 200/302 success

---

---

## 6. Test Cases — Appointment Module

---

### PBI-S3-08: Appointment Data Model

---

#### TC-S3-021 — Appointment Model Can Be Created With Required Fields

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-021 |
| **Requirement** | PBI-S3-08 (Technical), FR-P-4, FR-P-5 |
| **PBI** | PBI-S3-08 |
| **Priority** | High |
| **Type** | Unit — Model |

**Preconditions:**
- `Appointment` model is defined in `core/models.py`
- A `Patient` record and a doctor `UserProfile` exist

**Test Steps:**
1. Create an `Appointment` instance:
   ```python
   Appointment.objects.create(
       patient=patient,
       doctor=doctor_profile,
       appointment_datetime=datetime(2026, 4, 15, 10, 30),
       appointment_type="follow_up",
       status="scheduled",
       location="Room 204, Cardiology",
       notes="Follow up on blood panel results"
   )
   ```
2. Retrieve and assert field values

**Expected Result:**
- Appointment is persisted to database
- All fields match the input values
- `__str__` returns a meaningful string (e.g., patient name + date)

**Pass Criteria:** `Appointment.objects.count() == 1`; all asserted field values match

---

#### TC-S3-022 — Appointment Status Choices Are Valid

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-022 |
| **Requirement** | PBI-S3-08 |
| **PBI** | PBI-S3-08 |
| **Priority** | Medium |
| **Type** | Unit — Model Validation |

**Preconditions:**
- `Appointment` model is defined

**Test Steps:**
1. Assert that `Appointment.STATUS_CHOICES` contains at minimum the values:
   `"scheduled"`, `"confirmed"`, `"completed"`, `"cancelled"`, `"no_show"`
2. Attempt to create an `Appointment` with `status = "invalid_status"` and call `full_clean()`

**Expected Result:**
- Valid choices pass `full_clean()` without error
- `"invalid_status"` raises `django.core.exceptions.ValidationError`

**Pass Criteria:** `ValidationError` raised for invalid status; valid choices pass

---

#### TC-S3-023 — Appointment Type Choices Are Valid

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-023 |
| **Requirement** | PBI-S3-08 |
| **PBI** | PBI-S3-08 |
| **Priority** | Medium |
| **Type** | Unit — Model Validation |

**Preconditions:**
- `Appointment` model is defined

**Test Steps:**
1. Assert that `Appointment.APPOINTMENT_TYPE_CHOICES` contains at minimum:
   `"initial_consultation"`, `"follow_up"`, `"routine_checkup"`, `"lab_review"`, `"urgent_care"`
2. Attempt to create an `Appointment` with `appointment_type = "invalid_type"` and call `full_clean()`

**Expected Result:**
- Valid types pass `full_clean()` without error
- Invalid type raises `ValidationError`

**Pass Criteria:** Validation behaves correctly for both valid and invalid type values

---

#### TC-S3-024 — Appointment `__str__` Returns Meaningful Representation

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-024 |
| **Requirement** | PBI-S3-08 |
| **PBI** | PBI-S3-08 |
| **Priority** | Low |
| **Type** | Unit — Model |

**Preconditions:**
- An `Appointment` record exists

**Test Steps:**
1. Call `str(appointment)` on an appointment instance

**Expected Result:**
- Returns a non-empty string containing at least patient name or appointment date

**Pass Criteria:** `str(appointment)` is non-empty and contains identifying information

---

#### TC-S3-025 — Appointment Cannot Have `appointment_datetime` in the Past for Scheduled Status

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-025 |
| **Requirement** | PBI-S3-08 |
| **PBI** | PBI-S3-08 |
| **Priority** | Low |
| **Type** | Unit — Model Validation / Boundary |

**Preconditions:**
- `Appointment` model has a `clean()` method

**Test Steps:**
1. Attempt to create an `Appointment` with `status = "scheduled"` and `appointment_datetime = datetime(2000, 1, 1, 9, 0)` (far in the past)
2. Call `full_clean()` on the instance

**Expected Result:**
- A `ValidationError` is raised indicating that a scheduled appointment cannot be in the past

**Pass Criteria:** `ValidationError` raised for past datetime on a `"scheduled"` appointment

---

### FR-P-4 / FR-P-5: Patient Appointment Views

---

#### TC-S3-026 — Patient Can View Their Own Upcoming Appointments

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-026 |
| **Requirement** | FR-P-4 |
| **PBI** | PBI-S3-10 |
| **Priority** | High |
| **Type** | Functional — Access |

**Preconditions:**
- A patient user is logged in
- Two `Appointment` records exist for this patient: one future (`status = "scheduled"`), one past (`status = "completed"`)

**Test Steps:**
1. Log in as the patient user
2. Navigate to the Appointments section of the admin interface (patient-filtered)
3. Select the "Upcoming" filter or default view

**Expected Result:**
- Only the future appointment is displayed
- The past appointment is not shown in the upcoming list

**Pass Criteria:** Response contains the future appointment; past appointment is absent from the queryset

---

#### TC-S3-027 — Patient Can View Their Own Past Appointments

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-027 |
| **Requirement** | FR-P-4 |
| **PBI** | PBI-S3-10 |
| **Priority** | Medium |
| **Type** | Functional — Access |

**Preconditions:**
- A patient user is logged in
- A past `Appointment` record exists with `status = "completed"` and a past `appointment_datetime`

**Test Steps:**
1. Log in as the patient user
2. Navigate to the Appointments section
3. Select the "Past" or "Completed" filter

**Expected Result:**
- The completed past appointment is visible
- All shown appointments have `appointment_datetime` in the past

**Pass Criteria:** Completed appointment appears in the filtered queryset

---

#### TC-S3-028 — Patient Cannot View Another Patient's Appointments

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-028 |
| **Requirement** | FR-P-4 |
| **PBI** | PBI-S3-10 |
| **Priority** | High |
| **Type** | Functional — Negative / Data Isolation |

**Preconditions:**
- Two patient users exist: `patient_A` and `patient_B`
- An `Appointment` record exists for `patient_A`
- `patient_B` is logged in

**Test Steps:**
1. Log in as `patient_B`
2. Navigate to the Appointments section
3. Observe the displayed records

**Expected Result:**
- `patient_B` sees zero appointments (none assigned to them)
- No appointment belonging to `patient_A` is rendered

**Pass Criteria:** Queryset for `patient_B` returns empty; `patient_A`'s appointment is not present

---

#### TC-S3-029 — Appointments Are Shown in Chronological Order

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-029 |
| **Requirement** | FR-P-4 |
| **PBI** | PBI-S3-10 |
| **Priority** | Low |
| **Type** | Functional — Display Ordering |

**Preconditions:**
- Three upcoming `Appointment` records exist for a single patient with different dates

**Test Steps:**
1. Log in as the patient user
2. Navigate to the Appointments list view

**Expected Result:**
- Appointments are sorted ascending by `appointment_datetime` (earliest first)

**Pass Criteria:** Queryset ordering matches ascending `appointment_datetime`

---

#### TC-S3-030 — Appointment Detail Shows All Required Fields (FR-P-5)

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-030 |
| **Requirement** | FR-P-5 |
| **PBI** | PBI-S3-10 |
| **Priority** | High |
| **Type** | Functional — Data Completeness |

**Preconditions:**
- An `Appointment` exists with all fields populated
- Patient user is logged in

**Test Steps:**
1. Log in as the patient user
2. Navigate to the appointment detail page for their appointment
3. Observe which fields are rendered

**Expected Result:**
- The following fields are visible: appointment date, appointment time, doctor full name, location
- Fields are human-readable (e.g., doctor shown as "Dr. John Smith", not a PK)

**Pass Criteria:** Date, time, doctor name, and location are all present in the rendered response

---

#### TC-S3-031 — Patient Cannot Modify Their Appointment Record

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-031 |
| **Requirement** | FR-P-4, FR-P-5 |
| **PBI** | PBI-S3-10 |
| **Priority** | Medium |
| **Type** | Functional — Read-Only Enforcement |

**Preconditions:**
- An `Appointment` exists for the patient
- Patient user is logged in

**Test Steps:**
1. Log in as the patient user
2. Attempt to navigate to the appointment change/edit page
3. Attempt to POST a change to the `status` or `notes` field

**Expected Result:**
- Patient cannot edit appointment records (no edit form shown, or POST denied)
- Patient's view is read-only

**Pass Criteria:** Edit form is absent or POST returns 403/redirect without saving

---

### Admin Appointment Scheduling Interface

---

#### TC-S3-032 — Admin Can Create a New Appointment

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-032 |
| **Requirement** | FR-P-4, FR-P-5 (admin creates on behalf of patient) |
| **PBI** | PBI-S3-09 |
| **Priority** | High |
| **Type** | Functional — Admin CRUD |

**Preconditions:**
- Admin user is logged in
- At least one patient and one doctor exist

**Test Steps:**
1. Log in as admin
2. Navigate to the Appointments section → "Add Appointment"
3. Fill in: patient, doctor, date/time, type, status, location, notes
4. Save the record

**Expected Result:**
- Appointment created successfully
- Record appears in the appointments list
- HTTP 302 redirect after save (Django admin success behavior)

**Pass Criteria:** `Appointment.objects.count()` increases by 1; redirect to changelist occurs

---

#### TC-S3-033 — Admin Can Edit an Existing Appointment

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-033 |
| **Requirement** | FR-P-4 (scheduling management) |
| **PBI** | PBI-S3-09 |
| **Priority** | High |
| **Type** | Functional — Admin CRUD |

**Preconditions:**
- An `Appointment` with `status = "scheduled"` exists
- Admin user is logged in

**Test Steps:**
1. Log in as admin
2. Open the appointment in the change form
3. Change `status` to `"confirmed"` and update `notes`
4. Save

**Expected Result:**
- Changes are persisted
- `appointment.status == "confirmed"` after save

**Pass Criteria:** Updated values match the saved record

---

#### TC-S3-034 — Admin Can Delete an Appointment

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-034 |
| **Requirement** | (admin management) |
| **PBI** | PBI-S3-09 |
| **Priority** | Medium |
| **Type** | Functional — Admin CRUD |

**Preconditions:**
- An `Appointment` record exists
- Admin user is logged in

**Test Steps:**
1. Log in as admin
2. Select the appointment in the changelist and choose "Delete selected"
3. Confirm deletion

**Expected Result:**
- Appointment is removed from the database
- `Appointment.objects.count()` decrements by 1

**Pass Criteria:** Record no longer exists in the database

---

#### TC-S3-035 — Appointment List View Supports Status Filter

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-035 |
| **Requirement** | FR-P-4, FR-P-5 |
| **PBI** | PBI-S3-09 |
| **Priority** | Medium |
| **Type** | Functional — Filtering |

**Preconditions:**
- Multiple `Appointment` records exist with varying statuses (`"scheduled"`, `"completed"`, `"cancelled"`)
- Admin user is logged in

**Test Steps:**
1. Log in as admin
2. Navigate to the Appointments changelist
3. Use the status sidebar filter to select `"scheduled"`
4. Observe the filtered results

**Expected Result:**
- Only appointments with `status = "scheduled"` are shown
- Appointments with other statuses are excluded

**Pass Criteria:** Filtered queryset contains only `"scheduled"` records

---

#### TC-S3-036 — Appointment List Shows Required Columns

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-036 |
| **Requirement** | FR-P-4, FR-P-5 |
| **PBI** | PBI-S3-09 |
| **Priority** | Medium |
| **Type** | Functional — Display |

**Preconditions:**
- Multiple `Appointment` records exist
- Admin user is logged in

**Test Steps:**
1. Log in as admin
2. Navigate to the Appointments changelist

**Expected Result:**
- The list view displays columns for: Patient name, Doctor name, Appointment date/time, Appointment type, Status

**Pass Criteria:** All five column headers are present in the changelist HTML response

---

### FR-D-2: Doctor Appointment Management

---

#### TC-S3-037 — Doctor Can View Appointments for Assigned Patients

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-037 |
| **Requirement** | FR-D-2 |
| **PBI** | PBI-S3-11 |
| **Priority** | High |
| **Type** | Functional — Access |

**Preconditions:**
- A doctor user is logged in
- `patient_A` is assigned to this doctor
- An `Appointment` for `patient_A` exists

**Test Steps:**
1. Log in as the doctor user
2. Navigate to the Appointments section
3. Observe the displayed appointments

**Expected Result:**
- The appointment for `patient_A` (assigned patient) is visible

**Pass Criteria:** Appointment for `patient_A` appears in the doctor's queryset

---

#### TC-S3-038 — Doctor Cannot View Appointments for Unassigned Patients

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-038 |
| **Requirement** | FR-D-2 |
| **PBI** | PBI-S3-11 |
| **Priority** | High |
| **Type** | Functional — Negative / Data Isolation |

**Preconditions:**
- A doctor user is logged in
- `patient_B` is NOT assigned to this doctor
- An `Appointment` for `patient_B` exists

**Test Steps:**
1. Log in as the doctor user
2. Navigate to the Appointments section

**Expected Result:**
- `patient_B`'s appointment is NOT visible to the doctor

**Pass Criteria:** Queryset excludes appointments for patients not assigned to the doctor

---

#### TC-S3-039 — Doctor Can Update Appointment Notes for Assigned Patient

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-039 |
| **Requirement** | FR-D-2 |
| **PBI** | PBI-S3-11 |
| **Priority** | Medium |
| **Type** | Functional — Write Access |

**Preconditions:**
- Doctor is assigned to `patient_A`
- An `Appointment` for `patient_A` exists

**Test Steps:**
1. Log in as the doctor
2. Open the appointment change form
3. Update the `notes` field and save

**Expected Result:**
- Changes to `notes` persist
- Doctor cannot change appointment `status` to admin-only values (if any restriction is applied)

**Pass Criteria:** `appointment.notes` reflects the doctor's saved text

---

### FR-N-1: Nurse Appointment View

---

#### TC-S3-040 — Nurse Can View Appointments for Assigned Patients

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-040 |
| **Requirement** | FR-N-1 |
| **PBI** | PBI-S3-12 |
| **Priority** | High |
| **Type** | Functional — Access |

**Preconditions:**
- A nurse user is logged in
- `patient_A` is assigned to this nurse
- An `Appointment` for `patient_A` exists

**Test Steps:**
1. Log in as the nurse user
2. Navigate to the Appointments section
3. Observe the displayed appointments

**Expected Result:**
- The appointment for `patient_A` (assigned patient) is visible to the nurse

**Pass Criteria:** Appointment for `patient_A` appears in nurse's queryset

---

#### TC-S3-041 — Nurse Cannot View Appointments for Unassigned Patients

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-041 |
| **Requirement** | FR-N-1 |
| **PBI** | PBI-S3-12 |
| **Priority** | High |
| **Type** | Functional — Negative / Data Isolation |

**Preconditions:**
- A nurse user is logged in
- `patient_B` is NOT assigned to this nurse
- An `Appointment` for `patient_B` exists

**Test Steps:**
1. Log in as the nurse user
2. Navigate to the Appointments section

**Expected Result:**
- `patient_B`'s appointment is NOT visible to the nurse

**Pass Criteria:** Queryset excludes appointments for patients not assigned to the nurse

---

#### TC-S3-042 — Nurse Cannot Modify Appointment Records

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S3-042 |
| **Requirement** | FR-N-1 |
| **PBI** | PBI-S3-12 |
| **Priority** | Medium |
| **Type** | Functional — Read-Only Enforcement |

**Preconditions:**
- A nurse user is logged in
- An `Appointment` for an assigned patient exists

**Test Steps:**
1. Log in as the nurse user
2. Attempt to open the appointment change form
3. Attempt to POST a change to any field

**Expected Result:**
- Nurse's view is read-only (no Save button visible, or POST returns 403)
- No changes are persisted

**Pass Criteria:** Edit POST either blocked or admin form renders with all fields read-only

---

## 7. Test Summary

| Category | Total Test Cases | High Priority | Medium Priority | Low Priority |
|----------|-----------------|---------------|-----------------|--------------|
| Pharmacy — Medication Orders (FR-Ph-1, FR-Ph-2) | 7 | 5 | 2 | 0 |
| Pharmacy — Allergy View (FR-Ph-3) | 3 | 2 | 1 | 0 |
| Pharmacy — Conflict Flagging (FR-Ph-4) | 4 | 2 | 2 | 0 |
| Pharmacy — Conflict Warning (FR-Ph-5) | 3 | 1 | 2 | 0 |
| Doctor Prescription Workflow (FR-D-5) | 3 | 3 | 0 | 0 |
| Appointment Model (PBI-S3-08) | 5 | 1 | 2 | 2 |
| Patient Appointment Views (FR-P-4, FR-P-5) | 6 | 3 | 2 | 1 |
| Admin Appointment Interface | 5 | 2 | 3 | 0 |
| Doctor Appointment Mgmt (FR-D-2) | 3 | 2 | 1 | 0 |
| Nurse Appointment View (FR-N-1) | 3 | 2 | 1 | 0 |
| **TOTAL** | **42** | **23** | **16** | **3** |

**Test Files to Create in Sprint 3:**
- `app/tests/test_pharmacy_medication.py` — TC-S3-001 through TC-S3-020
- `app/tests/test_appointment_model.py` — TC-S3-021 through TC-S3-025
- `app/tests/test_appointment_patient_views.py` — TC-S3-026 through TC-S3-031
- `app/tests/test_appointment_admin.py` — TC-S3-032 through TC-S3-036
- `app/tests/test_appointment_doctor_nurse.py` — TC-S3-037 through TC-S3-042

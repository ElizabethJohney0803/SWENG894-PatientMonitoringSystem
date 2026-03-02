# Test Specifications — Sprint 2
## Patient Monitoring System

---

## 1. Overview

This document defines the complete test case specifications for all functional requirements planned for Sprint 2 (Patient Data Foundation and Medical Records System). Each test case is traceable to one or more functional requirements from the Functional Requirements document and to the implementation tasks defined in the sprint backlog.

### 1.1 Test Identifier Convention

Test identifiers follow this format:

```
TC-[SPRINT]-[TASK]-[TYPE]-[SEQUENCE]
```

| Segment | Values | Description |
|---|---|---|
| SPRINT | S2 | Sprint number |
| TASK | 009–016 | Task name |
| TYPE | M (Model), P (Permission), A (Admin), I (Integration) | Test category |
| SEQUENCE | 01, 02, … | Sequence within category |

### 1.2 Test File Mapping

| Test File | Location | Sprint / Task Coverage | Status |
|---|---|---|---|
| `test_models.py` | `app/tests/test_models.py` | Patient Model Creation, Patient-Doctor Assignment | Exists |
| `test_permissions.py` | `app/tests/test_permissions.py` | Patient-Doctor Assignment, Patient Admin Interface, Medical Records Access Control | Exists |
| `test_patient_doctor_assignment_admin.py` | `app/tests/test_patient_doctor_assignment_admin.py` | Patient-Doctor Assignment, Patient Admin Interface, Patient Search & Filtering | Exists |
| `test_patient_doctor_assignment_integration.py` | `app/tests/test_patient_doctor_assignment_integration.py` | Patient-Doctor Assignment | Exists |
| `test_patient_admin_access.py` | `app/tests/test_patient_admin_access.py` | Patient Admin Interface | Exists |
| `test_test_results_model.py` | `app/tests/test_test_results_model.py` | Test Results Model | To be created |
| `test_medical_history.py` | `app/tests/test_medical_history.py` | Medical History Tracking | To be created |
| `test_test_results_admin.py` | `app/tests/test_test_results_admin.py` | Test Results Admin Interface, Medical Records Access Control | To be created |

---

## 2. Requirements Traceability Matrix

| Requirement | Description | Test Cases |
|---|---|---|
| FR-A-1 | Admin create patient records | TC-S2-009-M-01, TC-S2-011-A-01 |
| FR-A-2 | Admin view patient records | TC-S2-011-A-02, TC-S2-012-A-01 |
| FR-A-3 | Admin update patient records | TC-S2-011-A-03 |
| FR-A-4 | Admin delete patient records | TC-S2-011-A-04 |
| FR-A-5/6/7/8 | Admin manage doctor records | TC-S2-010-M-04, TC-S2-010-P-02 |
| FR-P-6 | Patient view personal information | TC-S2-011-A-05 |
| FR-P-7 | Patient update editable fields | TC-S2-011-A-06 |
| FR-P-8 | Log patient info changes | TC-S2-011-A-07 |
| FR-D-2 | Doctor view assigned patients | TC-S2-010-M-02, TC-S2-010-P-01 |
| FR-D-6 | Doctor search by name or ID | TC-S2-012-A-02, TC-S2-012-A-03 |
| FR-N-1 | Nurse view assigned patients | TC-S2-010-P-03, TC-S2-011-A-08 |
| FR-N-3 | Nurse view contact information | TC-S2-011-A-09 |
| FR-AA-2 | Role-based access restriction | TC-S2-010-P-04, TC-S2-011-A-10, TC-S2-016-P-01 |
| FR-AA-3 | Prevent unauthorised data access | TC-S2-010-P-05, TC-S2-016-P-02 |
| FR-P-1 | Patient view test results | TC-S2-015-A-01, TC-S2-016-P-03 |
| FR-P-2 | Display test result details | TC-S2-013-M-03, TC-S2-015-A-02 |
| FR-P-3 | Prevent cross-patient result access | TC-S2-016-P-04 |
| FR-D-1 | Doctor view assigned patients' results | TC-S2-015-A-03, TC-S2-016-P-05 |
| FR-D-3 | Chronological display of test results | TC-S2-013-M-04, TC-S2-015-A-04 |
| FR-D-4 | Display diagnoses, procedures, visit notes | TC-S2-014-M-01, TC-S2-014-M-02 |
| FR-D-5 | Doctor view current and past medications | TC-S2-014-M-03, TC-S2-014-A-01 |
| FR-N-2 | Nurse view current medications | TC-S2-014-A-02 |

---

## 3. Sprint 2 Test Specifications

---

### Patient Model Creation

**Purpose:** Verify the Patient model is correctly structured with all required fields, relationships, and data integrity constraints.
**Test Class:** `TestPatientModel` in `app/tests/test_models.py`

---

#### TC-S2-009-M-01 — Patient Record Creation with Required Fields
**Type:** Unit — Model
**Requirement(s):** FR-A-1
**Pre-conditions:** Django ORM is initialised. A UserProfile with `role='patient'` exists.

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create a `Patient` record with all required fields (date_of_birth, gender, address, phone, medical_id) | Record is created without error |
| 2 | Query the record from the database | All field values match those supplied at creation |
| 3 | Verify `medical_id` follows format `PMR-YYYY-NNNNNN` | Medical ID is auto-generated correctly if not supplied |

**Pass Criteria:** Patient record persists with correct field values and auto-generated medical ID.

---

#### TC-S2-009-M-02 — Medical ID Auto-Generation and Uniqueness
**Type:** Unit — Model
**Requirement(s):** FR-A-1
**Pre-conditions:** At least one Patient record exists in the database.

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create two Patient records without providing a medical_id | Both records are created |
| 2 | Compare the medical IDs of the two records | IDs are unique and sequential |
| 3 | Attempt to create a Patient with a duplicate medical_id | `IntegrityError` or `ValidationError` is raised |

**Pass Criteria:** `medical_id` is unique across all records. Duplicate IDs are rejected.

---

#### TC-S2-009-M-03 — Patient Date of Birth Validation
**Type:** Unit — Model
**Requirement(s):** FR-A-1
**Pre-conditions:** None.

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create a Patient with `date_of_birth` set to a future date | `ValidationError` is raised |
| 2 | Create a Patient with `date_of_birth` more than 120 years in the past | `ValidationError` is raised |
| 3 | Create a Patient with a valid `date_of_birth` | Record is saved successfully |

**Pass Criteria:** Future and unrealistic birth dates are rejected. Valid dates are accepted.

---

#### TC-S2-009-M-04 — Patient Must Link to Patient-Role UserProfile
**Type:** Unit — Model
**Requirement(s):** FR-A-1, FR-AA-2
**Pre-conditions:** UserProfiles with roles `doctor`, `nurse`, and `patient` exist.

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create a Patient and link it to a UserProfile with `role='doctor'` | `ValidationError` is raised |
| 2 | Create a Patient and link it to a UserProfile with `role='patient'` | Record is saved successfully |

**Pass Criteria:** Only UserProfiles with `role='patient'` can be linked to a Patient record.

---

#### TC-S2-009-M-05 — Emergency Contact Creation and Relationship
**Type:** Unit — Model
**Requirement(s):** FR-A-1
**Pre-conditions:** A Patient record exists.

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create an EmergencyContact linked to the Patient | Record is created |
| 2 | Access `patient.emergency_contacts.all()` | Returns the newly created contact |
| 3 | Set `is_primary_contact=True` on a second contact for the same patient | The first contact's `is_primary_contact` is automatically set to `False` |
| 4 | Call `patient.get_primary_emergency_contact()` | Returns the correct primary contact |

**Pass Criteria:** Emergency contacts are correctly associated with patients. Only one primary contact per patient is enforced.

---

### Patient-Doctor Assignment

**Purpose:** Verify the ForeignKey relationship between Patient and doctor UserProfile is correctly implemented with appropriate access control, validation, and utility methods.
**Test Classes:**
- `TestPatientDoctorAssignment` → `app/tests/test_models.py`
- `TestPatientDoctorAssignmentPermissions` → `app/tests/test_permissions.py`
- `TestPatientDoctorAssignmentAdmin` → `app/tests/test_patient_doctor_assignment_admin.py`
- `TestPatientDoctorAssignmentIntegration` → `app/tests/test_patient_doctor_assignment_integration.py`

---

#### TC-S2-010-M-01 — Assign Doctor to Patient
**Type:** Unit — Model
**Requirement(s):** FR-D-2, FR-AA-2
**Pre-conditions:** A Patient record and a UserProfile with `role='doctor'` exist.
**Mapped to:** `test_patient_assigned_doctor_field_exists` in `test_models.py`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Access `patient.assigned_doctor` before any assignment | Value is `None` |
| 2 | Set `patient.assigned_doctor = doctor_profile` and save | Record is saved without error |
| 3 | Refresh the patient record from the database | `patient.assigned_doctor` equals the doctor profile |

**Pass Criteria:** Assignment persists correctly.

---

#### TC-S2-010-M-02 — Reverse Relationship: Doctor to Patients
**Type:** Unit — Model
**Requirement(s):** FR-D-2
**Pre-conditions:** A doctor UserProfile and multiple Patient records exist.
**Mapped to:** `test_patient_assigned_doctor_reverse_relationship` in `test_models.py`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Access `doctor_profile.assigned_patients.count()` before any assignment | Returns 0 |
| 2 | Assign two patients to the doctor and save both | No errors |
| 3 | Access `doctor_profile.assigned_patients.all()` | Returns a queryset containing both patients |

**Pass Criteria:** Reverse relation `assigned_patients` correctly returns all patients linked to the doctor.

---

#### TC-S2-010-M-03 — SET_NULL on Doctor Deletion
**Type:** Unit — Model
**Requirement(s):** FR-D-2, FR-A-8
**Pre-conditions:** A patient is assigned to a doctor.
**Mapped to:** `test_patient_assigned_doctor_set_null_on_delete` in `test_models.py`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Confirm `patient.assigned_doctor` is set | Not None |
| 2 | Delete the doctor's UserProfile | No error — cascade does not delete patient |
| 3 | Refresh the patient from the database | `patient.assigned_doctor` is `None` |

**Pass Criteria:** Deleting a doctor does not delete the patient. The `assigned_doctor` field is set to NULL.

---

#### TC-S2-010-M-04 — Only Doctor-Role Profiles Can Be Assigned
**Type:** Unit — Model
**Requirement(s):** FR-AA-2
**Pre-conditions:** UserProfiles with roles `admin`, `nurse`, and `doctor` exist.
**Mapped to:** `test_patient_assigned_doctor_validation` in `test_models.py`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Assign a UserProfile with `role='admin'` as `assigned_doctor` and call save | `ValidationError` raised: "Assigned doctor must have role='doctor'" |
| 2 | Assign a UserProfile with `role='doctor'` as `assigned_doctor` and call save | Record saved without error |

**Pass Criteria:** Non-doctor roles are rejected as valid doctor assignments.

---

#### TC-S2-010-M-05 — Doctor Utility Methods
**Type:** Unit — Model
**Requirement(s):** FR-D-2
**Pre-conditions:** A doctor UserProfile with assigned patients exists.
**Mapped to:** `test_doctor_utility_methods`, `test_can_assign_patients_property` in `test_models.py`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Call `doctor_profile.get_assigned_patients()` | Returns queryset of assigned patients |
| 2 | Call `doctor_profile.get_assigned_patients_count()` | Returns correct integer count |
| 3 | Check `admin_profile.can_assign_patients` | Returns `True` |
| 4 | Check `doctor_profile.can_assign_patients` | Returns `False` |

**Pass Criteria:** Utility methods return accurate data. Only admin can assign patients.

---

#### TC-S2-010-P-01 — Doctor Queryset Filtering in Admin
**Type:** Unit — Permissions
**Requirement(s):** FR-D-2, FR-AA-2, FR-AA-3
**Pre-conditions:** Two doctors and two patients exist; each patient is assigned to a different doctor.
**Mapped to:** `test_doctor_queryset_filtering` in `test_permissions.py`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Simulate admin request as Doctor 1 | `PatientAdmin.get_queryset()` returns only Doctor 1's patients |
| 2 | Simulate admin request as Doctor 2 | Returns only Doctor 2's patients |
| 3 | Confirm neither doctor can see the other's patients | Confirmed by queryset exclusion assertions |

**Pass Criteria:** `get_queryset()` correctly filters patients per authenticated doctor.

---

#### TC-S2-010-P-02 — Admin Can See All Patients
**Type:** Unit — Permissions
**Requirement(s):** FR-A-2, FR-AA-2
**Mapped to:** `test_admin_can_see_all_patients` in `test_permissions.py`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Simulate admin request | `get_queryset()` returns all patients regardless of assignment |

**Pass Criteria:** Admin's queryset is unfiltered.

---

#### TC-S2-010-P-03 — Nurse Can See All Patients
**Type:** Unit — Permissions
**Requirement(s):** FR-N-1
**Mapped to:** `test_patient_admin_nurse_sees_all_patients` in `test_patient_doctor_assignment_admin.py`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Simulate admin request as Nurse | `get_queryset()` returns expected patient set |

**Pass Criteria:** Nurse queryset returns the expected patient set per access rules.

---

#### TC-S2-010-P-04 — Doctor Cannot Modify Assigned Doctor Field
**Type:** Unit — Permissions
**Requirement(s):** FR-AA-2
**Mapped to:** `test_doctor_readonly_assigned_doctor_field` in `test_permissions.py`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Simulate change request as Doctor | `get_readonly_fields()` includes `assigned_doctor` |

**Pass Criteria:** `assigned_doctor` is read-only for doctor role.

---

#### TC-S2-010-P-05 — Patient Cannot Modify Assigned Doctor Field
**Type:** Unit — Permissions
**Requirement(s):** FR-AA-3
**Mapped to:** `test_patient_cannot_modify_assigned_doctor_field` in `test_permissions.py`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Simulate change request as Patient | `get_readonly_fields()` includes `assigned_doctor` |

**Pass Criteria:** `assigned_doctor` is read-only for patient role.

---

#### TC-S2-010-I-01 — Complete Assignment Workflow (Integration)
**Type:** Integration
**Requirement(s):** FR-D-2, FR-A-1, FR-AA-2
**Mapped to:** `test_complete_assignment_workflow` in `test_patient_doctor_assignment_integration.py`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create admin, doctor, and patient users from scratch | All created successfully |
| 2 | Verify patient has no assigned doctor | `assigned_doctor` is None |
| 3 | Assign patient to doctor and save | Saved without error |
| 4 | Verify assignment via both forward and reverse relations | Both confirm assignment |

**Pass Criteria:** Full end-to-end assignment workflow succeeds without errors.

---

#### TC-S2-010-I-02 — Multiple Patients to One Doctor
**Type:** Integration
**Requirement(s):** FR-D-2
**Mapped to:** `test_multiple_patients_single_doctor_workflow` in `test_patient_doctor_assignment_integration.py`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create one doctor and three patients | All created |
| 2 | Assign all three patients to the doctor | All saved |
| 3 | Check `doctor_profile.get_assigned_patients_count()` | Returns 3 |

**Pass Criteria:** One doctor can be assigned to multiple patients.

---

#### TC-S2-010-I-03 — Patient Reassignment Workflow
**Type:** Integration
**Requirement(s):** FR-D-2, FR-A-3
**Mapped to:** `test_patient_reassignment_workflow` in `test_patient_doctor_assignment_integration.py`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Assign patient to Doctor 1 | Saved |
| 2 | Reassign patient to Doctor 2 | Saved without error |
| 3 | Verify Doctor 1 has 0 assigned patients | Confirmed |
| 4 | Verify Doctor 2 has 1 assigned patient | Confirmed |

**Pass Criteria:** Reassignment correctly updates both doctors' patient lists.

---

### Patient Admin Interface

**Purpose:** Verify the Django admin interface presents the correct fields, fieldsets, and access levels to each user role.
**Test Classes:**
- `TestPatientDoctorAssignmentAdmin` → `app/tests/test_patient_doctor_assignment_admin.py`
- `TestPatientAdminAccess` → `app/tests/test_patient_admin_access.py`

---

#### TC-S2-011-A-01 — Admin Can Create Patient via Admin Form
**Type:** Unit — Admin
**Requirement(s):** FR-A-1

| Step | Action | Expected Result |
|---|---|---|
| 1 | Simulate POST to add patient form as Admin | Form is processed and patient is created |

**Pass Criteria:** Admin can successfully create a patient record via the admin interface.

---

#### TC-S2-011-A-02 — Care Assignment Fieldset Present in Form
**Type:** Unit — Admin
**Requirement(s):** FR-D-2, FR-A-3
**Mapped to:** `test_patient_admin_fieldsets_includes_care_assignment` in `test_patient_doctor_assignment_admin.py`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Access `PatientAdmin.fieldsets` | A fieldset named "Care Assignment" exists |
| 2 | Check fields within "Care Assignment" | Contains `assigned_doctor` |

**Pass Criteria:** "Care Assignment" fieldset with `assigned_doctor` is present.

---

#### TC-S2-011-A-03 — Doctor Dropdown Filtered to Doctors Only
**Type:** Unit — Admin
**Requirement(s):** FR-AA-2
**Mapped to:** `test_patient_admin_form_doctor_choices` in `test_patient_doctor_assignment_admin.py`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Instantiate `PatientAdminForm` | Form is created |
| 2 | Inspect `fields['assigned_doctor'].queryset` | Queryset contains only UserProfiles with `role='doctor'` |

**Pass Criteria:** Only doctor-role profiles appear in the assigned_doctor dropdown.

---

#### TC-S2-011-A-04 — Assigned Doctor Displayed in Patient List View
**Type:** Unit — Admin
**Requirement(s):** FR-D-2
**Mapped to:** `test_patient_admin_list_display_includes_assigned_doctor`, `test_patient_admin_list_display_unassigned_doctor` in `test_patient_doctor_assignment_admin.py`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Check `PatientAdmin.list_display` | Contains `get_assigned_doctor` |
| 2 | Call `get_assigned_doctor(patient)` for an assigned patient | Returns doctor's full name |
| 3 | Call `get_assigned_doctor(patient)` for an unassigned patient | Returns `"Unassigned"` |

**Pass Criteria:** Doctor column displays correctly in all cases.

---

#### TC-S2-011-A-05 — Patient User Sees Only Readonly Fields
**Type:** Unit — Admin
**Requirement(s):** FR-P-6, FR-P-7, FR-AA-3
**Mapped to:** `test_patient_admin_patient_readonly_fields` in `test_patient_doctor_assignment_admin.py`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Simulate change request as Patient user | `get_readonly_fields()` includes medical_id, blood_type, assigned_doctor |

**Pass Criteria:** Sensitive fields are read-only when a patient accesses their own record.

---

#### TC-S2-011-A-06 — Role-Based Readonly Fields Enforced Per Role
**Type:** Unit — Admin
**Requirement(s):** FR-AA-2
**Mapped to:** `test_patient_admin_readonly_fields_for_roles` in `test_patient_doctor_assignment_admin.py`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Check readonly fields for admin role | `assigned_doctor` is editable |
| 2 | Check readonly fields for doctor role | `assigned_doctor` is readonly |
| 3 | Check readonly fields for nurse role | All fields are readonly |

**Pass Criteria:** Field-level access control is correctly applied per role.

---

#### TC-S2-011-A-07 — Only Admin Can Modify Doctor Assignment
**Type:** Unit — Admin
**Requirement(s):** FR-AA-2, FR-A-3
**Mapped to:** `test_admin_can_modify_assigned_doctor_field` in `test_permissions.py`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Request change form as Admin | `assigned_doctor` is not in readonly_fields |
| 2 | Request change form as Doctor | `assigned_doctor` is in readonly_fields |

**Pass Criteria:** Only admin can modify the assigned_doctor field.

---

### Patient Search & Filtering

**Purpose:** Verify search and filter functionality in the Patient admin list view.
**Test Class:** `TestPatientDoctorAssignmentAdmin` in `app/tests/test_patient_doctor_assignment_admin.py`

---

#### TC-S2-012-A-01 — Filter Sidebar Includes Assigned Doctor
**Type:** Unit — Admin
**Requirement(s):** FR-A-2
**Mapped to:** `test_patient_admin_list_filter_includes_assigned_doctor` in `test_patient_doctor_assignment_admin.py`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Access `PatientAdmin.list_filter` | Contains `assigned_doctor` |

**Pass Criteria:** Assigned doctor filter is present in the list view sidebar.

---

#### TC-S2-012-A-02 — Search Fields Include Doctor Name
**Type:** Unit — Admin
**Requirement(s):** FR-D-6
**Mapped to:** `test_patient_admin_search_includes_doctor_fields` in `test_patient_doctor_assignment_admin.py`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Access `PatientAdmin.search_fields` | Contains `assigned_doctor__user__first_name` and `assigned_doctor__user__last_name` |

**Pass Criteria:** Doctor name fields are searchable from the patient list.

---

#### TC-S2-012-A-03 — Search Returns Correct Patients
**Type:** Unit — Admin
**Requirement(s):** FR-D-6, FR-A-2

| Step | Action | Expected Result |
|---|---|---|
| 1 | Search for patient by first name | Matching patients are returned |
| 2 | Search for patient by medical ID | Matching patient is returned |
| 3 | Search for non-existent value | Empty queryset returned |

**Pass Criteria:** Search returns accurate, role-filtered results.

---

### Test Results Model

**Purpose:** Verify the TestResult model is correctly structured with all required fields and relationships.
**Test Class:** `TestTestResultModel` in `app/tests/test_test_results_model.py` *(to be created)*

---

#### TC-S2-013-M-01 — TestResult Creation with Required Fields
**Type:** Unit — Model
**Requirement(s):** FR-P-2, FR-D-1
**Pre-conditions:** A Patient and a doctor UserProfile exist.

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create a TestResult with required fields (patient, ordering_doctor, test_name, test_type, test_date, result_value, reference_range) | Record is created without error |
| 2 | Query the record from the database | All field values match |

**Pass Criteria:** TestResult persists with all required fields correctly stored.

---

#### TC-S2-013-M-02 — TestResult Must Link to Valid Patient and Doctor
**Type:** Unit — Model
**Requirement(s):** FR-D-1, FR-AA-2

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create TestResult with a non-existent patient FK | `IntegrityError` is raised |
| 2 | Attempt to set `ordering_doctor` to a non-doctor UserProfile | `ValidationError` is raised |

**Pass Criteria:** Referential integrity is enforced for patient and doctor FKs.

---

#### TC-S2-013-M-03 — TestResult Fields Match FR-P-2 Requirements
**Type:** Unit — Model
**Requirement(s):** FR-P-2

| Step | Action | Expected Result |
|---|---|---|
| 1 | Access `test_name`, `result_value`, `reference_range`, `test_date` on a TestResult instance | All fields exist and return correct types |

**Pass Criteria:** All fields required by FR-P-2 are present and accessible on the model.

---

#### TC-S2-013-M-04 — TestResults Ordered Chronologically
**Type:** Unit — Model
**Requirement(s):** FR-D-3

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create three TestResult records with different test dates | Records created |
| 2 | Query `TestResult.objects.filter(patient=patient)` | Results returned in reverse chronological order (most recent first) |

**Pass Criteria:** Default model ordering satisfies FR-D-3.

---

#### TC-S2-013-M-05 — TestResult Deletion Does Not Affect Patient Record
**Type:** Unit — Model
**Requirement(s):** FR-P-1

| Step | Action | Expected Result |
|---|---|---|
| 1 | Delete a TestResult record | Deleted without error |
| 2 | Check that the linked Patient still exists | Patient record is intact |

**Pass Criteria:** TestResult records can be deleted independently without cascading to the patient.

---

### Medical History Tracking

**Purpose:** Verify medical history fields and the Medication model are correctly implemented and accessible to the right roles.
**Test Class:** `TestMedicalHistory` in `app/tests/test_medical_history.py` *(to be created)*

---

#### TC-S2-014-M-01 — Medical History Fields on Patient Model
**Type:** Unit — Model
**Requirement(s):** FR-D-4

| Step | Action | Expected Result |
|---|---|---|
| 1 | Access `patient.diagnoses`, `patient.procedures`, `patient.visit_notes` | Fields exist and accept text input |
| 2 | Save patient with history fields populated | Saved without error |
| 3 | Retrieve patient and read history fields | Values match those saved |

**Pass Criteria:** Medical history fields are present, writable, and retrievable.

---

#### TC-S2-014-M-02 — Allergy and Chronic Conditions Fields
**Type:** Unit — Model
**Requirement(s):** FR-D-4

| Step | Action | Expected Result |
|---|---|---|
| 1 | Access `patient.allergies` and `patient.chronic_conditions` | Fields exist |
| 2 | Populate and save both fields | Saved correctly |

**Pass Criteria:** Allergy and chronic condition tracking is supported at the model level.

---

#### TC-S2-014-M-03 — Medication Model Creation and Patient Link
**Type:** Unit — Model
**Requirement(s):** FR-D-5, FR-N-2

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create a Medication record linked to a Patient with required fields (name, dosage, frequency, prescribing_doctor, start_date, status) | Created without error |
| 2 | Access `patient.medications.all()` | Returns the created medication |
| 3 | Filter `patient.medications.filter(status='current')` | Returns only active medications |

**Pass Criteria:** Medications can be created, linked, and filtered by status.

---

#### TC-S2-014-M-04 — Medication Status Tracks Current vs Past
**Type:** Unit — Model
**Requirement(s):** FR-D-5

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create two medications: one `status='current'` and one `status='past'` | Both created |
| 2 | Query `patient.medications.filter(status='current')` | Returns only current medication |
| 3 | Query `patient.medications.filter(status='past')` | Returns only past medication |

**Pass Criteria:** Current and past medications are correctly distinguishable.

---

#### TC-S2-014-A-01 — Doctor Can Edit Medical History for Assigned Patients
**Type:** Unit — Admin
**Requirement(s):** FR-D-4, FR-D-5

| Step | Action | Expected Result |
|---|---|---|
| 1 | Simulate admin change request as Doctor for an assigned patient | History fields and medication inline are editable |
| 2 | Simulate admin change request as Doctor for an unassigned patient | Access is blocked or redirected |

**Pass Criteria:** Doctors can edit history only for their assigned patients.

---

#### TC-S2-014-A-02 — Nurse Can View Medications in Read-Only Mode
**Type:** Unit — Admin
**Requirement(s):** FR-N-2

| Step | Action | Expected Result |
|---|---|---|
| 1 | Simulate admin change request as Nurse | Medication inline is visible |
| 2 | Verify that add/edit/delete controls are absent from the medication inline for nurse | Confirmed — inline is rendered read-only |

**Pass Criteria:** Nurses can view current medications but cannot modify them.

---

### Test Results Admin Interface

**Purpose:** Verify the Django admin interface for TestResult enforces correct role-based visibility and editing capability.
**Test Class:** `TestTestResultAdmin` in `app/tests/test_test_results_admin.py` *(to be created)*

---

#### TC-S2-015-A-01 — Patient Can View Only Their Own Test Results
**Type:** Unit — Admin
**Requirement(s):** FR-P-1, FR-P-3

| Step | Action | Expected Result |
|---|---|---|
| 1 | Simulate list view as Patient | Only the patient's own TestResult records are returned |
| 2 | Confirm no other patient's results are visible | No cross-patient results in queryset |

**Pass Criteria:** Patient queryset is filtered to own results only.

---

#### TC-S2-015-A-02 — Test Result Detail Form Contains All FR-P-2 Fields
**Type:** Unit — Admin
**Requirement(s):** FR-P-2

| Step | Action | Expected Result |
|---|---|---|
| 1 | Access the TestResult change form | Fields for test_name, result_value, reference_range, test_date are all present |

**Pass Criteria:** All FR-P-2 required display fields are present in the admin form.

---

#### TC-S2-015-A-03 — Doctor Can Add Test Result for Assigned Patient Only
**Type:** Unit — Admin
**Requirement(s):** FR-D-1

| Step | Action | Expected Result |
|---|---|---|
| 1 | Simulate POST to add TestResult form as Doctor | TestResult is created for their assigned patient |
| 2 | Attempt to add result for an unassigned patient | Form validation fails or queryset does not include the patient |

**Pass Criteria:** Doctors can only create results for their assigned patients.

---

#### TC-S2-015-A-04 — Test Results Displayed in Chronological Order
**Type:** Unit — Admin
**Requirement(s):** FR-D-3

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create three test results with dates spanning several months | All created |
| 2 | Access the admin list view | Results are displayed with the most recent first |

**Pass Criteria:** Admin list view default ordering is reverse chronological by test_date.

---

#### TC-S2-015-A-05 — Patient Cannot Add or Edit Test Results
**Type:** Unit — Admin
**Requirement(s):** FR-P-3, FR-AA-3

| Step | Action | Expected Result |
|---|---|---|
| 1 | Simulate admin access as Patient | "Add test result" button is not visible |
| 2 | Attempt to access the add form URL directly as Patient | Returns 403 Forbidden or redirect |

**Pass Criteria:** Patients have no write access to test results in the admin interface.

---

### Medical Records Access Control

**Purpose:** Verify that queryset filtering correctly prevents unauthorised cross-patient and cross-doctor access to all medical records.
**Test Class:** `TestMedicalRecordsAccessControl` in `app/tests/test_test_results_admin.py` *(to be created)*

---

#### TC-S2-016-P-01 — Role-Based Queryset Applied for All User Roles
**Type:** Unit — Permissions
**Requirement(s):** FR-AA-2

| Step | Action | Expected Result |
|---|---|---|
| 1 | Access TestResult list as Admin | All records returned |
| 2 | Access TestResult list as Doctor | Only records for assigned patients returned |
| 3 | Access TestResult list as Patient | Only own records returned |

**Pass Criteria:** `get_queryset()` applies the correct filter for each role.

---

#### TC-S2-016-P-02 — Direct URL Access to Unauthorised Record is Blocked
**Type:** Unit — Permissions
**Requirement(s):** FR-AA-3

| Step | Action | Expected Result |
|---|---|---|
| 1 | Attempt to access a TestResult record belonging to another patient as Patient | Access denied — queryset does not include the record |
| 2 | Attempt to directly access the change URL for another patient's record | Returns 403 or redirect to list |

**Pass Criteria:** Unauthorised access to individual records is blocked at the queryset level.

---

#### TC-S2-016-P-03 — Doctor Cannot See Other Doctors' Patients' Results
**Type:** Unit — Permissions
**Requirement(s):** FR-D-1, FR-AA-3

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create Doctor A and Doctor B, each with one assigned patient and one test result | All created |
| 2 | Access TestResult list as Doctor A | Only Doctor A's patient's result is returned |
| 3 | Access TestResult list as Doctor B | Only Doctor B's patient's result is returned |

**Pass Criteria:** Doctors cannot access records from other doctors' patient pools.

---

#### TC-S2-016-P-04 — Patient Cannot Access Another Patient's Results
**Type:** Unit — Permissions
**Requirement(s):** FR-P-3

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create two patients, each with one test result | Both created |
| 2 | Access TestResult list as Patient A | Returns only Patient A's result |
| 3 | Attempt direct URL access to Patient B's result as Patient A | Returns 403 or redirect |

**Pass Criteria:** Complete cross-patient result isolation is enforced.

---

#### TC-S2-016-P-05 — Doctor Access Scoped Dynamically to Current Assignments
**Type:** Integration — Permissions
**Requirement(s):** FR-D-1, FR-AA-2

| Step | Action | Expected Result |
|---|---|---|
| 1 | Reassign a patient from Doctor A to Doctor B | Saved correctly |
| 2 | Access TestResult list as Doctor A | The reassigned patient's results are no longer visible |
| 3 | Access TestResult list as Doctor B | The reassigned patient's results are now visible |

**Pass Criteria:** Doctor access to results is dynamically scoped to their current patient assignment.

---

## 4. Test Execution Summary

### Sprint 2 — Expected Test Count

| Task | Test Class | Count | Status |
|---|---|---|---|
| Patient Model Creation | TestPatientModel | 5 | To be written |
| Patient-Doctor Assignment (Model) | TestPatientDoctorAssignment | 9 | Exists |
| Patient-Doctor Assignment (Permissions) | TestPatientDoctorAssignmentPermissions | 7 | Exists |
| Patient-Doctor Assignment (Admin) | TestPatientDoctorAssignmentAdmin | 15 | Exists |
| Patient-Doctor Assignment (Integration) | TestPatientDoctorAssignmentIntegration | 7 | Exists |
| Patient Admin Interface | TestPatientAdminAccess | 7 | Exists |
| Patient Search & Filtering | PatientSearch tests | 3 | Partially exists |
| Test Results Model | TestTestResultModel | 5 | To be created |
| Medical History Tracking | TestMedicalHistory | 4 (Model) + 2 (Admin) | To be created |
| Test Results Admin Interface | TestTestResultAdmin | 5 | To be created |
| Medical Records Access Control | TestMedicalRecordsAccessControl | 5 | To be created |
| **Sprint 2 Total** | | **74** | |

---

## 5. Test Running Instructions

### Run all Sprint 2 tests
```bash
cd app
pytest tests/test_models.py tests/test_permissions.py \
       tests/test_patient_doctor_assignment_admin.py \
       tests/test_patient_doctor_assignment_integration.py \
       tests/test_patient_admin_access.py \
       tests/test_test_results_model.py \
       tests/test_medical_history.py \
       tests/test_test_results_admin.py -v
```

### Run by task marker
```bash
pytest -m pms010 -v
pytest -m pms013 -v
```

### Run with HTML coverage report
```bash
pytest --cov=core tests/ --cov-report=html
```

---

*End of Document — Patient Monitoring System Test Specifications Sprint 2*

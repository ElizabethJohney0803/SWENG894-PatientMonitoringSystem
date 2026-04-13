# Sprint 4 — Test Specifications

**Project:** Patient Monitoring System  
**Sprint:** Sprint 4 (Final Sprint)  
**Sprint Duration:** April 4 – April 26, 2026  

---

## Table of Contents

1. [Introduction](#1-introduction)  
2. [Scope](#2-scope)  
3. [Test Environment](#3-test-environment)  
4. [Test Identifier Convention](#4-test-identifier-convention)  
5. [Requirements Traceability Matrix](#5-requirements-traceability-matrix)  
6. [Test Cases — PBI-S4-01: Nurse Patient List View](#6-test-cases--pbi-s4-01-nurse-patient-list-view)  
7. [Test Cases — PBI-S4-02: Nurse Medication Administration Tracking](#7-test-cases--pbi-s4-02-nurse-medication-administration-tracking)  
8. [Test Cases — PBI-S4-03: Nurse Contact Information View](#8-test-cases--pbi-s4-03-nurse-contact-information-view)  
9. [Test Cases — PBI-S4-04: Nurse Admin Navigation Customisation](#9-test-cases--pbi-s4-04-nurse-admin-navigation-customisation)  
10. [Test Cases — PBI-S4-05: Doctor Patient Dashboard Listing](#10-test-cases--pbi-s4-05-doctor-patient-dashboard-listing)  
11. [Test Cases — PBI-S4-06: Doctor Recent Test Results](#11-test-cases--pbi-s4-06-doctor-recent-test-results)  
12. [Test Cases — PBI-S4-07: Doctor Appointment Management](#12-test-cases--pbi-s4-07-doctor-appointment-management)  
13. [Test Cases — PBI-S4-08: Doctor Patient Search](#13-test-cases--pbi-s4-08-doctor-patient-search)  
14. [Test Cases — PBI-S4-09: Admin User Management Interface](#14-test-cases--pbi-s4-09-admin-user-management-interface)  
15. [Test Cases — PBI-S4-10: Admin Patient Record Management](#15-test-cases--pbi-s4-10-admin-patient-record-management)  
16. [Test Cases — PBI-S4-11: Admin System Settings & Group Management](#16-test-cases--pbi-s4-11-admin-system-settings--group-management)  
17. [Test Cases — PBI-S4-12: Admin Dashboard Statistics (Stretch)](#17-test-cases--pbi-s4-12-admin-dashboard-statistics-stretch)  
18. [Test Cases — PBI-S4-13: AuditLog Model](#18-test-cases--pbi-s4-13-auditlog-model)  
19. [Test Cases — PBI-S4-14: Log Data Access (Read) Events](#19-test-cases--pbi-s4-14-log-data-access-read-events)  
20. [Test Cases — PBI-S4-15: Log Data Modification Events](#20-test-cases--pbi-s4-15-log-data-modification-events)  
21. [Test Cases — PBI-S4-16: Admin Audit Log Viewer](#21-test-cases--pbi-s4-16-admin-audit-log-viewer)  
22. [Test Cases — PBI-S4-17: Drug–Allergy Risk Scoring Engine](#22-test-cases--pbi-s4-17-drugallergy-risk-scoring-engine)  
23. [Test File Mapping](#23-test-file-mapping)

---

## 1. Introduction

This document defines the complete set of test case specifications for Sprint 4 of the Patient Monitoring System. Sprint 4 is the **final sprint** of the project and is responsible for closing all remaining functional requirements (FR-N-1 through FR-N-3, FR-D-1 through FR-D-6, FR-A-1 through FR-A-12, FR-AA-2 through FR-AA-4, FR-P-8, and FR-Ph-4/FR-Ph-5 full implementation). It also delivers the full Algorithmic Component — the Drug–Allergy Risk Scoring Engine — as described in the Algorithmic Component Proposal.

Each test case is traceable to one or more functional requirements and one Product Backlog Item (PBI). Test cases are written in **Given / When / Then** format consistent with the Sprint 3 conventions and extend the existing `pytest`-based test suite located in `app/tests/`.

---

## 2. Scope

### 2.1 In-Scope Functional Requirements

| FR ID | Description |
|-------|-------------|
| FR-N-1 | Nurse views list of assigned patients |
| FR-N-2 | Nurse views current medications of assigned patients |
| FR-N-3 | Nurse views patient contact information |
| FR-D-1 | Doctor views test results of assigned patients |
| FR-D-2 | Doctor views list of assigned patients and appointments |
| FR-D-3 | Test results displayed chronologically per patient |
| FR-D-4 | Display diagnoses, procedures, and visit notes |
| FR-D-6 | Doctor searches patients by name or ID |
| FR-A-1 – FR-A-12 | Admin creates/views/updates/deletes patient and staff records |
| FR-AA-2 | Restrict access by role (nurse navigation scope) |
| FR-AA-3 | Prevent unauthorised access; audit log viewer |
| FR-AA-4 | Admin assigns roles to users / group management |
| FR-P-8 | Log changes to patient personal information |
| FR-Ph-4 | Automatically flag allergy-conflicting orders (full engine) |
| FR-Ph-5 | Display allergy conflict warning message (risk-level banner) |

### 2.2 Out-of-Scope for Sprint 4 Specifications

- FR-AA-1 (authentication) — delivered in Sprint 1; regression covered by existing `test_authentication.py`
- FR-P-1 through FR-P-7 — delivered in Sprints 1–2; covered by existing test suites
- FR-Ph-1 through FR-Ph-3 — delivered in Sprint 3; covered by `test_pharmacy_medication_orders.py`
- FR-D-5 — delivered in Sprint 3; covered by Sprint 3 test suite
- Infrastructure and deployment tests

---

## 3. Test Environment

| Attribute | Value |
|-----------|-------|
| Test Framework | `pytest` 7.x + `pytest-django` |
| Django Settings Module | `patient_monitoring_system.settings_test` |
| Database | SQLite (in-memory for unit/integration tests) |
| Fixtures Location | `app/tests/conftest.py` |
| Test Markers | `django_db`, `unit`, `models`, `admin`, `permissions`, `integration` |
| Run Command | `cd app && pytest tests/ -v` |
| Admin Test Helpers | `django.test.RequestFactory`, `django.contrib.admin.AdminSite` |
| HTTP Client Tests | `django.test.Client` |

---

## 4. Test Identifier Convention

```
TC-S4-[NNN]-[TYPE]
```

| Segment | Meaning |
|---------|---------|
| `TC` | Test Case |
| `S4` | Sprint 4 |
| `NNN` | Zero-padded sequence number (001–068) |
| `TYPE` | `U` = Unit · `F` = Functional · `I` = Integration · `N` = Negative |

---

## 5. Requirements Traceability Matrix

### 5.1 Functional Requirements → Test Cases

| FR ID | PBI | Test Cases |
|-------|-----|------------|
| FR-N-1 | PBI-S4-01 | TC-S4-001-F, TC-S4-002-F, TC-S4-003-N, TC-S4-004-F |
| FR-N-2 | PBI-S4-02 | TC-S4-005-F, TC-S4-006-F, TC-S4-007-F, TC-S4-008-N, TC-S4-009-N |
| FR-N-3 | PBI-S4-03 | TC-S4-010-F, TC-S4-011-F |
| FR-AA-2 | PBI-S4-04 | TC-S4-012-F, TC-S4-013-N, TC-S4-014-F |
| FR-D-2 | PBI-S4-05 | TC-S4-015-F, TC-S4-016-F, TC-S4-017-N, TC-S4-018-F |
| FR-D-1, FR-D-3 | PBI-S4-06 | TC-S4-019-F, TC-S4-020-F, TC-S4-021-F, TC-S4-022-F |
| FR-D-2 (appointments) | PBI-S4-07 | TC-S4-023-F, TC-S4-024-F, TC-S4-025-N, TC-S4-026-F |
| FR-D-6 | PBI-S4-08 | TC-S4-027-F, TC-S4-028-F |
| FR-A-5 – FR-A-12, FR-AA-4 | PBI-S4-09 | TC-S4-029-F, TC-S4-030-I, TC-S4-031-F, TC-S4-032-F, TC-S4-033-N |
| FR-A-1 – FR-A-4 | PBI-S4-10 | TC-S4-034-F, TC-S4-035-U, TC-S4-036-F, TC-S4-037-F |
| FR-AA-4 | PBI-S4-11 | TC-S4-038-F, TC-S4-039-I, TC-S4-040-F, TC-S4-041-N |
| FR-A-1 – FR-A-12 (stats) | PBI-S4-12 *(Stretch)* | TC-S4-042-F, TC-S4-043-F |
| FR-P-8, FR-AA-3 | PBI-S4-13 | TC-S4-044-U, TC-S4-045-U, TC-S4-046-U, TC-S4-047-U |
| FR-AA-2, FR-AA-3 | PBI-S4-14 | TC-S4-048-I, TC-S4-049-I, TC-S4-050-N, TC-S4-051-F |
| FR-P-8 | PBI-S4-15 | TC-S4-052-I, TC-S4-053-I, TC-S4-054-I, TC-S4-055-F |
| FR-AA-3 | PBI-S4-16 | TC-S4-056-F, TC-S4-057-F, TC-S4-058-F, TC-S4-059-N, TC-S4-060-F |
| FR-Ph-4, FR-Ph-5 | PBI-S4-17 | TC-S4-061-U, TC-S4-062-U, TC-S4-063-U, TC-S4-064-U, TC-S4-065-U, TC-S4-066-F, TC-S4-067-F, TC-S4-068-U |

> **Note:** Sequence numbers in sections below follow the sprint-level sequence TC-S4-001 through TC-S4-068 and are re-numbered continuously. The table above is the canonical mapping. Stretch PBI-S4-12 counters are TC-S4-042 and TC-S4-043.

### 5.2 PBI → Acceptance Criteria → Test Cases

| PBI | AC ID | Test Case(s) |
|-----|-------|--------------|
| PBI-S4-01 | AC-01.1 | TC-S4-001-F |
| PBI-S4-01 | AC-01.2 | TC-S4-002-F |
| PBI-S4-01 | AC-01.3 | TC-S4-003-N |
| PBI-S4-01 | AC-01.4 | TC-S4-004-F |
| PBI-S4-02 | AC-02.1 | TC-S4-005-F |
| PBI-S4-02 | AC-02.2 | TC-S4-006-F |
| PBI-S4-02 | AC-02.3 | TC-S4-007-F |
| PBI-S4-02 | AC-02.4 | TC-S4-008-N |
| PBI-S4-02 | AC-02.5 | TC-S4-009-N |
| PBI-S4-03 | AC-03.1 | TC-S4-010-F |
| PBI-S4-03 | AC-03.2 | TC-S4-011-F |
| PBI-S4-04 | AC-04.1 | TC-S4-012-F |
| PBI-S4-04 | AC-04.2 | TC-S4-013-N |
| PBI-S4-04 | AC-04.3 | TC-S4-014-F |
| PBI-S4-05 | AC-05.1 | TC-S4-015-F |
| PBI-S4-05 | AC-05.2 | TC-S4-016-F |
| PBI-S4-05 | AC-05.3 | TC-S4-017-N |
| PBI-S4-05 | AC-05.4 | TC-S4-018-F |
| PBI-S4-06 | AC-06.1 | TC-S4-019-F |
| PBI-S4-06 | AC-06.2 | TC-S4-020-F |
| PBI-S4-06 | AC-06.3 | TC-S4-021-F |
| PBI-S4-06 | AC-06.4 | TC-S4-022-F |
| PBI-S4-07 | AC-07.1 | TC-S4-023-F |
| PBI-S4-07 | AC-07.2 | TC-S4-024-F |
| PBI-S4-07 | AC-07.3 | TC-S4-025-N |
| PBI-S4-07 | AC-07.4 | TC-S4-026-F |
| PBI-S4-08 | AC-08.1 | TC-S4-027-F |
| PBI-S4-08 | AC-08.2 | TC-S4-028-F |
| PBI-S4-09 | AC-09.1 | TC-S4-029-F |
| PBI-S4-09 | AC-09.2 | TC-S4-030-I |
| PBI-S4-09 | AC-09.3 | TC-S4-031-F |
| PBI-S4-09 | AC-09.4 | TC-S4-032-F |
| PBI-S4-09 | AC-09.5 | TC-S4-033-N |
| PBI-S4-10 | AC-10.1 | TC-S4-034-F |
| PBI-S4-10 | AC-10.2 | TC-S4-035-U |
| PBI-S4-10 | AC-10.3 | TC-S4-036-F |
| PBI-S4-10 | AC-10.4 | TC-S4-037-F |
| PBI-S4-11 | AC-11.1 | TC-S4-038-F |
| PBI-S4-11 | AC-11.2 | TC-S4-039-I |
| PBI-S4-11 | AC-11.3 | TC-S4-040-F |
| PBI-S4-11 | AC-11.4 | TC-S4-041-N |
| PBI-S4-12 *(Stretch)* | AC-12.1 | TC-S4-042-F |
| PBI-S4-12 *(Stretch)* | AC-12.2 | TC-S4-043-F |
| PBI-S4-13 | AC-13.1 | TC-S4-044-U |
| PBI-S4-13 | AC-13.2 | TC-S4-045-U |
| PBI-S4-13 | AC-13.3 | TC-S4-046-U |
| PBI-S4-13 | AC-13.4 | TC-S4-047-U |
| PBI-S4-14 | AC-14.1 | TC-S4-048-I |
| PBI-S4-14 | AC-14.2 | TC-S4-049-I |
| PBI-S4-14 | AC-14.3 | TC-S4-050-N |
| PBI-S4-14 | AC-14.4 | TC-S4-051-F |
| PBI-S4-15 | AC-15.1 | TC-S4-052-I |
| PBI-S4-15 | AC-15.2 | TC-S4-053-I |
| PBI-S4-15 | AC-15.3 | TC-S4-054-I |
| PBI-S4-15 | AC-15.4 | TC-S4-055-F |
| PBI-S4-16 | AC-16.1 | TC-S4-056-F |
| PBI-S4-16 | AC-16.2 | TC-S4-057-F |
| PBI-S4-16 | AC-16.3 | TC-S4-058-F |
| PBI-S4-16 | AC-16.4 | TC-S4-059-N |
| PBI-S4-16 | AC-16.5 | TC-S4-060-F |
| PBI-S4-17 | AC-17.1 | TC-S4-061-U |
| PBI-S4-17 | AC-17.2 | TC-S4-062-U |
| PBI-S4-17 | AC-17.3 | TC-S4-063-U |
| PBI-S4-17 | AC-17.4 | TC-S4-064-U |
| PBI-S4-17 | AC-17.5 | TC-S4-065-U |
| PBI-S4-17 | AC-17.6 | TC-S4-066-F |
| PBI-S4-17 | AC-17.7 | TC-S4-067-F |
| PBI-S4-17 | AC-17.8 | TC-S4-068-U |
| PBI-S4-17 | AC-17.9 | TC-S4-069-U |
| PBI-S4-17 | AC-17.10 | TC-S4-070-U |

---

## 6. Test Cases — PBI-S4-01: Nurse Patient List View

### FR-N-1: Nurse views list of assigned patients

---

#### TC-S4-001-F — Nurse queryset returns only assigned patients

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-001-F |
| **Requirement** | FR-N-1 |
| **PBI** | PBI-S4-01 |
| **AC** | AC-01.1 |
| **Priority** | High |
| **Type** | Functional — Data Isolation |
| **Preconditions** | A nurse user exists with `UserProfile.role = "nurse"`. Two patient records exist: Patient A with `assigned_nurse` pointing to the nurse's `UserProfile`, and Patient B with `assigned_nurse = None` (or a different nurse). `PatientAdmin` is registered in the admin site. |
| **Test Steps** | 1. Instantiate `PatientAdmin` with a mock `AdminSite`. <br>2. Create a `GET` request via `RequestFactory`. <br>3. Attach the nurse user to `request.user`. <br>4. Call `admin.get_queryset(request)`. <br>5. Inspect the returned queryset. |
| **Expected Result** | The queryset contains exactly Patient A. Patient B is absent. |
| **Pass Criteria** | `assert patient_a in qs` and `assert patient_b not in qs` and `qs.count() == 1` |

---

#### TC-S4-002-F — Nurse patient list displays required columns

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-002-F |
| **Requirement** | FR-N-1 |
| **PBI** | PBI-S4-01 |
| **AC** | AC-01.2 |
| **Priority** | High |
| **Type** | Functional — Display |
| **Preconditions** | Same setup as TC-S4-001-F. `PatientAdmin.list_display` must be configured for the nurse role. |
| **Test Steps** | 1. Create a `GET` request with the nurse user. <br>2. Call `admin.get_list_display(request)` (or inspect `list_display` for the nurse role branch). <br>3. Verify the returned fields. |
| **Expected Result** | The `list_display` returned for a nurse includes: patient full name, date of birth, blood type, assigned doctor name, and chronic conditions. |
| **Pass Criteria** | All five field names (or their column callables) are present in the returned `list_display` tuple/list. |

---

#### TC-S4-003-N — Nurse denied access to unassigned patient via direct URL

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-003-N |
| **Requirement** | FR-N-1 |
| **PBI** | PBI-S4-01 |
| **AC** | AC-01.3 |
| **Priority** | High |
| **Type** | Functional — Negative / Access Control |
| **Preconditions** | Nurse user exists. An unassigned patient (Patient B) exists. Admin site is configured. The Django test `Client` is used for HTTP-level testing. |
| **Test Steps** | 1. Authenticate the test client as the nurse user. <br>2. Construct the direct admin change URL for Patient B: `/admin/core/patient/<patient_b_pk>/change/`. <br>3. Issue a `GET` request to that URL. <br>4. Inspect the response. |
| **Expected Result** | Response status is `403 Forbidden` or the user is redirected and the patient record content is not rendered. |
| **Pass Criteria** | `assert response.status_code in (403, 302)` and patient B's fields are not present in the response content. |

---

#### TC-S4-004-F — Nurse patient detail page is fully read-only

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-004-F |
| **Requirement** | FR-N-1 |
| **PBI** | PBI-S4-01 |
| **AC** | AC-01.4 |
| **Priority** | High |
| **Type** | Functional — Permissions |
| **Preconditions** | Nurse user has Patient A assigned. `PatientAdmin` is configured. |
| **Test Steps** | 1. Create a `GET` request with the nurse user. <br>2. Call `admin.has_change_permission(request, patient_a)`. <br>3. Call `admin.has_delete_permission(request, patient_a)`. <br>4. Call `admin.get_readonly_fields(request, patient_a)` and verify coverage. |
| **Expected Result** | `has_change_permission` returns `False`. `has_delete_permission` returns `False`. All editable fields are listed in `readonly_fields`. |
| **Pass Criteria** | `assert admin.has_change_permission(request, patient_a) is False` <br>`assert admin.has_delete_permission(request, patient_a) is False` |

---

## 7. Test Cases — PBI-S4-02: Nurse Medication Administration Tracking

### FR-N-2: Nurse views current medications of assigned patients

---

#### TC-S4-005-F — Nurse medication queryset scoped to assigned patients

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-005-F |
| **Requirement** | FR-N-2 |
| **PBI** | PBI-S4-02 |
| **AC** | AC-02.1 |
| **Priority** | High |
| **Type** | Functional — Data Isolation |
| **Preconditions** | Nurse user exists. Patient A is `assigned_nurse` = nurse. Patient B belongs to a different nurse. Medication M1 belongs to Patient A; Medication M2 belongs to Patient B. `MedicationAdmin` is registered. |
| **Test Steps** | 1. Instantiate `MedicationAdmin` with mock `AdminSite`. <br>2. Create `GET` request with nurse user. <br>3. Call `admin.get_queryset(request)`. |
| **Expected Result** | Queryset contains M1 only; M2 is absent. |
| **Pass Criteria** | `assert m1 in qs` and `assert m2 not in qs` |

---

#### TC-S4-006-F — Nurse medication list displays required columns

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-006-F |
| **Requirement** | FR-N-2 |
| **PBI** | PBI-S4-02 |
| **AC** | AC-02.2 |
| **Priority** | High |
| **Type** | Functional — Display |
| **Preconditions** | Same as TC-S4-005-F. `MedicationAdmin.list_display` includes nurse-role branch. |
| **Test Steps** | 1. Create `GET` request with nurse user. <br>2. Inspect `list_display` returned for the nurse role. |
| **Expected Result** | `list_display` includes: patient name, medication name, dosage, frequency, start date, status, and an allergy-conflict indicator column. |
| **Pass Criteria** | All seven fields (or their callable equivalents) are present in the returned list. |

---

#### TC-S4-007-F — Allergy-conflict indicator displayed for conflicting medications

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-007-F |
| **Requirement** | FR-N-2 |
| **PBI** | PBI-S4-02 |
| **AC** | AC-02.3 |
| **Priority** | High |
| **Type** | Functional — Display |
| **Preconditions** | Nurse user exists with an assigned patient whose `allergies` field contains "penicillin". A `Medication` with `medication_name = "Amoxicillin"` is saved for that patient, triggering `allergy_conflict = True` (Sprint 3 engine) or `risk_level` mapping rule (Sprint 4 engine). |
| **Test Steps** | 1. Retrieve the saved medication object. <br>2. Call the `allergy_conflict_display` callable (or equivalent) defined on `MedicationAdmin`. <br>3. Inspect the returned HTML string. |
| **Expected Result** | The returned string contains a visible warning indicator — e.g. the `⚠` character, a CSS class `"allergy-warning"`, or equivalent markup. |
| **Pass Criteria** | `assert "⚠" in result or "allergy-warning" in result` |

---

#### TC-S4-008-N — Nurse cannot add, edit, or delete medication records

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-008-N |
| **Requirement** | FR-N-2 |
| **PBI** | PBI-S4-02 |
| **AC** | AC-02.4 |
| **Priority** | High |
| **Type** | Functional — Negative / Permissions |
| **Preconditions** | Nurse user exists. Medication M1 belongs to an assigned patient. |
| **Test Steps** | 1. Create a `GET` request with the nurse user. <br>2. Call `admin.has_add_permission(request)`. <br>3. Call `admin.has_change_permission(request, m1)`. <br>4. Call `admin.has_delete_permission(request, m1)`. |
| **Expected Result** | All three permission checks return `False`. |
| **Pass Criteria** | `assert not admin.has_add_permission(request)` <br>`assert not admin.has_change_permission(request, m1)` <br>`assert not admin.has_delete_permission(request, m1)` |

---

#### TC-S4-009-N — Nurse with no assigned patients sees empty medication list

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-009-N |
| **Requirement** | FR-N-2 |
| **PBI** | PBI-S4-02 |
| **AC** | AC-02.5 |
| **Priority** | Medium |
| **Type** | Functional — Negative / Edge Case |
| **Preconditions** | Nurse user exists with no patients assigned. Several medications exist for other patients. |
| **Test Steps** | 1. Create `GET` request with the unassigned nurse user. <br>2. Call `admin.get_queryset(request)` on `MedicationAdmin`. |
| **Expected Result** | The returned queryset is empty (`count() == 0`). No medications for other patients are exposed. |
| **Pass Criteria** | `assert qs.count() == 0` |

---

## 8. Test Cases — PBI-S4-03: Nurse Contact Information View

### FR-N-3: Nurse views patient contact information

---

#### TC-S4-010-F — Emergency contact queryset scoped to nurse's assigned patients

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-010-F |
| **Requirement** | FR-N-3 |
| **PBI** | PBI-S4-03 |
| **AC** | AC-03.1 |
| **Priority** | High |
| **Type** | Functional — Data Isolation |
| **Preconditions** | Nurse user exists. Patient A assigned to nurse has Emergency Contact EC1. Patient B (not assigned) has Emergency Contact EC2. `EmergencyContactAdmin` is registered. |
| **Test Steps** | 1. Instantiate `EmergencyContactAdmin` with mock `AdminSite`. <br>2. Create `GET` request with nurse user. <br>3. Call `admin.get_queryset(request)`. |
| **Expected Result** | Queryset contains EC1 only. EC2 is absent. |
| **Pass Criteria** | `assert ec1 in qs` and `assert ec2 not in qs` |

---

#### TC-S4-011-F — Nurse can view patient personal contact in read-only fields

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-011-F |
| **Requirement** | FR-N-3 |
| **PBI** | PBI-S4-03 |
| **AC** | AC-03.2 |
| **Priority** | High |
| **Type** | Functional — Display |
| **Preconditions** | Nurse user exists. Patient A assigned to nurse has `phone_primary`, `phone_secondary`, and `email_personal` set. |
| **Test Steps** | 1. Create `GET` request with nurse user. <br>2. Call `admin.get_readonly_fields(request, patient_a)` on `PatientAdmin`. <br>3. Verify the contact fields are included in `readonly_fields`. |
| **Expected Result** | `phone_primary`, `phone_secondary`, and `email_personal` are returned in the `readonly_fields` for a nurse viewing Patient A. |
| **Pass Criteria** | All three field names appear in the `readonly_fields` list returned for the nurse role. |

---

## 9. Test Cases — PBI-S4-04: Nurse Admin Navigation Customisation

### FR-AA-2: Restrict access by role — nurse navigation scope

---

#### TC-S4-012-F — Nurse admin index shows only permitted sections

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-012-F |
| **Requirement** | FR-AA-2 |
| **PBI** | PBI-S4-04 |
| **AC** | AC-04.1 |
| **Priority** | High |
| **Type** | Functional — Access Control |
| **Preconditions** | Nurse user exists and is logged into the admin site. All model admins are registered. The admin site uses role-aware navigation filtering. |
| **Test Steps** | 1. Authenticate the Django test `Client` as the nurse user. <br>2. Issue a `GET` to `/admin/`. <br>3. Inspect the response content for app/model labels. |
| **Expected Result** | Only the sections for Patients, Medications, Appointments, and Test Results are present in the HTML. Sections for Users, Groups, User Profiles, and Audit Logs are absent. |
| **Pass Criteria** | Response status is `200`. Permitted labels are found in content; forbidden labels are not. |

---

#### TC-S4-013-N — Nurse denied access to Users, Groups, UserProfiles admin URLs

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-013-N |
| **Requirement** | FR-AA-2 |
| **PBI** | PBI-S4-04 |
| **AC** | AC-04.2 |
| **Priority** | High |
| **Type** | Functional — Negative / Access Control |
| **Preconditions** | Nurse user exists and is authenticated. |
| **Test Steps** | 1. Authenticate test `Client` as nurse. <br>2. Issue `GET` requests to: `/admin/auth/user/`, `/admin/auth/group/`, `/admin/core/userprofile/`. <br>3. Inspect response status codes. |
| **Expected Result** | Each request returns `403 Forbidden` or a redirect to the login/error page. |
| **Pass Criteria** | `assert response.status_code in (403, 302)` for all three URLs. |

---

#### TC-S4-014-F — Non-nurse roles unaffected by nurse nav customisation

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-014-F |
| **Requirement** | FR-AA-2 |
| **PBI** | PBI-S4-04 |
| **AC** | AC-04.3 |
| **Priority** | Medium |
| **Type** | Functional — Regression |
| **Preconditions** | Admin (superuser) user exists. All model admins are registered. |
| **Test Steps** | 1. Authenticate test `Client` as administrator. <br>2. Issue `GET` to `/admin/`. <br>3. Verify that Users, Groups, UserProfiles, and Audit Logs sections remain visible. |
| **Expected Result** | All sections normally accessible to an administrator remain visible. No nurse-specific filtering is applied. |
| **Pass Criteria** | Labels for Users, Groups, and UserProfiles are all found in the response content for the administrator. |

---

## 10. Test Cases — PBI-S4-05: Doctor Patient Dashboard Listing

### FR-D-2: Doctor views list of assigned patients

---

#### TC-S4-015-F — Doctor patient queryset scoped to assigned patients

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-015-F |
| **Requirement** | FR-D-2 |
| **PBI** | PBI-S4-05 |
| **AC** | AC-05.1 |
| **Priority** | High |
| **Type** | Functional — Data Isolation |
| **Preconditions** | Doctor user exists. Patient A is `assigned_doctor` = doctor. Patient C is assigned to a different doctor. `PatientAdmin` is registered. |
| **Test Steps** | 1. Instantiate `PatientAdmin` with mock `AdminSite`. <br>2. Create `GET` request with doctor user. <br>3. Call `admin.get_queryset(request)`. |
| **Expected Result** | Queryset contains Patient A. Patient C is absent. |
| **Pass Criteria** | `assert patient_a in qs` and `assert patient_c not in qs` |

---

#### TC-S4-016-F — Doctor patient list row displays required summary columns

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-016-F |
| **Requirement** | FR-D-2, FR-D-4 |
| **PBI** | PBI-S4-05 |
| **AC** | AC-05.2 |
| **Priority** | High |
| **Type** | Functional — Display |
| **Preconditions** | `PatientAdmin.list_display` is configured with a doctor-role branch. |
| **Test Steps** | 1. Create `GET` request with doctor user. <br>2. Inspect `list_display` for doctor role. |
| **Expected Result** | `list_display` for a doctor includes: patient name, medical ID, date of birth, primary diagnosis summary, pending test result count, and next upcoming appointment date. |
| **Pass Criteria** | All six expected fields or column callables are present in the returned tuple/list. |

---

#### TC-S4-017-N — Doctor denied access to unassigned patient via direct URL

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-017-N |
| **Requirement** | FR-D-2 |
| **PBI** | PBI-S4-05 |
| **AC** | AC-05.3 |
| **Priority** | High |
| **Type** | Functional — Negative / Access Control |
| **Preconditions** | Doctor user exists. Patient C is not assigned to this doctor. |
| **Test Steps** | 1. Authenticate `Client` as doctor. <br>2. Issue `GET` to `/admin/core/patient/<patient_c_pk>/change/`. <br>3. Inspect response. |
| **Expected Result** | Response is `403 Forbidden` or a redirect; Patient C's data is not rendered. |
| **Pass Criteria** | `assert response.status_code in (403, 302)` |

---

#### TC-S4-018-F — Doctor can edit clinical fields; account fields are read-only

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-018-F |
| **Requirement** | FR-D-4 |
| **PBI** | PBI-S4-05 |
| **AC** | AC-05.4 |
| **Priority** | High |
| **Type** | Functional — Permissions |
| **Preconditions** | Doctor user and assigned Patient A exist. |
| **Test Steps** | 1. Create `GET` request with doctor user. <br>2. Call `admin.get_readonly_fields(request, patient_a)`. <br>3. Verify `diagnoses`, `procedures`, `visit_notes`, `allergies`, `chronic_conditions` are NOT in `readonly_fields`. <br>4. Verify `email`, `username` (or proxy fields) ARE in `readonly_fields`. |
| **Expected Result** | Clinical fields are editable for the doctor role; account-level fields are read-only. |
| **Pass Criteria** | Clinical field names are absent from `readonly_fields`; account-level field names are present in `readonly_fields`. |

---

## 11. Test Cases — PBI-S4-06: Doctor Recent Test Results

### FR-D-1, FR-D-3: Doctor views and sorts test results

---

#### TC-S4-019-F — Doctor test result queryset scoped to assigned patients

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-019-F |
| **Requirement** | FR-D-1 |
| **PBI** | PBI-S4-06 |
| **AC** | AC-06.1 |
| **Priority** | High |
| **Type** | Functional — Data Isolation |
| **Preconditions** | Doctor user exists. TestResult TR1 belongs to an assigned patient. TestResult TR2 belongs to a patient assigned to a different doctor. `TestResultAdmin` is registered. |
| **Test Steps** | 1. Instantiate `TestResultAdmin` with mock `AdminSite`. <br>2. Create `GET` request with doctor user. <br>3. Call `admin.get_queryset(request)`. |
| **Expected Result** | Queryset contains TR1 and excludes TR2. |
| **Pass Criteria** | `assert tr1 in qs` and `assert tr2 not in qs` |

---

#### TC-S4-020-F — Doctor test results ordered by test_date descending

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-020-F |
| **Requirement** | FR-D-3 |
| **PBI** | PBI-S4-06 |
| **AC** | AC-06.2 |
| **Priority** | High |
| **Type** | Functional — Ordering |
| **Preconditions** | Doctor user exists. At least three `TestResult` records with different `test_date` values are assigned to the doctor's patient(s). |
| **Test Steps** | 1. Create `GET` request with doctor user. <br>2. Call `admin.get_queryset(request)` and retrieve the ordered queryset. <br>3. Extract `test_date` from the first and last result. |
| **Expected Result** | Results are ordered so the most recent `test_date` appears first; `first.test_date >= last.test_date`. |
| **Pass Criteria** | `assert dates[0] >= dates[1] >= dates[2]` across the returned list. |

---

#### TC-S4-021-F — Critical test result rows are visually differentiated

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-021-F |
| **Requirement** | FR-D-1 |
| **PBI** | PBI-S4-06 |
| **AC** | AC-06.3 |
| **Priority** | Medium |
| **Type** | Functional — Display |
| **Preconditions** | A `TestResult` with `status = "critical"` exists. A `status_display` callable is defined on `TestResultAdmin`. |
| **Test Steps** | 1. Retrieve the critical `TestResult` object. <br>2. Call the `status_display` callable on the admin instance. <br>3. Inspect the returned HTML string. |
| **Expected Result** | The returned HTML contains CSS class `"critical"`, bold formatting, or a colour-coded badge indicating the critical status. |
| **Pass Criteria** | `assert "critical" in result.lower()` and result contains markup (e.g. a `<span>` or `<strong>` tag). |

---

#### TC-S4-022-F — Doctor ordering_doctor auto-set to current user on TestResult creation

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-022-F |
| **Requirement** | FR-D-1 |
| **PBI** | PBI-S4-06 |
| **AC** | AC-06.4 |
| **Priority** | High |
| **Type** | Functional — Business Logic |
| **Preconditions** | Doctor user and assigned patient exist. The `TestResultAdmin.save_model()` override sets `obj.ordering_doctor` to the request user's `UserProfile` when the doctor role is detected. |
| **Test Steps** | 1. Create a `POST` request simulating a new `TestResult` form submission as the doctor user. <br>2. Call `admin.save_model(request, obj, form, change=False)`. <br>3. Reload the object from the database. |
| **Expected Result** | `obj.ordering_doctor` equals the doctor user's `UserProfile` after save. |
| **Pass Criteria** | `assert tr.ordering_doctor == doctor_user.profile` |

---

## 12. Test Cases — PBI-S4-07: Doctor Appointment Management

### FR-D-2: Doctor views and manages appointments (closes PBI-S3-11 bug)

---

#### TC-S4-023-F — Doctor appointment queryset returns assigned patients' appointments

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-023-F |
| **Requirement** | FR-D-2 |
| **PBI** | PBI-S4-07 |
| **AC** | AC-07.1 |
| **Priority** | High |
| **Type** | Functional — Regression Fix |
| **Preconditions** | Doctor user exists. Appointment APT1 is for an assigned patient (doctor FK = doctor's UserProfile). Appointment APT2 is for an unassigned patient. `AppointmentAdmin` is registered and its `get_queryset()` bug (returning `qs.none()`) has been fixed. |
| **Test Steps** | 1. Instantiate `AppointmentAdmin` with mock `AdminSite`. <br>2. Create `GET` request with doctor user. <br>3. Call `admin.get_queryset(request)`. |
| **Expected Result** | Queryset contains APT1 and is NOT empty. APT2 is absent. |
| **Pass Criteria** | `assert qs.count() >= 1` and `assert apt1 in qs` and `assert apt2 not in qs` |

---

#### TC-S4-024-F — Doctor can edit appointment notes, status, location, type

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-024-F |
| **Requirement** | FR-D-2 |
| **PBI** | PBI-S4-07 |
| **AC** | AC-07.2 |
| **Priority** | High |
| **Type** | Functional — Permissions |
| **Preconditions** | Doctor user and assigned Appointment APT1 exist. |
| **Test Steps** | 1. Create `GET` request with doctor user and object APT1. <br>2. Call `admin.get_readonly_fields(request, apt1)`. <br>3. Verify `notes`, `status`, `location`, `appointment_type` are NOT in `readonly_fields`. |
| **Expected Result** | The four editable fields are writable for the doctor role. |
| **Pass Criteria** | None of the four field names appear in the `readonly_fields` returned for this doctor+object combination. |

---

#### TC-S4-025-N — Doctor denied access to appointment for unassigned patient

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-025-N |
| **Requirement** | FR-D-2 |
| **PBI** | PBI-S4-07 |
| **AC** | AC-07.3 |
| **Priority** | High |
| **Type** | Functional — Negative / Access Control |
| **Preconditions** | Doctor user exists. APT2 belongs to an unassigned patient. |
| **Test Steps** | 1. Authenticate `Client` as doctor. <br>2. Issue `GET` to `/admin/core/appointment/<apt2_pk>/change/`. |
| **Expected Result** | Response is `403 Forbidden` or redirect. |
| **Pass Criteria** | `assert response.status_code in (403, 302)` |

---

#### TC-S4-026-F — Appointment list filterable by status and sortable by datetime

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-026-F |
| **Requirement** | FR-D-2 |
| **PBI** | PBI-S4-07 |
| **AC** | AC-07.4 |
| **Priority** | Medium |
| **Type** | Functional — Display |
| **Preconditions** | `AppointmentAdmin.list_filter` includes `status`. `AppointmentAdmin.ordering` or `date_hierarchy` includes `appointment_datetime`. |
| **Test Steps** | 1. Create `GET` request with doctor user. <br>2. Inspect `list_filter` on `AppointmentAdmin`. <br>3. Inspect `ordering` attribute. |
| **Expected Result** | `"status"` is present in `list_filter`. `"appointment_datetime"` (ascending or descending) is present in `ordering`. |
| **Pass Criteria** | `assert "status" in admin.list_filter` and `"appointment_datetime" in admin.ordering or "-appointment_datetime" in admin.ordering` |

---

## 13. Test Cases — PBI-S4-08: Doctor Patient Search

### FR-D-6: Doctor searches patients by name or Medical Record ID

---

#### TC-S4-027-F — Doctor search by partial name returns assigned patients only

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-027-F |
| **Requirement** | FR-D-6 |
| **PBI** | PBI-S4-08 |
| **AC** | AC-08.1 |
| **Priority** | High |
| **Type** | Functional — Search |
| **Preconditions** | Doctor user exists. Patient A (assigned, first name "Alice") and Patient C (unassigned, first name "Alicia") both exist. `PatientAdmin.search_fields` is configured. |
| **Test Steps** | 1. Create `GET` search request with query `"Ali"` and doctor user via the admin changelist URL: `/admin/core/patient/?q=Ali`. <br>2. Authenticate and issue the request. <br>3. Inspect the returned changelist content. |
| **Expected Result** | Patient A appears in results. Patient C (unassigned) does not appear. |
| **Pass Criteria** | Patient A's name is in the response content; Patient C's name is not. |

---

#### TC-S4-028-F — Doctor search by Medical Record ID returns assigned patient only

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-028-F |
| **Requirement** | FR-D-6 |
| **PBI** | PBI-S4-08 |
| **AC** | AC-08.2 |
| **Priority** | High |
| **Type** | Functional — Search |
| **Preconditions** | Patient A (assigned) has `medical_id = "PMR-2025-000001"`. Patient C (unassigned) has `medical_id = "PMR-2025-000002"`. `search_fields` includes `medical_id`. |
| **Test Steps** | 1. Authenticate `Client` as doctor. <br>2. Issue `GET` to `/admin/core/patient/?q=PMR-2025`. <br>3. Inspect response content. |
| **Expected Result** | Only Patient A's record appears; Patient C is excluded because the doctor-role queryset scope is applied before the search filter. |
| **Pass Criteria** | Patient A's `medical_id` is in the response content; Patient C's `medical_id` is not. |

---

## 14. Test Cases — PBI-S4-09: Admin User Management Interface

### FR-A-5 – FR-A-12, FR-AA-4: Admin manages all user accounts

---

#### TC-S4-029-F — Admin user list shows all users across all roles

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-029-F |
| **Requirement** | FR-A-5 – FR-A-12 |
| **PBI** | PBI-S4-09 |
| **AC** | AC-09.1 |
| **Priority** | High |
| **Type** | Functional — Display |
| **Preconditions** | Admin user and at least one user from each role (patient, doctor, nurse, pharmacy) exist. `UserAdmin` is registered. |
| **Test Steps** | 1. Instantiate `UserAdmin` with mock `AdminSite`. <br>2. Create `GET` request with admin user. <br>3. Call `admin.get_queryset(request)`. |
| **Expected Result** | All users (doctor, nurse, patient, pharmacy) are present in the queryset. |
| **Pass Criteria** | `assert all_users_count == qs.count()` where `all_users_count` includes all non-admin users created. |

---

#### TC-S4-030-I — Creating user with role auto-assigns to Django Group

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-030-I |
| **Requirement** | FR-AA-4 |
| **PBI** | PBI-S4-09 |
| **AC** | AC-09.2 |
| **Priority** | High |
| **Type** | Integration — Business Logic |
| **Preconditions** | Django Groups "doctor", "nurse", "patient", "pharmacy" exist (created by `setup_groups` management command). Admin user exists. |
| **Test Steps** | 1. Simulate form submission via `admin.save_model()` creating a new user with `role = "nurse"`. <br>2. Reload the user from the database. <br>3. Inspect `user.groups.all()`. |
| **Expected Result** | The newly created user is a member of the "nurse" Django Group. |
| **Pass Criteria** | `assert nurse_group in new_user.groups.all()` |

---

#### TC-S4-031-F — Deactivated user (is_active=False) cannot log in

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-031-F |
| **Requirement** | FR-A-5 – FR-A-12 |
| **PBI** | PBI-S4-09 |
| **AC** | AC-09.3 |
| **Priority** | High |
| **Type** | Functional — Access Control |
| **Preconditions** | A doctor user exists with `is_active = True`. Admin sets `is_active = False` and saves. |
| **Test Steps** | 1. Set `user.is_active = False` and `user.save()`. <br>2. Attempt to authenticate via `django.test.Client.login(username=..., password=...)`. <br>3. Inspect the result. |
| **Expected Result** | `client.login()` returns `False`; the user cannot access authenticated pages. |
| **Pass Criteria** | `assert client.login(username="doctor_deactivated", password="...") is False` |

---

#### TC-S4-032-F — Changing user role moves them to the correct new group

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-032-F |
| **Requirement** | FR-AA-4 |
| **PBI** | PBI-S4-09 |
| **AC** | AC-09.4 |
| **Priority** | High |
| **Type** | Functional — Business Logic |
| **Preconditions** | A user with `role = "nurse"` exists and is a member of the "nurse" group. Admin changes role to "pharmacy" via `UserAdmin.save_model()`. |
| **Test Steps** | 1. Call `admin.save_model()` with the updated role "pharmacy". <br>2. Reload user. <br>3. Inspect `user.groups.all()`. |
| **Expected Result** | User is removed from "nurse" group and added to "pharmacy" group in the same operation. |
| **Pass Criteria** | `assert nurse_group not in user.groups.all()` and `assert pharmacy_group in user.groups.all()` |

---

#### TC-S4-033-N — Non-admin denied access to Users admin section

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-033-N |
| **Requirement** | FR-AA-4 |
| **PBI** | PBI-S4-09 |
| **AC** | AC-09.5 |
| **Priority** | High |
| **Type** | Functional — Negative / Access Control |
| **Preconditions** | A nurse user (non-admin) exists and is authenticated. |
| **Test Steps** | 1. Authenticate `Client` as nurse. <br>2. Issue `GET` to `/admin/auth/user/`. |
| **Expected Result** | Response is `403 Forbidden` or redirect. |
| **Pass Criteria** | `assert response.status_code in (403, 302)` |

---

## 15. Test Cases — PBI-S4-10: Admin Patient Record Management

### FR-A-1 – FR-A-4: Admin performs full CRUD on patient records

---

#### TC-S4-034-F — Admin sees all patient records regardless of assignment

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-034-F |
| **Requirement** | FR-A-1, FR-A-2 |
| **PBI** | PBI-S4-10 |
| **AC** | AC-10.1 |
| **Priority** | High |
| **Type** | Functional — Data Access |
| **Preconditions** | Admin user exists. Patient A is assigned to Doctor1. Patient B has no assigned doctor. Patient C is assigned to Doctor2. All are in the database. |
| **Test Steps** | 1. Instantiate `PatientAdmin` with mock `AdminSite`. <br>2. Create `GET` request with admin user. <br>3. Call `admin.get_queryset(request)`. |
| **Expected Result** | All three patients are present in the returned queryset. |
| **Pass Criteria** | `assert qs.count() == total_patient_count` (includes A, B, and C). |

---

#### TC-S4-035-U — New patient record receives auto-generated medical ID

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-035-U |
| **Requirement** | FR-A-1 |
| **PBI** | PBI-S4-10 |
| **AC** | AC-10.2 |
| **Priority** | High |
| **Type** | Unit — Model |
| **Preconditions** | A `UserProfile` with `role = "patient"` exists. `Patient.save()` auto-generates `medical_id` if blank. |
| **Test Steps** | 1. Create a new `Patient` record without supplying `medical_id`. <br>2. Save the record. <br>3. Reload from the database. |
| **Expected Result** | `medical_id` is set and matches the pattern `PMR-YYYY-NNNNNN` (e.g. `PMR-2025-000001`). |
| **Pass Criteria** | `import re; assert re.match(r"PMR-\d{4}-\d{6}", patient.medical_id)` |

---

#### TC-S4-036-F — Admin can edit all patient record field categories

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-036-F |
| **Requirement** | FR-A-3 |
| **PBI** | PBI-S4-10 |
| **AC** | AC-10.3 |
| **Priority** | High |
| **Type** | Functional — Permissions |
| **Preconditions** | Admin user and Patient A exist. |
| **Test Steps** | 1. Create `GET` request with admin user and object Patient A. <br>2. Call `admin.get_readonly_fields(request, patient_a)`. <br>3. Verify demographic, medical-history, allergy, diagnosis, and assigned-staff fields are NOT in `readonly_fields`. |
| **Expected Result** | All editable categories are writable for the admin role. |
| **Pass Criteria** | Representative fields (`date_of_birth`, `allergies`, `diagnoses`, `assigned_doctor`) are absent from `readonly_fields`. |

---

#### TC-S4-037-F — Admin patient deletion triggers confirmation page listing related objects

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-037-F |
| **Requirement** | FR-A-4 |
| **PBI** | PBI-S4-10 |
| **AC** | AC-10.4 |
| **Priority** | High |
| **Type** | Functional — UI Flow |
| **Preconditions** | Admin user exists. Patient A has at least one related `Medication`, one `TestResult`, one `Appointment`, and one `EmergencyContact`. |
| **Test Steps** | 1. Authenticate `Client` as admin. <br>2. Issue `POST` to `/admin/core/patient/<patient_a_pk>/delete/` (initial confirmation request). <br>3. Inspect the response content (the pre-confirm page). |
| **Expected Result** | The response contains a confirmation page listing the related objects (medication, test result, appointment, emergency contact) that will be cascade-deleted. |
| **Pass Criteria** | Response status is `200` and relevant model labels (Medication, Test Result, Appointment, Emergency Contact) appear in the response content. |

---

## 16. Test Cases — PBI-S4-11: Admin System Settings & Group Management

### FR-AA-4: Admin manages Django groups and permissions

---

#### TC-S4-038-F — Admin sees all Django groups with assigned permissions

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-038-F |
| **Requirement** | FR-AA-4 |
| **PBI** | PBI-S4-11 |
| **AC** | AC-11.1 |
| **Priority** | High |
| **Type** | Functional — Display |
| **Preconditions** | All five role groups (patient, doctor, nurse, pharmacy, admin) exist in the database. Admin user exists. `GroupAdmin` is registered. |
| **Test Steps** | 1. Authenticate `Client` as admin. <br>2. Issue `GET` to `/admin/auth/group/`. <br>3. Verify that all five group names appear in the response. |
| **Expected Result** | All five group names ("patient", "doctor", "nurse", "pharmacy", "admin") are visible in the list. |
| **Pass Criteria** | All five group names are found in `response.content`. |

---

#### TC-S4-039-I — Editing group permissions affects users on next login

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-039-I |
| **Requirement** | FR-AA-4 |
| **PBI** | PBI-S4-11 |
| **AC** | AC-11.2 |
| **Priority** | Medium |
| **Type** | Integration — Business Logic |
| **Preconditions** | A "nurse" group exists. A nurse user is a member. A specific `Permission` object (e.g. `view_patient`) is NOT currently assigned to the nurse group. |
| **Test Steps** | 1. Add the permission directly to the group via the ORM: `nurse_group.permissions.add(perm)`. <br>2. Log the nurse user out and back in (or call `user.get_all_permissions()` after clearing the cache). <br>3. Check permissions for the nurse user. |
| **Expected Result** | The `view_patient` permission is now present in the nurse user's active permission set. |
| **Pass Criteria** | `assert user.has_perm("core.view_patient")` after re-authentication. |

---

#### TC-S4-040-F — Sync User Groups action re-assigns all UserProfiles to correct groups

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-040-F |
| **Requirement** | FR-AA-4 |
| **PBI** | PBI-S4-11 |
| **AC** | AC-11.3 |
| **Priority** | High |
| **Type** | Functional — Admin Action |
| **Preconditions** | A nurse user exists but is NOT a member of the "nurse" group (mismatched state). The "Sync User Groups" admin action is defined on `UserAdmin` or `UserProfileAdmin`. |
| **Test Steps** | 1. Confirm nurse user is not in the "nurse" group: `assert nurse_group not in user.groups.all()`. <br>2. Invoke the sync action via `admin.sync_user_groups(request, queryset)`. <br>3. Reload the user from the database. <br>4. Inspect `user.groups.all()`. |
| **Expected Result** | After the sync action, the nurse user is now a member of the "nurse" group. |
| **Pass Criteria** | `assert nurse_group in user.groups.all()` |

---

#### TC-S4-041-N — Non-admin denied access to Groups admin section

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-041-N |
| **Requirement** | FR-AA-4 |
| **PBI** | PBI-S4-11 |
| **AC** | AC-11.4 |
| **Priority** | High |
| **Type** | Functional — Negative / Access Control |
| **Preconditions** | A doctor user (non-admin) exists and is authenticated. |
| **Test Steps** | 1. Authenticate `Client` as doctor. <br>2. Issue `GET` to `/admin/auth/group/`. |
| **Expected Result** | Response is `403 Forbidden` or redirect. |
| **Pass Criteria** | `assert response.status_code in (403, 302)` |

---

## 17. Test Cases — PBI-S4-12: Admin Dashboard Statistics *(Stretch)*

### FR-A-1 – FR-A-12: Admin system-wide statistics overview

---

#### TC-S4-042-F — Admin dashboard displays system-wide statistics panel

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-042-F |
| **Requirement** | FR-A-1 – FR-A-12 |
| **PBI** | PBI-S4-12 *(Stretch)* |
| **AC** | AC-12.1 |
| **Priority** | Medium |
| **Type** | Functional — Display |
| **Preconditions** | Admin user exists. Known counts of patients (3), doctors (2), nurses (2), pharmacy users (1), and pending medication orders (4) are in the database. The admin index template has been extended with a statistics panel. |
| **Test Steps** | 1. Authenticate `Client` as admin. <br>2. Issue `GET` to `/admin/`. <br>3. Inspect the response content for statistics values. |
| **Expected Result** | The page contains the correct counts for patients (3), doctors (2), nurses (2), pharmacy users (1), and pending orders (4). |
| **Pass Criteria** | Each count value appears in `response.content` within the statistics panel HTML section. |

---

#### TC-S4-043-F — Admin dashboard shows 5 most recent audit log entries

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-043-F |
| **Requirement** | FR-AA-3 |
| **PBI** | PBI-S4-12 *(Stretch)* |
| **AC** | AC-12.2 |
| **Priority** | Medium |
| **Type** | Functional — Display |
| **Preconditions** | Six `AuditLog` entries exist with different timestamps. The admin index is extended to show recent log entries. |
| **Test Steps** | 1. Authenticate `Client` as admin. <br>2. Issue `GET` to `/admin/`. <br>3. Inspect the response content for recent audit entries. |
| **Expected Result** | Exactly the 5 most recent entries (by `timestamp`) are rendered; the 6th oldest entry is not present. |
| **Pass Criteria** | The 5 most recent log entry representations appear in `response.content`. The oldest entry's identifier does not appear. |

---

## 18. Test Cases — PBI-S4-13: AuditLog Model

### FR-P-8, FR-AA-3: AuditLog model structure and immutability

---

#### TC-S4-044-U — AuditLog table exists with all required columns after migration

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-044-U |
| **Requirement** | FR-P-8, FR-AA-3 |
| **PBI** | PBI-S4-13 |
| **AC** | AC-13.1 |
| **Priority** | High |
| **Type** | Unit — Model |
| **Preconditions** | Migrations have been applied (`python manage.py migrate`). |
| **Test Steps** | 1. Import `AuditLog` from `core.models`. <br>2. Inspect `AuditLog._meta.get_fields()`. <br>3. Verify each required field name is present. |
| **Expected Result** | All required fields exist on the model: `id`, `user` (FK, nullable), `action` (choices: read/create/update/delete), `model_name`, `object_id`, `object_repr`, `ip_address`, `timestamp`, `changes_summary`. |
| **Pass Criteria** | All nine field names are found in the set of field names returned by `{f.name for f in AuditLog._meta.get_fields()}`. |

---

#### TC-S4-045-U — AuditLog entry is immutable — cannot be updated after creation

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-045-U |
| **Requirement** | FR-P-8, FR-AA-3 |
| **PBI** | PBI-S4-13 |
| **AC** | AC-13.2 |
| **Priority** | High |
| **Type** | Unit — Model |
| **Preconditions** | An `AuditLog` entry has been created and saved (has a PK). |
| **Test Steps** | 1. Create a valid `AuditLog` entry and save it. <br>2. Modify `entry.action = "delete"`. <br>3. Call `entry.save()`. <br>4. Inspect whether an exception is raised or the modification is silently rejected. |
| **Expected Result** | Calling `save()` on an existing `AuditLog` entry raises a `ValueError` (or similar exception) or silently ignores the update, leaving the original record unchanged in the database. |
| **Pass Criteria** | Either `with pytest.raises((ValueError, PermissionError)):` passes, or after the call, `AuditLog.objects.get(pk=entry.pk).action == "read"` (original value unchanged). |

---

#### TC-S4-046-U — AuditLog timestamp auto-set to UTC on creation and cannot be overridden

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-046-U |
| **Requirement** | FR-P-8 |
| **PBI** | PBI-S4-13 |
| **AC** | AC-13.3 |
| **Priority** | High |
| **Type** | Unit — Model |
| **Preconditions** | `AuditLog.timestamp` is defined as `auto_now_add=True` or equivalent. |
| **Test Steps** | 1. Note the current UTC time: `before = timezone.now()`. <br>2. Create and save an `AuditLog` entry without passing `timestamp`. <br>3. Note the time again: `after = timezone.now()`. <br>4. Reload the entry and inspect `entry.timestamp`. |
| **Expected Result** | `entry.timestamp` is between `before` and `after`. Passing an explicit `timestamp` value in the constructor does not override it. |
| **Pass Criteria** | `assert before <= entry.timestamp <= after` |

---

#### TC-S4-047-U — AuditLog migration applies cleanly to a fresh schema

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-047-U |
| **Requirement** | FR-P-8 |
| **PBI** | PBI-S4-13 |
| **AC** | AC-13.4 |
| **Priority** | High |
| **Type** | Unit — Migration |
| **Preconditions** | The `AuditLog` migration file exists in `core/migrations/`. |
| **Test Steps** | 1. Run `python manage.py migrate --run-syncdb` in a fresh test database environment. <br>2. Inspect the exit code and any error messages. |
| **Expected Result** | `migrate` completes with exit code `0` and no error output. The `core_auditlog` table exists in the schema. |
| **Pass Criteria** | Command exits with code `0`; no `MigrationError` or SQL error is raised. |

---

## 19. Test Cases — PBI-S4-14: Log Data Access (Read) Events

### FR-AA-2, FR-AA-3: Read events on sensitive detail pages are logged

---

#### TC-S4-048-I — Opening a Patient detail page creates an AuditLog read entry

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-048-I |
| **Requirement** | FR-AA-2, FR-AA-3 |
| **PBI** | PBI-S4-14 |
| **AC** | AC-14.1 |
| **Priority** | High |
| **Type** | Integration — Audit Logging |
| **Preconditions** | Admin user and Patient A exist. `PatientAdmin.change_view()` is overridden to write a read `AuditLog` entry. `AuditLog` model exists. |
| **Test Steps** | 1. Note `AuditLog.objects.count()` before the request. <br>2. Authenticate `Client` as admin. <br>3. Issue `GET` to `/admin/core/patient/<patient_a_pk>/change/`. <br>4. Query `AuditLog.objects.filter(action="read", model_name="Patient", object_id=str(patient_a.pk))`. |
| **Expected Result** | A new `AuditLog` entry exists with `action="read"`, `model_name="Patient"`, `object_id=str(patient_a.pk)`, and `user=admin_user`. |
| **Pass Criteria** | `assert log_entry.action == "read"` and `assert log_entry.user == admin_user` |

---

#### TC-S4-049-I — Opening TestResult, Medication, or Appointment detail creates read entry

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-049-I |
| **Requirement** | FR-AA-3 |
| **PBI** | PBI-S4-14 |
| **AC** | AC-14.2 |
| **Priority** | High |
| **Type** | Integration — Audit Logging |
| **Preconditions** | Admin user, one `TestResult`, one `Medication`, and one `Appointment` exist. All three `ModelAdmin` classes have `change_view()` overrides to write read log entries. |
| **Test Steps** | 1. For each object (TestResult TR1, Medication M1, Appointment APT1): authenticate, issue `GET` to its change URL, verify a `AuditLog` read entry was created for the correct model and object ID. |
| **Expected Result** | Three `AuditLog` entries exist after the three requests, one for each model/object combination. |
| **Pass Criteria** | `AuditLog.objects.filter(action="read", model_name__in=["TestResult","Medication","Appointment"]).count() == 3` |

---

#### TC-S4-050-N — Viewing a list page does NOT create an AuditLog entry

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-050-N |
| **Requirement** | FR-AA-3 |
| **PBI** | PBI-S4-14 |
| **AC** | AC-14.3 |
| **Priority** | High |
| **Type** | Functional — Negative |
| **Preconditions** | Admin user exists. No `AuditLog` entries exist before the test. `PatientAdmin` changelist view does not log. |
| **Test Steps** | 1. Authenticate `Client` as admin. <br>2. Issue `GET` to `/admin/core/patient/` (the list/changelist page). <br>3. Count `AuditLog.objects.count()`. |
| **Expected Result** | No new `AuditLog` entries are created by the list page request. |
| **Pass Criteria** | `assert AuditLog.objects.count() == 0` (or same as before). |

---

#### TC-S4-051-F — Read log entry captures client IP from REMOTE_ADDR

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-051-F |
| **Requirement** | FR-AA-3 |
| **PBI** | PBI-S4-14 |
| **AC** | AC-14.4 |
| **Priority** | High |
| **Type** | Functional — Security |
| **Preconditions** | Admin user and Patient A exist. The `change_view()` override extracts IP from `request.META["REMOTE_ADDR"]`. |
| **Test Steps** | 1. Create a `GET` request using `RequestFactory().get("/", REMOTE_ADDR="192.168.1.100")`. <br>2. Simulate `PatientAdmin.change_view()`. <br>3. Query the created `AuditLog` entry. |
| **Expected Result** | `AuditLog.ip_address == "192.168.1.100"`. The IP is captured server-side from the request object, not from a user-controlled header. |
| **Pass Criteria** | `assert log_entry.ip_address == "192.168.1.100"` |

---

## 20. Test Cases — PBI-S4-15: Log Data Modification Events

### FR-P-8: Write events are logged with field-level change summaries

---

#### TC-S4-052-I — Saving an existing record creates an update log with old/new field values

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-052-I |
| **Requirement** | FR-P-8 |
| **PBI** | PBI-S4-15 |
| **AC** | AC-15.1 |
| **Priority** | High |
| **Type** | Integration — Audit Logging |
| **Preconditions** | Admin user and Patient A (`phone_primary = "1234567890"`) exist. `PatientAdmin.save_model()` is overridden to diff fields and write an `AuditLog` update entry. |
| **Test Steps** | 1. Simulate changing `patient_a.phone_primary` to `"0987654321"` via `admin.save_model()`. <br>2. Query the `AuditLog` entry with `action="update"` and `object_id=patient_a.pk`. |
| **Expected Result** | An `AuditLog` entry exists with `action="update"`, and its `changes_summary` field records the change: `phone_primary: "1234567890" → "0987654321"`. |
| **Pass Criteria** | `assert "phone_primary" in log_entry.changes_summary` and both old and new values appear in the summary. |

---

#### TC-S4-053-I — Creating a new record writes an AuditLog create entry

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-053-I |
| **Requirement** | FR-P-8 |
| **PBI** | PBI-S4-15 |
| **AC** | AC-15.2 |
| **Priority** | High |
| **Type** | Integration — Audit Logging |
| **Preconditions** | Admin user exists. `save_model()` is overridden for `change=False` (new object) to write a create log. |
| **Test Steps** | 1. Simulate creating a new `Medication` via `admin.save_model(request, new_med, form, change=False)`. <br>2. Query `AuditLog.objects.filter(action="create", model_name="Medication")`. |
| **Expected Result** | An `AuditLog` entry with `action="create"` is found and its `object_repr` contains the new medication's string representation. |
| **Pass Criteria** | `assert log_entry.action == "create"` and `assert str(new_med) in log_entry.object_repr` |

---

#### TC-S4-054-I — Deleting a record writes an AuditLog delete entry

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-054-I |
| **Requirement** | FR-P-8 |
| **PBI** | PBI-S4-15 |
| **AC** | AC-15.3 |
| **Priority** | High |
| **Type** | Integration — Audit Logging |
| **Preconditions** | Admin user and Appointment APT1 exist. `AppointmentAdmin.delete_model()` is overridden to write a delete log. |
| **Test Steps** | 1. Note `str(apt1)` before deletion. <br>2. Call `admin.delete_model(request, apt1)`. <br>3. Query `AuditLog.objects.filter(action="delete", model_name="Appointment")`. |
| **Expected Result** | An `AuditLog` entry with `action="delete"` exists, and its `object_repr` contains the pre-deletion string representation of the appointment. |
| **Pass Criteria** | `assert log_entry.action == "delete"` and `assert repr_before_deletion in log_entry.object_repr` |

---

#### TC-S4-055-F — Modification log entry correctly identifies the authenticated user

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-055-F |
| **Requirement** | FR-P-8 |
| **PBI** | PBI-S4-15 |
| **AC** | AC-15.4 |
| **Priority** | High |
| **Type** | Functional — Business Logic |
| **Preconditions** | Two admin users (Admin1, Admin2) exist. Admin2 performs a modification action. |
| **Test Steps** | 1. Create a request with `request.user = admin2`. <br>2. Call `admin.save_model(request, obj, form, change=True)`. <br>3. Query the resulting `AuditLog` entry's `user` field. |
| **Expected Result** | `log_entry.user == admin2` — not Admin1 or any other user. |
| **Pass Criteria** | `assert log_entry.user == admin2` |

---

## 21. Test Cases — PBI-S4-16: Admin Audit Log Viewer

### FR-AA-3: Admin can view and filter audit log entries

---

#### TC-S4-056-F — Admin audit log list shows all entries with required columns

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-056-F |
| **Requirement** | FR-AA-3 |
| **PBI** | PBI-S4-16 |
| **AC** | AC-16.1 |
| **Priority** | High |
| **Type** | Functional — Display |
| **Preconditions** | Admin user exists. Three `AuditLog` entries exist. `AuditLogAdmin` is registered with `list_display` covering: timestamp, user, action, model_name, object_id, object_repr, ip_address. |
| **Test Steps** | 1. Create a `GET` request with admin user. <br>2. Inspect `AuditLogAdmin.list_display`. |
| **Expected Result** | `list_display` contains all seven required column names. |
| **Pass Criteria** | All seven field names (or their equivalent callables) are present in `list_display`. |

---

#### TC-S4-057-F — Admin can filter audit log by action, user, model, and date range

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-057-F |
| **Requirement** | FR-AA-3 |
| **PBI** | PBI-S4-16 |
| **AC** | AC-16.2 |
| **Priority** | High |
| **Type** | Functional — Filtering |
| **Preconditions** | `AuditLogAdmin` is configured with `list_filter` including `action`, `user`, `model_name`, and `date_hierarchy = "timestamp"`. |
| **Test Steps** | 1. Inspect `AuditLogAdmin.list_filter`. <br>2. Inspect `AuditLogAdmin.date_hierarchy`. |
| **Expected Result** | `list_filter` contains `"action"`, `"user"`, and `"model_name"`. `date_hierarchy` is set to `"timestamp"`. |
| **Pass Criteria** | `assert all(f in admin.list_filter for f in ["action", "user", "model_name"])` and `assert admin.date_hierarchy == "timestamp"` |

---

#### TC-S4-058-F — Individual audit log entry detail page is read-only

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-058-F |
| **Requirement** | FR-AA-3 |
| **PBI** | PBI-S4-16 |
| **AC** | AC-16.3 |
| **Priority** | High |
| **Type** | Functional — Permissions |
| **Preconditions** | Admin user and one `AuditLog` entry exist. `AuditLogAdmin` has `readonly_fields` set for all fields. |
| **Test Steps** | 1. Create `GET` request with admin user. <br>2. Call `admin.has_change_permission(request, log_entry)`. <br>3. Call `admin.has_delete_permission(request, log_entry)`. <br>4. Call `admin.has_add_permission(request)`. |
| **Expected Result** | All three permission checks return `False`. No write controls are available for any role. |
| **Pass Criteria** | `assert not admin.has_change_permission(request, log_entry)` <br>`assert not admin.has_delete_permission(request, log_entry)` <br>`assert not admin.has_add_permission(request)` |

---

#### TC-S4-059-N — Non-admin denied access to Audit Logs admin section

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-059-N |
| **Requirement** | FR-AA-3 |
| **PBI** | PBI-S4-16 |
| **AC** | AC-16.4 |
| **Priority** | High |
| **Type** | Functional — Negative / Access Control |
| **Preconditions** | A pharmacy user (non-admin) exists and is authenticated. |
| **Test Steps** | 1. Authenticate `Client` as pharmacy user. <br>2. Issue `GET` to `/admin/core/auditlog/`. |
| **Expected Result** | Response is `403 Forbidden` or redirect. |
| **Pass Criteria** | `assert response.status_code in (403, 302)` |

---

#### TC-S4-060-F — Audit log default ordering is by timestamp descending

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-060-F |
| **Requirement** | FR-AA-3 |
| **PBI** | PBI-S4-16 |
| **AC** | AC-16.5 |
| **Priority** | Medium |
| **Type** | Functional — Ordering |
| **Preconditions** | At least three `AuditLog` entries exist with distinct timestamps. `AuditLogAdmin` has `ordering = ("-timestamp",)`. |
| **Test Steps** | 1. Instantiate `AuditLogAdmin` with mock `AdminSite`. <br>2. Create `GET` request with admin user. <br>3. Call `admin.get_queryset(request)` and inspect the first and last items. |
| **Expected Result** | The first result has the most recent `timestamp`; the last result has the oldest `timestamp`. |
| **Pass Criteria** | `assert qs.first().timestamp >= qs.last().timestamp` |

---

## 22. Test Cases — PBI-S4-17: Drug–Allergy Risk Scoring Engine

### FR-Ph-4, FR-Ph-5: Full algorithmic component implementation

---

#### TC-S4-061-U — Exact name match sets risk_level=critical, risk_score=100

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-061-U |
| **Requirement** | FR-Ph-4 |
| **PBI** | PBI-S4-17 |
| **AC** | AC-17.1 |
| **Priority** | High |
| **Type** | Unit — Algorithm |
| **Preconditions** | `DrugAllergyRiskEngine` service class is implemented. A patient's `allergies` field contains `"Penicillin"`. A `Medication` with `medication_name = "penicillin"` is about to be saved. |
| **Test Steps** | 1. Instantiate `DrugAllergyRiskEngine`. <br>2. Call `engine.evaluate(medication_name="penicillin", allergies_text="Penicillin")`. <br>3. Inspect the returned result dict/namedtuple. |
| **Expected Result** | `result.risk_level == "critical"` and `result.risk_score == 100`. |
| **Pass Criteria** | `assert result.risk_level == "critical"` and `assert result.risk_score == 100` |

---

#### TC-S4-062-U — Drug-class cross-reactivity match sets risk_level=high, risk_score=75

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-062-U |
| **Requirement** | FR-Ph-4 |
| **PBI** | PBI-S4-17 |
| **AC** | AC-17.2 |
| **Priority** | High |
| **Type** | Unit — Algorithm |
| **Preconditions** | `DrugAllergyRiskEngine` has drug-class dictionary mapping `"amoxicillin"` → `"penicillin"`. Patient allergies field contains `"penicillin"` (class name). Medication name is `"Amoxicillin"`. |
| **Test Steps** | 1. Call `engine.evaluate(medication_name="Amoxicillin", allergies_text="penicillin")`. <br>2. Inspect result. |
| **Expected Result** | `result.risk_level == "high"` and `result.risk_score == 75`. No exact name match exists; class match fired. |
| **Pass Criteria** | `assert result.risk_level == "high"` and `assert result.risk_score == 75` |

---

#### TC-S4-063-U — Fuzzy edit-distance match sets risk_level=medium, risk_score=50

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-063-U |
| **Requirement** | FR-Ph-4 |
| **PBI** | PBI-S4-17 |
| **AC** | AC-17.3 |
| **Priority** | High |
| **Type** | Unit — Algorithm |
| **Preconditions** | Patient allergies text contains `"asprin"` (misspelling of "aspirin"). Medication name is `"aspirin"`. No exact or class match exists. Edit distance between `"asprin"` and `"aspirin"` is 1 (≤ threshold of 2). |
| **Test Steps** | 1. Call `engine.evaluate(medication_name="aspirin", allergies_text="asprin")`. <br>2. Inspect result. |
| **Expected Result** | `result.risk_level == "medium"` and `result.risk_score == 50`. |
| **Pass Criteria** | `assert result.risk_level == "medium"` and `assert result.risk_score == 50` |

---

#### TC-S4-064-U — No strategy match sets risk_level=safe, risk_score=0, allergy_conflict=False

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-064-U |
| **Requirement** | FR-Ph-4 |
| **PBI** | PBI-S4-17 |
| **AC** | AC-17.4 |
| **Priority** | High |
| **Type** | Unit — Algorithm |
| **Preconditions** | Patient allergies text is `"latex"`. Medication name is `"Metformin"` (no class, no fuzzy match). |
| **Test Steps** | 1. Call `engine.evaluate(medication_name="Metformin", allergies_text="latex")`. <br>2. Inspect result. |
| **Expected Result** | `result.risk_level == "safe"`, `result.risk_score == 0`, and `result.allergy_conflict == False`. |
| **Pass Criteria** | `assert result.risk_level == "safe"` and `assert result.risk_score == 0` and `assert result.allergy_conflict is False` |

---

#### TC-S4-065-U — Highest score across all strategies determines final risk_level

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-065-U |
| **Requirement** | FR-Ph-4 |
| **PBI** | PBI-S4-17 |
| **AC** | AC-17.5 |
| **Priority** | High |
| **Type** | Unit — Algorithm |
| **Preconditions** | A scenario where both Strategy B (score 75) and Strategy C (score 50) fire but Strategy A (score 100) does not (no exact name match). |
| **Test Steps** | 1. Construct allergies text so the fuzzy match fires (score 50) and the class match fires (score 75). <br>2. Call `engine.evaluate()` with that combination. <br>3. Inspect `result.risk_score`. |
| **Expected Result** | `result.risk_score == 75` (highest from class match), and `result.risk_level == "high"`. The fuzzy score (50) is subordinated. |
| **Pass Criteria** | `assert result.risk_score == 75` and `assert result.risk_level == "high"` |

---

#### TC-S4-066-F — Pharmacy view shows risk-level warning banner for non-safe medications

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-066-F |
| **Requirement** | FR-Ph-5 |
| **PBI** | PBI-S4-17 |
| **AC** | AC-17.6 |
| **Priority** | High |
| **Type** | Functional — UI |
| **Preconditions** | A `Medication` with `risk_level = "high"` and `risk_score = 75` exists. The `MedicationAdmin.change_view()` injects a warning banner context variable for non-safe risk levels. A pharmacy user has view permission on this medication. |
| **Test Steps** | 1. Authenticate `Client` as pharmacy user. <br>2. Issue `GET` to `/admin/core/medication/<med_pk>/change/`. <br>3. Inspect response content for the warning banner. |
| **Expected Result** | The response contains a banner/alert indicating the risk level ("HIGH"), the matched allergen, and the strategy that fired. |
| **Pass Criteria** | `assert "HIGH" in response.content.decode()` and the matched allergen token appears in the content. |

---

#### TC-S4-067-F — Doctor prescription form shows allergy alert for matching patient

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-067-F |
| **Requirement** | FR-Ph-5 |
| **PBI** | PBI-S4-17 |
| **AC** | AC-17.7 |
| **Priority** | High |
| **Type** | Functional — UI |
| **Preconditions** | Doctor user exists. Assigned patient has `allergies = "penicillin"`. Doctor is creating or viewing a `Medication` with `medication_name = "Amoxicillin"` (class match → HIGH). The `MedicationAdmin.change_view()` injects alert context for doctors. |
| **Test Steps** | 1. Authenticate `Client` as doctor. <br>2. Issue `GET` to `/admin/core/medication/<med_pk>/change/` (for the matching medication). <br>3. Inspect response for alert message. |
| **Expected Result** | An alert message is rendered in the change-form context before rendering, indicating the allergy risk level. |
| **Pass Criteria** | An allergy alert string (e.g. "allergy", "risk", or the risk level name) is present in `response.content.decode()`. |

---

#### TC-S4-068-U — DrugAllergyRiskEngine returns correct class for known drug name

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-068-U |
| **Requirement** | FR-Ph-4 |
| **PBI** | PBI-S4-17 |
| **AC** | AC-17.8 |
| **Priority** | High |
| **Type** | Unit — Algorithm |
| **Preconditions** | `DrugAllergyRiskEngine` has a `DRUG_CLASS_MAP` dictionary with at least 30 drugs across 6 classes. |
| **Test Steps** | 1. Query: `engine.get_drug_class("Ceftriaxone")`. <br>2. Inspect the returned class name. |
| **Expected Result** | Returns `"cephalosporin"` (case-insensitive match). |
| **Pass Criteria** | `assert engine.get_drug_class("Ceftriaxone").lower() == "cephalosporin"` |

---

#### TC-S4-069-U — Allergy tokens normalised from mixed separators and whitespace

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-069-U |
| **Requirement** | FR-Ph-4 |
| **PBI** | PBI-S4-17 |
| **AC** | AC-17.9 |
| **Priority** | High |
| **Type** | Unit — Algorithm |
| **Preconditions** | A patient's `allergies` field contains mixed-format text: `"  Penicillin , LATEX ; Sulfa\nAspirin  "`. |
| **Test Steps** | 1. Call `engine._normalise_allergies("  Penicillin , LATEX ; Sulfa\nAspirin  ")`. <br>2. Inspect the returned list of tokens. |
| **Expected Result** | Returns a list of four lowercase, stripped tokens: `["penicillin", "latex", "sulfa", "aspirin"]`. No extra whitespace, no empty strings. |
| **Pass Criteria** | `assert sorted(tokens) == ["aspirin", "latex", "penicillin", "sulfa"]` |

---

#### TC-S4-070-U — Medication migration adding risk_level and risk_score applies cleanly

| Field | Detail |
|-------|--------|
| **Test ID** | TC-S4-070-U |
| **Requirement** | FR-Ph-4 |
| **PBI** | PBI-S4-17 |
| **AC** | AC-17.10 |
| **Priority** | High |
| **Type** | Unit — Migration |
| **Preconditions** | The migration file adding `risk_level` (CharField, choices: safe/medium/high/critical) and `risk_score` (IntegerField, default 0) to the `Medication` model has been created. |
| **Test Steps** | 1. Run `python manage.py migrate` against a fresh schema. <br>2. Inspect migration output for errors. <br>3. Check the `Medication` model's fields in the live schema. |
| **Expected Result** | Migration completes with exit code `0`. `Medication._meta.get_field("risk_level")` and `Medication._meta.get_field("risk_score")` return valid field objects without raising `FieldDoesNotExist`. |
| **Pass Criteria** | `Medication._meta.get_field("risk_level")` does not raise; `Medication._meta.get_field("risk_score")` does not raise. |

---

## 23. Test File Mapping

This table maps each planned test file to the test cases it will contain and whether it builds on an existing file or is new.

| Test File | Test Cases | FR Coverage | Status |
|-----------|-----------|-------------|--------|
| `app/tests/test_nurse_patient_view.py` | TC-S4-001 – TC-S4-004 | FR-N-1 | New |
| `app/tests/test_nurse_medication_view.py` | TC-S4-005 – TC-S4-009 | FR-N-2 | New |
| `app/tests/test_nurse_contact_view.py` | TC-S4-010 – TC-S4-011 | FR-N-3 | New |
| `app/tests/test_nurse_nav_customisation.py` | TC-S4-012 – TC-S4-014 | FR-AA-2 | New |
| `app/tests/test_doctor_patient_dashboard.py` | TC-S4-015 – TC-S4-018 | FR-D-2, FR-D-4 | New |
| `app/tests/test_doctor_test_results.py` | TC-S4-019 – TC-S4-022 | FR-D-1, FR-D-3 | New |
| `app/tests/test_doctor_appointments.py` | TC-S4-023 – TC-S4-026 | FR-D-2 (appointments) | Extends `test_appointment_model.py` |
| `app/tests/test_doctor_patient_search.py` | TC-S4-027 – TC-S4-028 | FR-D-6 | New |
| `app/tests/test_admin_user_management.py` | TC-S4-029 – TC-S4-033 | FR-A-5 – FR-A-12, FR-AA-4 | Extends `test_permissions.py` |
| `app/tests/test_admin_patient_management.py` | TC-S4-034 – TC-S4-037 | FR-A-1 – FR-A-4 | Extends `test_access_control.py` |
| `app/tests/test_admin_group_management.py` | TC-S4-038 – TC-S4-041 | FR-AA-4 | New |
| `app/tests/test_admin_dashboard_stats.py` | TC-S4-042 – TC-S4-043 | FR-A-1 – FR-A-12 *(stretch)* | New |
| `app/tests/test_audit_log_model.py` | TC-S4-044 – TC-S4-047 | FR-P-8, FR-AA-3 | New |
| `app/tests/test_audit_log_read_events.py` | TC-S4-048 – TC-S4-051 | FR-AA-2, FR-AA-3 | New |
| `app/tests/test_audit_log_write_events.py` | TC-S4-052 – TC-S4-055 | FR-P-8 | New |
| `app/tests/test_audit_log_viewer.py` | TC-S4-056 – TC-S4-060 | FR-AA-3 | New |
| `app/tests/test_drug_allergy_engine.py` | TC-S4-061 – TC-S4-070 | FR-Ph-4, FR-Ph-5 | Extends `test_allergy_conflict_detection.py` |

**Total test cases: 70** (TC-S4-001 through TC-S4-070)  
**Core PBIs covered: 16** (PBI-S4-01 through PBI-S4-17, excluding stretch PBI-S4-12)  
**Stretch PBI covered: 1** (PBI-S4-12 — TC-S4-042 – TC-S4-043)  
**Functional requirements fully covered: 28**

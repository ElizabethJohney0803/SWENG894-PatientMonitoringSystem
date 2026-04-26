# Patient Monitoring System - Test Suite

Complete automated test suite for the Patient Monitoring System. Covers all four sprints of the project: role-based authentication, patient/pharmacy/doctor/nurse workflows, audit logging, and the Drug-Allergy Risk Scoring Engine.

**Total tests: 704 | Pass rate: 100% | Coverage (app modules): 84%**

---

## Test Files

### Core / Sprint 1

| File | Tests | What it covers |
|------|-------|----------------|
| `test_models.py` | 41 | UserProfile model — creation, role properties, group assignment, completeness |
| `test_forms.py` | 12 | CustomUserCreationForm — all roles, validation, password rules, field exclusion |
| `test_permissions.py` | 25 | AdminOnly / PatientAccess / MedicalStaff / DoctorOnly mixins |
| `test_integration.py` | 24 | End-to-end user creation and role-change workflows |

### Patient Workflows / Sprint 2

| File | Tests | What it covers |
|------|-------|----------------|
| `test_patient_role_admin_interface.py` | 57 | Patient-role admin view — read-only fields, data isolation, fieldsets |
| `test_patient_admin_access.py` | 21 | HTTP-level access control for patient admin URLs |
| `test_patient_admin_templates.py` | 11 | Admin template rendering for patient role |
| `test_patient_appointment_view.py` | 16 | Patient view of upcoming appointments |
| `test_medical_history.py` | 88 | Medical history CRUD — diagnoses, procedures, visit notes |

### Pharmacy Workflows / Sprint 3

| File | Tests | What it covers |
|------|-------|----------------|
| `test_pharmacy_medication_orders.py` | 9 | Pharmacy views medication orders |
| `test_pharmacy_allergy_information.py` | 13 | Pharmacy views patient allergy information |
| `test_pharmacy_fulfillment_status.py` | 12 | Medication fulfillment status updates |
| `test_pharmacy_dosage_notes.py` | 10 | Dosage and administration notes display |
| `test_allergy_conflict_detection.py` | 14 | Basic allergy-conflict flag on medication save |
| `test_allergy_conflict_warning.py` | 8 | Allergy conflict warning indicator in admin list |
| `test_doctor_prescription_workflow.py` | 11 | Doctor prescription creation and allergy alert |

### Doctor / Nurse / Appointment Workflows / Sprint 3-4

| File | Tests | What it covers |
|------|-------|----------------|
| `test_access_control.py` | 71 | Role-scoped querysets and HTTP access for all roles across Patient, Medication, TestResult |
| `test_admin_search_filtering.py` | 34 | Doctor/admin patient search by name and Medical Record ID; list filters |
| `test_appointment_model.py` | 21 | Appointment model constraints and field validation |
| `test_appointment_admin.py` | 13 | AppointmentAdmin queryset and edit rights per role |
| `test_nurse_appointment_view.py` | 12 | Nurse appointment view and navigation scope |
| `test_testresult_model.py` | 63 | TestResult model, admin queryset, chronological ordering, critical status display |
| `test_patient_doctor_assignment_admin.py` | 17 | Doctor-patient assignment via admin |
| `test_patient_doctor_assignment_integration.py` | 10 | End-to-end doctor-patient assignment |
| `test_patient_doctor_assignment_commands.py` | 13 | `assign_patients` management command |

### Audit Logging / Sprint 4

| File | Tests | What it covers |
|------|-------|----------------|
| `test_audit_log_admin.py` | 16 | AuditLog model immutability, AuditLogAdmin list/filter/readonly, non-admin denial |

### Drug-Allergy Risk Scoring Engine / Sprint 4

| File | Tests | What it covers |
|------|-------|----------------|
| `test_drug_allergy_engine.py` | 44 | DrugAllergyRiskEngine — exact match (score 100), cross-reactivity (score 75), fuzzy edit-distance (score 50), SAFE path, token normalisation |

### Admin Dashboard / Sprint 4

| File | Tests | What it covers |
|------|-------|----------------|
| `test_admin_dashboard.py` | 7 | Admin dashboard statistics panel — counts, recent audit logs, non-admin exclusion |

### Infrastructure

| File | Tests | What it covers |
|------|-------|----------------|
| `test_migrations.py` | 11 | Migration smoke tests — AuditLog table, risk_level/risk_score fields apply cleanly |

---

## Shared Fixtures (`conftest.py`)

| Fixture | Description |
|---------|-------------|
| `create_groups` | Creates all required Django groups (Patients, Doctors, Nurses, Pharmacy, Admins) |
| `admin_user` | Admin-role user with `is_staff=True` |
| `doctor_user` | Doctor-role user with license number and cardiology department |
| `nurse_user` | Nurse-role user with license number and emergency department |
| `patient_user` | Patient-role user |
| `pharmacy_user` | Pharmacy-role user with license number |
| `patient_record` | Patient model instance assigned to `doctor_user` |

---

## Running Tests

The test suite runs inside the Docker container. Start it first if it is not already running:

```bash
docker compose up -d
```

**Run all tests:**
```bash
docker compose exec pms_web python -m pytest tests/ -v
```

**Run all tests (quiet summary only):**
```bash
docker compose exec pms_web python -m pytest tests/ -q
```

**Run a single test file:**
```bash
docker compose exec pms_web python -m pytest tests/test_drug_allergy_engine.py -v
```

**Run a single test class or method:**
```bash
docker compose exec pms_web python -m pytest tests/test_access_control.py::TestPatientAdminQuerysetFiltering -v
docker compose exec pms_web python -m pytest tests/test_access_control.py::TestPatientAdminQuerysetFiltering::test_nurse_sees_own_assigned_patients -v
```

**Run by marker:**
```bash
docker compose exec pms_web python -m pytest tests/ -m unit -v
docker compose exec pms_web python -m pytest tests/ -m integration -v
docker compose exec pms_web python -m pytest tests/ -m admin -v
docker compose exec pms_web python -m pytest tests/ -m permissions -v
```

**Coverage report (app modules only — excludes migrations and management commands):**
```bash
docker compose exec pms_web sh -c "
cat > /tmp/covrc << 'EOF'
[run]
omit =
    */migrations/*
    */management/*
    */tests.py
    */views.py
EOF
python -m pytest tests/ --cov=core --cov-report=term-missing --cov-config=/tmp/covrc -q
"
```

**Verbose output with full tracebacks on failure:**
```bash
docker compose exec pms_web python -m pytest tests/ -v --tb=long
```

---

## Test Markers

| Marker | Purpose |
|--------|---------|
| `@pytest.mark.unit` | Isolated model/service/utility tests |
| `@pytest.mark.integration` | Multi-component interaction tests |
| `@pytest.mark.system` | End-to-end workflow tests |
| `@pytest.mark.models` | Django model tests |
| `@pytest.mark.forms` | Form validation tests |
| `@pytest.mark.permissions` | Access-control and mixin tests |
| `@pytest.mark.admin` | Django admin interface tests |

---

## Code Coverage

Coverage is measured against active application modules only (migrations, management commands, and placeholder stubs are excluded).

| Module | Coverage |
|--------|----------|
| `core/models.py` | 97% |
| `core/admin.py` | 80% |
| `core/mixins.py` | 84% |
| `core/services/drug_allergy_engine.py` | 98% |
| `core/apps.py` | 100% |
| **Total (app modules)** | **84%** |

---

## Test Environment

| Attribute | Value |
|-----------|-------|
| Framework | pytest 9.0.3 + pytest-django 4.12.0 |
| Python | 3.11.4 |
| Django | 4.2.10 |
| Database | SQLite in-memory |
| Settings module | `patient_monitoring_system.settings_test` |
| Config file | `pytest.ini` |

---

## Debugging

**Show print output during tests:**
```bash
docker compose exec pms_web python -m pytest tests/ -s
```

**Drop into pdb on first failure:**
```bash
docker compose exec pms_web python -m pytest tests/ --pdb
```

**Stop after the first failure:**
```bash
docker compose exec pms_web python -m pytest tests/ -x
```

## Test Data

Tests use realistic hospital scenarios:
- **Departments**: Cardiology, Emergency, Surgery, Neurology, Pediatrics, ICU
- **License Numbers**: MD123456 (doctors), RN123456 (nurses), PH123456 (pharmacy)  
- **Roles**: All five system roles (patient, doctor, nurse, pharmacy, admin)
- **Permissions**: Complete role-based permission matrix

This test suite ensures the Patient Monitoring System maintains security, data integrity, and proper role-based access control across all user interactions.
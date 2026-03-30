# Patient Monitoring System - Test Suite

This comprehensive test suite covers all aspects of the Patient Monitoring System's role-based authentication and user management functionality.

## Test Categories

### Unit Tests (tests/test_models.py)
- **UserProfile Model**: Creation, validation, properties, group assignment
- **Role Properties**: Testing medical staff, patient access, prescription rights
- **Profile Completeness**: Required field validation for different roles
- **Group Assignment**: Automatic assignment and reassignment on role changes

### Form Tests (tests/test_forms.py)  
- **CustomUserCreationForm**: All role types (doctor, nurse, patient, pharmacy, admin)
- **Validation Logic**: Role-specific required fields (license, department)
- **Password Security**: Complex password requirements and matching
- **Field Exclusion**: License field handling for patients

### Permission Tests (tests/test_permissions.py)
- **Admin Interface Access**: Module permissions for different roles
- **Role-Based Mixins**: AdminOnly, PatientAccess, MedicalStaff, DoctorOnly
- **Queryset Filtering**: Users can only see appropriate data
- **CRUD Permissions**: Add, change, delete permissions by role

### Integration Tests (tests/test_integration.py)
- **Complete Workflows**: End-to-end user creation and role assignment  
- **Admin Interface**: Form integration with dynamic fieldsets
- **Role Changes**: Workflow testing when users change roles
- **Data Isolation**: Users only access their own data

### System Tests (tests/test_integration.py)
- **Security**: System-wide permission enforcement
- **Edge Cases**: Handling users without profiles, cleanup on deletion
- **Group Integrity**: Role-based group assignments remain consistent
- **Bulk Operations**: Multiple user creation and management

## Test Fixtures

### Sample Users (tests/conftest.py)
- **admin_user**: Admin role with full privileges
- **doctor_user**: Doctor with cardiology department and license
- **nurse_user**: Nurse with emergency department and license  
- **patient_user**: Patient with no professional requirements
- **pharmacy_user**: Pharmacy role with license
- **create_groups**: Sets up all required Django groups

## Running Tests

### Prerequisites
```bash
# Install test dependencies
pip install -r requirements-test.txt
```

### Test Commands

**Run All Tests:**
```bash
python manage.py test_pms --category=all --verbose
```

**Run by Category:**
```bash
# Unit tests only
python manage.py test_pms --category=unit

# Integration tests  
python manage.py test_pms --category=integration

# System tests
python manage.py test_pms --category=system

# Specific components
python manage.py test_pms --category=models
python manage.py test_pms --category=forms
python manage.py test_pms --category=permissions
```

**With Coverage Report:**
```bash
python manage.py test_pms --category=all --coverage --verbose
```

**Direct PyTest Commands:**
```bash
# All tests with verbose output
pytest tests/ -v

# Tests by marker
pytest tests/ -m unit -v
pytest tests/ -m integration -v  
pytest tests/ -m system -v
pytest tests/ -m models -v
pytest tests/ -m forms -v
pytest tests/ -m permissions -v

# Coverage report
pytest --cov=core --cov-report=html --cov-report=term-missing tests/
```

### Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Unit tests for individual components
- `@pytest.mark.integration` - Integration tests for component interactions  
- `@pytest.mark.system` - End-to-end system tests
- `@pytest.mark.models` - Django model tests
- `@pytest.mark.forms` - Form validation tests
- `@pytest.mark.permissions` - Permission and access control tests
- `@pytest.mark.admin` - Admin interface tests

## Test Coverage

The test suite covers:

### Models (UserProfile)
- ✅ Profile creation for all roles
- ✅ Role-specific property methods
- ✅ Required field validation
- ✅ Group assignment automation
- ✅ Profile completeness checking
- ✅ Role change handling

### Forms (CustomUserCreationForm)
- ✅ Valid data submission for all roles
- ✅ Validation errors for missing required fields
- ✅ Password security enforcement
- ✅ License field exclusion for patients
- ✅ Department requirements for medical staff

### Admin Interface
- ✅ Permission-based access control
- ✅ Queryset filtering by role
- ✅ Dynamic fieldset generation
- ✅ Module permission enforcement
- ✅ CRUD operation restrictions

### Security & Permissions
- ✅ Role-based access control (RBAC)
- ✅ Data isolation between users
- ✅ Admin-only operations enforcement
- ✅ Superuser privilege handling
- ✅ Group membership management

### Integration Workflows  
- ✅ Complete user creation workflows
- ✅ Role change processes
- ✅ Group assignment consistency
- ✅ Profile data integrity
- ✅ Admin interface integration

## Expected Test Results

**Passing Tests:** 50+ comprehensive tests covering all functionality

**Coverage Target:** >80% code coverage for core module

**Performance:** All tests complete in <30 seconds

## Test Environment

- **Database**: Uses Django's test database (SQLite in memory)
- **Isolation**: Each test is isolated with fresh data
- **Groups**: Required Django groups created automatically
- **Users**: Sample users created with proper profiles and permissions

## Continuous Integration

Tests are designed to run in CI/CD environments:

```yaml
# Example GitHub Actions workflow
- name: Run Tests  
  run: |
    python manage.py test_pms --category=all --coverage
    
- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## Debugging Failed Tests

**View detailed output:**
```bash
pytest tests/ -v -s --tb=long
```

**Run specific failing test:**
```bash  
pytest tests/test_models.py::TestUserProfileModel::test_group_assignment_on_save -v -s
```

**Debug with pdb:**
```bash
pytest tests/ --pdb
```

## Test Data

Tests use realistic hospital scenarios:
- **Departments**: Cardiology, Emergency, Surgery, Neurology, Pediatrics, ICU
- **License Numbers**: MD123456 (doctors), RN123456 (nurses), PH123456 (pharmacy)  
- **Roles**: All five system roles (patient, doctor, nurse, pharmacy, admin)
- **Permissions**: Complete role-based permission matrix

This test suite ensures the Patient Monitoring System maintains security, data integrity, and proper role-based access control across all user interactions.
function toggleRequiredFields() {
    const roleField = document.getElementById('id_role');
    const departmentRow = document.querySelector('.field-department');
    const licenseRow = document.querySelector('.field-license_number');
    const departmentField = document.getElementById('id_department');
    const licenseField = document.getElementById('id_license_number');
    
    if (!roleField) return;
    
    const selectedRole = roleField.value;
    
    // Reset required attributes and styling
    if (departmentField) {
        departmentField.removeAttribute('required');
        departmentField.style.backgroundColor = '';
    }
    if (licenseField) {
        licenseField.removeAttribute('required');
        licenseField.style.backgroundColor = '';
        licenseField.value = ''; // Clear value when hiding
    }
    
    // Handle patient role - hide professional fields completely
    if (selectedRole === 'patient') {
        if (departmentRow) departmentRow.style.display = 'none';
        if (licenseRow) licenseRow.style.display = 'none';
        return; // Exit early for patients
    }
    
    // Handle department field for medical roles
    if (['doctor', 'nurse'].includes(selectedRole)) {
        if (departmentRow) departmentRow.style.display = '';
        if (departmentField) {
            departmentField.setAttribute('required', 'required');
            departmentField.style.backgroundColor = '#fff2cc'; // Light yellow to indicate required
        }
    } else {
        if (departmentRow) departmentRow.style.display = '';
        if (departmentField) {
            departmentField.removeAttribute('required');
            departmentField.style.backgroundColor = '';
        }
    }
    
    // Handle license field for medical staff
    if (['doctor', 'nurse', 'pharmacy'].includes(selectedRole)) {
        if (licenseRow) licenseRow.style.display = '';
        if (licenseField) {
            licenseField.setAttribute('required', 'required');
            licenseField.style.backgroundColor = '#fff2cc'; // Light yellow to indicate required
        }
    } else {
        if (licenseRow) licenseRow.style.display = '';
        if (licenseField) {
            licenseField.removeAttribute('required');
            licenseField.style.backgroundColor = '';
        }
    }
}

// Add form submission validation
function validateForm() {
    const roleField = document.getElementById('id_role');
    const departmentField = document.getElementById('id_department');
    const licenseField = document.getElementById('id_license_number');
    
    if (!roleField) return true;
    
    const selectedRole = roleField.value;
    const errors = [];
    
    // Skip validation for patients
    if (selectedRole === 'patient') {
        return true;
    }
    
    // Validate required fields for medical staff
    if (['doctor', 'nurse', 'pharmacy'].includes(selectedRole)) {
        if (licenseField && !licenseField.value.trim()) {
            errors.push('License number is required for medical staff.');
            licenseField.style.borderColor = 'red';
        }
    }
    
    if (['doctor', 'nurse'].includes(selectedRole)) {
        if (departmentField && !departmentField.value.trim()) {
            errors.push('Department is required for doctors and nurses.');
            departmentField.style.borderColor = 'red';
        }
    }
    
    if (errors.length > 0) {
        alert('Please fix the following errors:\n' + errors.join('\n'));
        return false;
    }
    
    return true;
}

// Run on page load
document.addEventListener('DOMContentLoaded', function() {
    toggleRequiredFields();
    
    // Also run when role changes
    const roleField = document.getElementById('id_role');
    if (roleField) {
        roleField.addEventListener('change', toggleRequiredFields);
    }
    
    // Add form validation on submit
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            if (!validateForm()) {
                e.preventDefault();
            }
        });
    }
});
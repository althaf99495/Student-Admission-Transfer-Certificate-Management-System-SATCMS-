/**
 * student_form.js
 * Contains client-side logic for student registration and edit forms.
 */
document.addEventListener('DOMContentLoaded', function() {
    
    // Initialize Flatpickr for all elements with the 'datepicker' class
    flatpickr(".datepicker", {
        altInput: true,
        altFormat: "d-m-Y", // Display format (e.g., 16-11-2002)
        dateFormat: "d-m-Y", // Format for the hidden input value (e.g., 16-11-2002)
    });

    /**
     * Sets up a toggle for an "Other" text input based on a select dropdown's value.
     * @param {string} selectId The ID of the <select> element.
     * @param {string} otherInputId The ID of the text <input> for "Other" value.
     */
    function initializeOtherToggle(selectId, otherInputId) {
        const selectElement = document.getElementById(selectId);
        const otherInputElement = document.getElementById(otherInputId);

        if (!selectElement || !otherInputElement) return;

        selectElement.addEventListener('change', function() {
            if (this.value === 'Other') {
                otherInputElement.classList.remove('d-none');
                otherInputElement.required = true;
            } else {
                otherInputElement.classList.add('d-none');
                otherInputElement.required = false;
                otherInputElement.value = '';
            }
        });

        // Initial check on page load in case of re-population after validation error
        if (selectElement.value === 'Other') {
            otherInputElement.classList.remove('d-none');
            otherInputElement.required = true;
        }
    }
    
    // Initialize all "Other" toggles on the page
    initializeOtherToggle('state', 'state_other');
    initializeOtherToggle('nationality', 'nationality_other');
    initializeOtherToggle('religion', 'religion_other');
    initializeOtherToggle('caste', 'caste_other');
    initializeOtherToggle('mother_tongue', 'mother_tongue_other');

    
    /**
     * Handles the student registration form submission via AJAX.
     * @param {Event} event The form submission event.
     */
    async function handleStudentFormSubmit(event) {
        event.preventDefault(); // Prevent default synchronous form submission

        const form = event.target;
        const formData = new FormData(form);
        const formMessages = document.getElementById('formMessages');
        formMessages.innerHTML = ''; // Clear previous messages

        // Client-side validation check
        if (!form.checkValidity()) {
            event.stopPropagation();
            form.classList.add('was-validated');
            return;
        }

        try {
            const response = await fetch(form.action, {
                method: 'POST',
                headers: {
                    // This header is important for Flask to know it's an AJAX request
                    'X-Requested-With': 'XMLHttpRequest',
                    // The CSRF token is sent as part of the form data
                },
                body: formData
            });

            const result = await response.json();

            if (!response.ok) { // Handle HTTP errors (e.g., 400, 500)
                displayErrors(result.errors || { 'general': 'An unknown error occurred. Please try again.' });
            } else {
                // Handle successful submission
                const successModalEl = document.getElementById('successModal');
                const successModal = new bootstrap.Modal(successModalEl);
                document.getElementById('successMessageText').textContent = result.message;
                document.getElementById('admissionNoDisplay').textContent = result.admission_no;
                document.getElementById('viewStudentBtn').href = result.student_url;
                successModal.show();
                            
                // Reset the form and update admission number after the modal is hidden
                successModalEl.addEventListener('hidden.bs.modal', function handler() {
                    form.reset();
                    form.classList.remove('was-validated');
                    // Add a small delay to allow the browser to fully render the form reset
                    setTimeout(() => {
                        // Display the generated admission number on the main form page
                        // after reset, so other fields are clear for new entry.
                        const admissionNoInput = document.getElementById('admission_no');
                        const admissionNoHelpText = document.getElementById('admissionNoHelpText');
                        if (admissionNoInput) {
                            admissionNoInput.value = result.admission_no;
                        }
                        if (admissionNoHelpText) {
                            admissionNoHelpText.textContent = `Last registered: ${result.admission_no}. Ready for new entry.`;
                            admissionNoHelpText.classList.remove('text-muted');
                            admissionNoHelpText.classList.add('text-success'); 
                        }
                    }, 50); // 50ms delay, adjust if needed
                    // Remove this event listener after it runs once
                    successModalEl.removeEventListener('hidden.bs.modal', handler);
                });
            }

        } catch (error) {
            console.error('Submission error:', error);
            displayErrors({ 'network': 'A network error occurred. Please check your connection and try again.' });
        }
    }

    /**
     * Displays validation or other errors in the form messages container.
     * @param {object} errors - An object where keys are field names and values are error messages.
     */
    function displayErrors(errors) {
        const formMessages = document.getElementById('formMessages');
        formMessages.innerHTML = ''; // Clear previous messages
        
        let errorHtml = '<div class="alert alert-danger" role="alert"><h5 class="alert-heading">Validation Errors</h5><ul>';
        for (const field in errors) {
            errorHtml += `<li><strong>${formatFieldName(field)}:</strong> ${errors[field]}</li>`;
            // Highlight the invalid field
            const inputField = document.querySelector(`[name="${field}"]`);
            if (inputField) {
                inputField.classList.add('is-invalid');
            }
        }
        errorHtml += '</ul></div>';
        formMessages.innerHTML = errorHtml;
        window.scrollTo(0, 0); // Scroll to the top to see the errors
    }

    /**
     * Formats a field name from snake_case to Title Case.
     * @param {string} fieldName - The field name (e.g., 'student_name').
     * @returns {string} The formatted field name (e.g., 'Student Name').
     */
    function formatFieldName(fieldName) {
        return fieldName
            .replace(/_/g, ' ')
            .replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase());
    }

    // Attach the AJAX submission handler to the registration form
    const studentRegistrationForm = document.getElementById('studentRegistrationForm');
    if (studentRegistrationForm) {
        studentRegistrationForm.addEventListener('submit', handleStudentFormSubmit);
    }
    
    // The edit form does not use AJAX by default in this setup, it uses standard form submission.
    // If you wanted AJAX for the edit form as well, you would attach a similar event listener to 'studentEditForm'.
});

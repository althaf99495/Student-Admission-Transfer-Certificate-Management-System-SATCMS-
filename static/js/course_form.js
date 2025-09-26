// static/js/course_form.js

document.addEventListener('DOMContentLoaded', function () {
    // Basic form validation feedback for Bootstrap
    const forms = document.querySelectorAll('.needs-validation');

    Array.prototype.slice.call(forms).forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }

            form.classList.add('was-validated');
        }, false);
    });

    // Auto-capitalize the course code input field
    const courseCodeInput = document.getElementById('course_code');
    if (courseCodeInput) {
        courseCodeInput.addEventListener('input', function() {
            this.value = this.value.toUpperCase();
        });
    }
});

    /**
     * Initializes a toggle for an "Other" text input based on a select dropdown's value.
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

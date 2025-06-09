// static/js/fee.js

document.addEventListener('DOMContentLoaded', function () {
    // Initialize Select2 for student search dropdown
    if (document.getElementById('student_id')) {
        $('#student_id').select2({
            theme: 'bootstrap-5',
            placeholder: 'Type to search for a student...',
        });
    }

    // Initialize Flatpickr for date fields
    flatpickr(".datepicker", {
        altInput: true,
        altFormat: "d/m/Y",
        dateFormat: "Y-m-d",
    });
    
    // Bootstrap form validation
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

    // Confirmation for delete forms
    const deleteForms = document.querySelectorAll('.confirm-delete-form');
    deleteForms.forEach(form => {
        form.addEventListener('submit', function(event) {
            const itemId = form.dataset.itemId;
            const itemName = form.dataset.itemName || 'item'; // Default to 'item' if not specified
            const message = `Are you sure you want to delete this ${itemName} (ID: ${itemId})? This action cannot be undone.`;
            
            if (!confirm(message)) {
                event.preventDefault(); // Stop form submission
            }
        });
    });

});

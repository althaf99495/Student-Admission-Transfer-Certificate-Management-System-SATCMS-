// static/js/tc_preview.js

document.addEventListener('DOMContentLoaded', function () {
    // Initialize Flatpickr for datepickers
    flatpickr(".datepicker", {
        altInput: true,
        altFormat: "d/m/Y",
        dateFormat: "Y-m-d",
    });

    // Basic Bootstrap form validation
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
});

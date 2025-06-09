// static/js/custom.js

/**
 * Shows a generic modal.
 * @param {string} title - The title of the modal.
 * @param {string} message - The message content of the modal.
 * @param {function} confirmCallback - Function to call when confirm button is clicked.
 * @param {string} [confirmText='Confirm'] - Text for the confirm button.
 * @param {string} [cancelText='Cancel'] - Text for the cancel button.
 * @param {string} [iconClass='fa-exclamation-triangle text-red-600'] - Font Awesome class for the icon.
 * @param {string} [iconBgClass='bg-red-100'] - Background class for the icon container.
 * @param {string} [confirmBtnClass='bg-red-500 hover:bg-red-700'] - Classes for confirm button.
 */
function showGenericModal(title, message, confirmCallback, confirmText = 'Confirm', cancelText = 'Cancel', iconClass = 'fas fa-exclamation-triangle text-red-600', iconBgClass = 'bg-red-100', confirmBtnClass = 'bg-red-500 hover:bg-red-700 focus:ring-red-300') {
    const modal = document.getElementById('genericModal');
    const modalTitle = document.getElementById('genericModalTitle');
    const modalMessage = document.getElementById('genericModalMessage');
    const modalConfirmButton = document.getElementById('genericModalConfirmButton');
    const modalCancelButton = document.getElementById('genericModalCancelButton');
    const modalIconContainer = document.getElementById('genericModalIcon');
    const modalIcon = modalIconContainer.querySelector('i');

    if (!modal || !modalTitle || !modalMessage || !modalConfirmButton || !modalCancelButton || !modalIconContainer || !modalIcon) {
        console.error('Modal elements not found!');
        return;
    }

    modalTitle.textContent = title;
    modalMessage.innerHTML = message; // Use innerHTML to allow for simple HTML like <br>
    modalConfirmButton.textContent = confirmText;
    modalCancelButton.textContent = cancelText;

    // Update icon
    modalIcon.className = `fas ${iconClass} text-xl`; // Ensure fas is present for Font Awesome
    modalIconContainer.className = `mx-auto flex items-center justify-center h-12 w-12 rounded-full ${iconBgClass}`;
    
    // Update confirm button classes
    modalConfirmButton.className = `px-4 py-2 text-white text-base font-medium rounded-md w-full shadow-sm focus:outline-none focus:ring-2 ${confirmBtnClass}`;


    // Clone and replace buttons to remove old event listeners
    const newConfirmButton = modalConfirmButton.cloneNode(true);
    modalConfirmButton.parentNode.replaceChild(newConfirmButton, modalConfirmButton);
    
    const newCancelButton = modalCancelButton.cloneNode(true);
    modalCancelButton.parentNode.replaceChild(newCancelButton, modalCancelButton);

    newConfirmButton.addEventListener('click', () => {
        if (typeof confirmCallback === 'function') {
            confirmCallback();
        }
        modal.classList.add('hidden');
    });

    newCancelButton.addEventListener('click', () => {
        modal.classList.add('hidden');
    });

    modal.classList.remove('hidden');
}

/**
 * Initializes dynamic "Other" text fields for select elements.
 * When a select option with value "other" (case-insensitive) is chosen,
 * it shows a text input field next to or below the select.
 * The text input will have the name `selectName_other`.
 * @param {string} selectContainerSelector - CSS selector for the container holding the select and where the "other" input should be placed.
 */
function initializeDynamicOtherFields(selectContainerSelector = '.dynamic-other-container') {
    document.querySelectorAll(selectContainerSelector).forEach(container => {
        const selectElement = container.querySelector('select');
        if (!selectElement) return;

        const otherInputName = selectElement.name + '_other';
        let otherInput = container.querySelector(`input[name="${otherInputName}"]`);

        // Create "other" input if it doesn't exist (e.g. for initial page load)
        if (!otherInput) {
            otherInput = document.createElement('input');
            otherInput.type = 'text';
            otherInput.name = otherInputName;
            otherInput.placeholder = 'Please specify';
            otherInput.className = 'mt-2 p-2 border border-gray-300 rounded-md w-full other-input hidden'; // Tailwind classes
            // Insert after the select element or at the end of the container
            selectElement.parentNode.insertBefore(otherInput, selectElement.nextSibling);
        }
        
        // Function to toggle visibility
        const toggleOtherInput = () => {
            if (selectElement.value.toLowerCase() === 'other') {
                otherInput.classList.remove('hidden');
                otherInput.focus();
            } else {
                otherInput.classList.add('hidden');
                otherInput.value = ''; // Clear value when hidden
            }
        };

        // Initial check
        toggleOtherInput();

        // Event listener for changes
        selectElement.addEventListener('change', toggleOtherInput);
    });
}

// Auto-initialize dynamic "Other" fields on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    initializeDynamicOtherFields();
});


/**
 * Handles form submission via AJAX.
 * @param {HTMLFormElement} formElement - The form element to submit.
 * @param {function} onSuccess - Callback function on successful submission (receives response data).
 * @param {function} [onError] - Callback function on error (receives error object or response data).
 */
async function submitFormAjax(formElement, onSuccess, onError) {
    try {
        const formData = new FormData(formElement);
        const response = await fetch(formElement.action, {
            method: formElement.method,
            body: formData,
            headers: {
                // 'Content-Type': 'application/x-www-form-urlencoded' or 'multipart/form-data' is set by FormData
                'X-Requested-With': 'XMLHttpRequest', // Often used to indicate AJAX requests
            },
        });

        const responseData = await response.json();

        if (response.ok) {
            if (typeof onSuccess === 'function') {
                onSuccess(responseData);
            }
        } else {
            if (typeof onError === 'function') {
                onError(responseData);
            } else {
                // Default error handling: show modal or alert
                let errorMessage = responseData.error || 'An unknown error occurred.';
                if (responseData.errors) { // For validation errors
                    errorMessage += '<br><ul class="list-disc list-inside text-left">';
                    for (const field in responseData.errors) {
                        errorMessage += `<li>${responseData.errors[field].join(', ')}</li>`;
                    }
                    errorMessage += '</ul>';
                }
                showGenericModal('Submission Error', errorMessage, null, 'Close', null, 'fas fa-times-circle text-red-600', 'bg-red-100');
            }
        }
    } catch (error) {
        console.error('AJAX submission error:', error);
        if (typeof onError === 'function') {
            onError(error);
        } else {
            showGenericModal('Network Error', 'Could not connect to the server. Please try again.', null, 'Close', null, 'fas fa-network-wired text-red-600', 'bg-red-100');
        }
    }
}

/**
 * Vendor Popup Manager
 * Handles both Django admin popups and custom modal popups for vendor management
 */

document.addEventListener('DOMContentLoaded', function() {
    // Add CSS styles for the modal
    const style = document.createElement('style');
    style.textContent = `
        .vendor-modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }
        .vendor-modal-content {
            background-color: #fefefe;
            margin: 10% auto;
            padding: 20px;
            border: 1px solid #888;
            width: 50%;
            max-width: 500px;
            border-radius: 5px;
        }
        .vendor-form-group {
            margin-bottom: 15px;
        }
        .vendor-form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        .vendor-form-group input {
            width: 100%;
            padding: 8px;
            box-sizing: border-box;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        .vendor-form-actions {
            text-align: right;
            margin-top: 20px;
        }
        .vendor-btn {
            padding: 8px 16px;
            margin-left: 10px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .vendor-btn-cancel {
            background-color: #f1f1f1;
        }
        .vendor-btn-save {
            background-color: #417690;
            color: white;
        }
        .vendor-error {
            color: red;
            margin-top: 10px;
            display: none;
        }
    `;
    document.head.appendChild(style);
    
    // Create the modal HTML
    const modalHtml = `
        <div id="vendorModal" class="vendor-modal">
            <div class="vendor-modal-content">
                <h2>Add New Vendor</h2>
                <form id="vendorForm">
                    <div class="vendor-form-group">
                        <label for="vendor_name">Vendor Name*</label>
                        <input type="text" id="vendor_name" required>
                    </div>
                    <div class="vendor-form-group">
                        <label for="vendor_contact">Contact Number</label>
                        <input type="text" id="vendor_contact">
                    </div>
                    <div class="vendor-form-group">
                        <label for="vendor_area">Area</label>
                        <input type="text" id="vendor_area">
                    </div>
                    <div id="vendorFormError" class="vendor-error"></div>
                    <div class="vendor-form-actions">
                        <button type="button" class="vendor-btn vendor-btn-cancel" id="vendorCancel">Cancel</button>
                        <button type="submit" class="vendor-btn vendor-btn-save">Save Vendor</button>
                    </div>
                </form>
            </div>
        </div>
    `;
    
    // Add modal to the page
    const modalContainer = document.createElement('div');
    modalContainer.innerHTML = modalHtml;
    document.body.appendChild(modalContainer);
    
    // Get modal elements
    const modal = document.getElementById('vendorModal');
    const form = document.getElementById('vendorForm');
    const cancelBtn = document.getElementById('vendorCancel');
    const errorDiv = document.getElementById('vendorFormError');
    
    // Add event listeners
    cancelBtn.addEventListener('click', function() {
        modal.style.display = 'none';
    });
    
    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
    
    // Process form submission
    form.addEventListener('submit', function(event) {
        event.preventDefault();
        
        const name = document.getElementById('vendor_name').value.trim();
        const contact = document.getElementById('vendor_contact').value.trim();
        const area = document.getElementById('vendor_area').value.trim();
        
        if (!name) {
            errorDiv.textContent = 'Vendor name is required';
            errorDiv.style.display = 'block';
            return;
        }
        
        errorDiv.style.display = 'none';
        
        // In a real implementation, you would send this data to your server
        // For now, we'll simulate a successful API call
        
        // Generate a temporary ID (in production, this would come from the server)
        const tempId = Date.now();
        
        // Find the vendor select field
        const vendorSelect = document.querySelector('select#id_vendor');
        if (vendorSelect) {
            // Add the new vendor to the dropdown
            const option = new Option(name, tempId);
            vendorSelect.add(option);
            
            // Select the new option
            vendorSelect.value = tempId;
            
            // Trigger the change event
            const event = new Event('change');
            vendorSelect.dispatchEvent(event);
            
            // Close the modal
            modal.style.display = 'none';
            
            // Reset the form
            form.reset();
            
            // Show success alert
            alert(`Vendor "${name}" added successfully!`);
        }
    });
    
    // Find all vendor select fields and add the '+ Add Vendor' button
    const vendorFields = document.querySelectorAll('select[id*="vendor"]');
    vendorFields.forEach(function(select) {
        const addButton = document.createElement('a');
        addButton.href = '#';
        addButton.className = 'add-another';
        addButton.innerHTML = '+';
        addButton.title = 'Add Vendor';
        addButton.style.marginLeft = '5px';
        
        // Add button after the select
        select.parentNode.insertBefore(addButton, select.nextSibling);
        
        // Show modal when clicking the add button
        addButton.addEventListener('click', function(event) {
            event.preventDefault();
            modal.style.display = 'block';
        });
    });
    
    // Define the dismissAddRelatedObjectPopup function for the admin popups
    if (typeof window.dismissAddRelatedObjectPopup !== 'function') {
        window.dismissAddRelatedObjectPopup = function(win, objId, objName) {
            const name = objName || objId;
            const id = objId;
            
            // Find the vendor select element
            const selects = document.querySelectorAll('select[name*="vendor"]');
            if (selects.length) {
                selects.forEach(function(sel) {
                    // Add the option if it doesn't exist
                    if (!sel.querySelector(`option[value="${id}"]`)) {
                        const option = new Option(name, id);
                        sel.add(option);
                    }
                    
                    // Select the new option
                    sel.value = id;
                    
                    // Trigger the change event
                    const event = new Event('change');
                    sel.dispatchEvent(event);
                });
                
                // Close the popup window
                win.close();
            }
        };
    }
}); 
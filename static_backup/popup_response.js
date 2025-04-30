/**
 * Global popup response handler for Django admin.
 * This file ensures the dismissAddRelatedObjectPopup function is available
 * in any window that might receive a popup response.
 */

// Define the popup response function globally
window.dismissAddRelatedObjectPopup = function(popup, objId, objName) {
    console.log('dismissAddRelatedObjectPopup called with', objId, objName);
    
    var vendorField = document.getElementById('id_vendor');
    
    if (vendorField) {
        // Create a new option for the vendor
        var option = new Option(objName, objId);
        option.selected = true;
        
        // Add the option to the select field
        vendorField.appendChild(option);
        
        // Trigger change event
        if ("createEvent" in document) {
            var evt = document.createEvent("HTMLEvents");
            evt.initEvent("change", false, true);
            vendorField.dispatchEvent(evt);
        } else {
            vendorField.fireEvent("onchange");
        }
    }
    
    // Close the popup
    popup.close();
};
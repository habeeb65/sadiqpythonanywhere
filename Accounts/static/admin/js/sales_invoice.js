// Update the autocomplete display to show product quantities
(function($) {
    $(document).ready(function() {
        console.log("Sales invoice JS loaded and DOM ready.");

        // Listen for lot selection changes on the specific select2 input
        $('#id_lots-0-purchase_invoice').on('select2:select', function(e) {
            const lotId = e.params.data.id;
            console.log("Lot selected with ID:", lotId);

            // Fetch detailed product info using the standard $ for consistency
            $.get(`/admin/Accounts/purchaseinvoice/${lotId}/change/`, function(data) {
                // Parse and display product quantities here if needed
                console.log("Lot details fetched (or change page loaded):", data);
                // You might need to parse the HTML 'data' to get info if it's not a JSON endpoint
            }).fail(function(jqXHR, textStatus, errorThrown) {
                console.error("Error fetching lot details:", textStatus, errorThrown);
            });
        });

        // Add logs for debugging if select2 isn't initializing or event isn't firing
        if ($('#id_lots-0-purchase_invoice').length === 0) {
            console.error("Select2 element #id_lots-0-purchase_invoice not found!");
        } else {
            console.log("Select2 element found. Attaching listener.");
        }
    });
})(django.jQuery);

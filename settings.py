JAZZMIN_SETTINGS = {
    # ... existing jazzmin settings ...
    'menu': [
        {'label': 'Home', 'app': 'home', 'url': 'admin:index', 'icon': 'fas fa-home'},
        {'app': 'Accounts', 'label': 'Vendor Summary', 'icon': 'fas fa-users', 'url': '/admin/vendor-summary/'},
        {'app': 'auth', 'label': 'Authentication', 'icon': 'fas fa-lock'},
        # ... rest of your existing menu items ...
    ],
    # ... other jazzmin settings ...
    "custom_js": None,  # Make sure this is None or points to a valid JS file
}


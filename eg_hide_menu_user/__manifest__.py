{
    "name": "Hide Menus per User",
    "version": "19.0.1.0.0",
    "category": "Extra Tools",
    "summary": "Hide specific menus from specific users",
    "description": """
Hide Menus per User
===================
Lets an administrator pick menus that must be hidden for a given user.

* Configure from the user form (Settings > Users > "Hidden Menus" tab),
  or from the menu form (Settings > Technical > Menu Items > "Hidden for Users").
* Hiding a menu also hides all of its sub-menus.
* Only administrators (Settings access) can see or edit this configuration.

Note: this hides menus in the interface only. It does not remove access
rights to the underlying records - use groups / record rules for that.
    """,
    "author": "Elite Nest",
    "depends": ["base"],
    "data": [
        "views/res_users_view.xml",
        "views/ir_ui_menu_view.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}


# -*- coding: utf-8 -*-
{
    "name": "Property Dashboard Real-Time | Real Estate Executive Command Center",
    "version": "19.0.1.0.0",
    "category": "Real Estate/Property Management",
    "summary": "Real-time executive dashboard for Property and Lease Contract Management with WebSocket bus updates, Chart.js analytics, and AED rent benchmarks",
    "author": "INKERP / Elite Nest",
    "website": "https://www.inkerp.com",
    "license": "OPL-1",
    "depends": [
        "base",
        "web",
        "bus",
        "eg_property_management",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/property_dashboard_data.xml",
        "views/property_dashboard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "property_dashboard_realtime/static/src/dashboard/property_dashboard.scss",
            "property_dashboard_realtime/static/src/dashboard/property_dashboard.js",
            "property_dashboard_realtime/static/src/dashboard/property_dashboard.xml",
        ],
    },
    "images": [
        "static/description/icon.svg",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}

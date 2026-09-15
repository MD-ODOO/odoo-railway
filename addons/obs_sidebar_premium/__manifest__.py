# -*- coding: utf-8 -*-
{
    'name': 'Sidebar Premium',
    'version': '19.0.1.0.0',
    'summary': 'Floating sidebar with bookmarks, calculator, clock, notes, font size and theme color',
    'description': """
SideBar
=======

A free floating sidebar for Odoo 19 that gives you quick access to productivity tools
without leaving your current page.

Features:
---------
- Fullscreen, hide navbar, compact mode
- Font size control (70% to 150%)
- Theme color picker (12 presets + custom hex)
- Live clock with timezone
- Full calculator
- Bookmarks with custom names and no-reload navigation
- Auto-tracked recent pages (last 20)
- Persistent quick notes (auto-saved to localStorage)
- Fully responsive (mobile, tablet, desktop)
    """,
    'author': 'Obystech Solutions',
    'maintainer': 'Karjout Abdeslam',
    'website': 'https://obystech.com',
    'support': 'abdeslam@obystech.com',
    'category': 'Web',
    'license': 'LGPL-3',
    'depends': ['web'],
    'assets': {
        'web.assets_backend': [
            'obs_sidebar_premium/static/src/css/sidebar.css',
            'obs_sidebar_premium/static/src/xml/sidebar.xml',
            'obs_sidebar_premium/static/src/js/sidebar.js',
        ],
    },
    'images': ['static/description/images/banner.jpg'],
    'installable': True,
    'auto_install': False,
    'application': False,
    'price': 0,
    'currency': 'EUR',
}

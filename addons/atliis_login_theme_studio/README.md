# Login Theme Studio

Login Theme Studio is an Odoo 19 module by Atliis 360 for configuring Odoo
login, signup and password reset branding without editing XML, SCSS,
JavaScript or core Odoo files.

The module keeps Odoo's native authentication logic intact. It customises the
presentation layer through QWeb inheritance, frontend assets and safe public
theme payloads.

## Features

- No-code login, signup and password reset branding.
- Multi-company, Website ID and domain-based theme resolution.
- Draft, scheduled, published, expired and archived workflow states.
- Live preview with desktop, tablet and mobile frames.
- Configurable logos, colours, typography, cards, background media and links.
- Password visibility and Caps Lock feedback.
- Footer, support, privacy, terms and help links.
- Accessibility score and contrast/usability report.
- Safe fallback to either a configured default theme or native Odoo login.
- Optional Website integration without a hard dependency on the Website app.

## Dependencies

Required:

- `base`
- `web`
- `auth_signup`

Supported installations:

- Odoo 19 Community
- Odoo 19 Enterprise
- Odoo.sh
- Self-hosted Odoo installations

Odoo Online SaaS is not supported because third-party custom modules cannot
normally be installed there.

## Installation

1. Copy `atliis_login_theme_studio` into an Odoo addons path.
2. Restart Odoo.
3. Update the app list.
4. Install **Login Theme Studio**.

Command-line upgrade example:

```bash
python odoo-bin -c odoo.conf -d your_database -u atliis_login_theme_studio --stop-after-init
```

## Configuration

Open **Settings > Login Studio**.

Use **Themes** to create and manage login themes. A theme is applied to public
authentication pages only when it is active, published and inside its optional
schedule window.

Theme resolution priority:

1. Exact domain match
2. Website ID match
3. Company match
4. Global default theme
5. Configured fallback or native Odoo login

Use **Configuration** to choose:

- Default login theme
- Force native Odoo login
- Domain resolution
- Scheduling support
- Fallback mode

## Preview

Open a theme and click **Preview**. The preview page shows desktop, tablet and
mobile frames using the same frontend asset bundle as the real login page.

The preview uses a non-posting mock login form, so it cannot alter
authentication state or weaken login security.

## Accessibility

Each theme includes:

- Accessibility score
- Detailed contrast warnings
- Font-size checks
- Password visibility and Caps Lock usability checks
- Reduced-motion check

Use **Check Accessibility** from the theme form for a quick admin notification.

## Safe Mode

If a theme configuration causes a rendering issue, append this query parameter
to the login URL:

```text
/web/login?login_theme_safe_mode=1
```

Administrators can also enable **Force Native Login** in Login Studio settings.

## Testing

Run module tests with:

```bash
python odoo-bin -c odoo.conf -d your_database --test-enable --test-tags /atliis_login_theme_studio --stop-after-init
```

The test suite covers:

- Model validation
- Theme resolver priority and fallback behavior
- Access rights
- Authentication page smoke checks

## Security Notes

- The module does not replace Odoo login, signup, password reset or OAuth
  controllers.
- Public rendering uses a restricted safe payload instead of exposing records.
- Preview routes require authenticated users with Login Theme Studio access.
- Manager permissions are separated from viewer permissions.

## Support

Publisher: Atliis 360

Website: https://www.atliis.com

Live demo: https://demov19.atliis.com/web/login?utm_source=odoo_apps&utm_medium=live_preview&utm_campaign=atliis_login_theme_studio

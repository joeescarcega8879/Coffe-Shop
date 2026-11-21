# ☕ Coffee Shop — Restaurant Menu Website (Django)

A simple, responsive restaurant website with a browsable menu, category filtering,
item detail pages, a working contact form, and a full Django Admin panel.

Built with **Django 5.2** and a custom frontend (Tailwind CDN + Material Symbols + custom CSS).

---

## ✨ Features

- **Home page** — restaurant info, logo, featured items, navbar and footer
- **Menu page** — grid of items (image, name, description, price, category) with
  **server-side category filtering** via `?categoria=slug`
- **Item detail page** — large image, full description, price, category (`/menu/<id>/`)
- **Contact page** — restaurant info + **functional form** that saves `ContactMessage`
  records and shows flash messages
- **Django Admin** — CRUD for categories, menu items (with image thumbnails) and
  contact messages
- **Media support** — upload item images through the Admin, served in dev via `/media/`
- **Custom 404/500 pages**, basic SEO (titles, meta description, alt attributes)
- **Mobile-first** responsive design (collapsible navbar, adaptive grids)

## 🛠 Tech stack

| Layer | Technology |
|---|---|
| Backend | Django 5.2 (Python) |
| Database | SQLite (default) |
| Frontend | Tailwind CSS (CDN), Material Symbols, vanilla JS + custom CSS |
| Images | Pillow (`ImageField`) |
| Tests | Django TestCase (21 tests) |

## 📁 Project structure

```
Coffe-Shop/
├── core/                 # Project settings (settings.py, urls.py)
├── menu/                 # Main app
│   ├── fixtures/
│   │   └── initial_data.json   # 4 categories + 10 menu items (seed data)
│   ├── migrations/
│   ├── admin.py          # Admin registrations + image thumbnails
│   ├── models.py         # Category, MenuItem, ContactMessage
│   ├── tests.py          # 21 tests (models, views, filtering, contact form)
│   ├── urls.py           # app_name = 'menu'
│   └── views.py          # home, menu_list, menu_detail, contact
├── templates/
│   ├── base.html         # Shared navbar/footer/flash messages
│   ├── 404.html          # Custom error pages
│   ├── 500.html
│   └── menu/             # home, menu_list, menu_detail, contact
├── static/               # css, js (Tailwind config, main.js)
├── media/                # Uploaded images (menu_items/)
└── manage.py
```

## 🚀 Getting started

### 1. Clone & environment

```bash
git clone <your-repo-url> Coffe-Shop
cd Coffe-Shop
```

Create a virtual environment (choose one):

```bash
# Option A — venv
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Option B — conda
conda create -n DjangoEnvironment python=3.14
conda activate DjangoEnvironment
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Apply migrations

```bash
python manage.py migrate
```

### 4. Load seed data (4 categories + 10 menu items)

```bash
python manage.py loaddata initial_data
```

> ⚠️ The fixture includes `created_at`/`updated_at`/`date_sent` values explicitly —
> `loaddata` requires them for `auto_now` fields, do not remove them.

### 5. Create a superuser (admin panel)

```bash
python manage.py createsuperuser
```

### 6. Run the server

```bash
python manage.py runserver
```

Open **http://127.0.0.1:8000/** 🎉

| Page | URL |
|---|---|
| Home | `/` |
| Menu | `/menu/` |
| Menu + filter | `/menu/?categoria=coffees` |
| Item detail | `/menu/1/` |
| Contact | `/contact/` |
| Admin | `/admin/` |

## 🧪 Running the tests

```bash
python manage.py test
```

Runs 21 tests covering models (slug auto-generation, `__str__`, ordering),
views (templates, context), category filtering, detail 404s, and the contact
form (valid/invalid POST). Tests use a **temporary database** — your data is untouched.

## 🖼 Managing images

Upload item images through the Admin (`/admin/` → Menu items → pick file → Save).
Thumbnails appear in the list view. Images are stored in `media/menu_items/` and
served in development via `/media/`.

## 🧹 Other useful commands

```bash
python manage.py makemigrations --check --dry-run   # verify migrations
python manage.py collectstatic                      # needed before deploy
python manage.py flush --noinput && python manage.py loaddata initial_data   # reset data
```

## 🚀 Deployment

Production setup for a Linux server (tested stack: **Caddy** → **gunicorn** → Django, managed by systemd):
see **[deploy/README.md](deploy/README.md)** for the step-by-step guide.

- All configuration comes from environment variables — see [`.env.example`](.env.example)
  (`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `TIME_ZONE`, paths, email…).
  Local development needs none of them.
- With `DEBUG=False` the app enables HTTPS redirect, secure cookies and HSTS;
  `python manage.py check --deploy` is part of the test suite.
- Static files are served by WhiteNoise; uploaded media by the web server.
- Checkout and contact form are rate limited per client IP (10 / 5 requests per hour).
- Update a running server with `./deploy/deploy.sh` (backs up the DB, migrates, restarts, health-checks).

---

Made with ☕ — Coffee Shop project

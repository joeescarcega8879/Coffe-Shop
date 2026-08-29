# Plan de Desarrollo — Sitio Web de Menú para Restaurante (Django)

## Objetivo
Sitio web simple y responsivo para un restaurante con menú navegable, panel de administración y formulario de contacto.

## Requerimientos del proyecto
- Página de inicio: info del restaurante, logo, platillos destacados, navbar y footer.
- Página de menú: nombre, descripción, precio, imagen y categoría de cada platillo.
- Filtrado por categoría y página de detalle de platillo.
- Django Admin para ABM (agregar, editar, eliminar) de categorías y platillos.
- Página de contacto con información del restaurante y formulario funcional.
- Modelos: `Category`, `MenuItem`, `ContactMessage`.
- Diseño responsivo con Bootstrap.

## Stack
- Python 3.14.4 (disponible en el entorno)
- Django 5.2 (instalado en `venv`; proyecto generado con `startproject core`)
- SQLite (por defecto)
- Bootstrap 5 (CDN)
- Pillow (instalado — requerido por `ImageField`)

---

## 📌 Estado del proyecto — actualizado 2026-08-28

**Resumen:** Fase 0 ✅ · Fase 1 ✅ · Fase 2 ✅ · Fase 3 ✅ · Fase 4 ✅ (aplicadas) · Fase 5 pendiente.

### Decisiones confirmadas
| Decisión | Elección |
|---|---|
| Idioma de la interfaz | **Inglés** (todo el código, modelos y datos en inglés; `LANGUAGE_CODE='en-us'`) |
| Frontend | **Tailwind CDN + Material Symbols + CSS custom** (páginas hechas por el usuario en `~/.../FrontEnd-Proyects/Coffe-shop-Front`, incrustadas en Django en Fase 3). ~~Vanilla sin CDN~~ descartado |
| Estructura del menú | Una sola página con filtros (`?categoria=slug`) |
| Nombre del restaurante | **Coffee Shop** (branding en navbar/footer/títulos) |

### Desviaciones vs. plan original (importante)
1. **Modelos en inglés y con campos extra**: `Category` y `MenuItem` tienen además `created_at` / `updated_at` (no estaban en el plan). `Category` usa `related_name='menu_items'` y su `slug` tiene `max_length=100`.
2. **`MenuItem` NO tiene campo `slug`** → la página de detalle usará `pk` (id numérico): `menu/<int:pk>/`.
3. **Fixture**: el archivo es `menu/fixtures/initial_data.json` (NO `datos_iniciales`) → se carga con `python manage.py loaddata initial_data`. Contiene 4 categorías y 10 platillos.
4. **Truco de `loaddata`**: los campos `auto_now`/`auto_now_add` (`created_at`, `updated_at`, `date_sent`) **deben ir explícitos en el fixture** (el loader no los rellena, falla con `NOT NULL constraint failed`).
5. `TIME_ZONE = 'UTC'` (por defecto; se puede cambiar, ej. `America/Mexico_City`).
6. **Frontend de Fase 3**: no fue "vanilla generado aparte" — el usuario ya tenía las 4 páginas hechas con **Tailwind CDN** (no Bootstrap). Se copiaron assets a `static/` y las páginas a `templates/menu/`, con `base.html` para navbar/footer compartidos.
7. **Entorno**: Django/Pillow están en el entorno conda `DjangoEnvironment` (NO en `venv/` — el venv original ya no existe). Comandos con `~/miniconda3/envs/DjangoEnvironment/bin/python manage.py ...` o activar con `conda activate DjangoEnvironment`.
8. **Fixture alineado al frontend (2026-08-28)**: precios y descripciones de los 10 ítems ahora coinciden con el catálogo del frontend (Espresso $3.50, Cappuccino $4.50, Chocolate Frappe $5.50, Cheesecake $6.00, Croissant $3.75, Pancakes $8.50, etc.). El frontend tiene además Iced Latte ($4.75) y Avocado Toast ($9.50) que **no están en la DB** (no son requeridos).
9. **Superuser creado** ✅ (Admin operativo).
10. **Nav activo**: resuelto server-side con `request.resolver_match.url_name` en `base.html` (se eliminó el bloque JS de `main.js` que colisionaba). `contact.js` reescrito sin `preventDefault` (el POST real va a Django).

### Pendientes menores detectados
- ✅ Resuelto: typo `list_selecte_related` → `list_select_related` ya corregido en `menu/admin.py`.
- Método muerto `short_description` en `CategoryAdmin` (opcional borrarlo).
- Imágenes de platillos **vacías** en la DB (pendiente Fase 4: subir por Admin).

---

## Fase 0 — Setup del proyecto ✅
- [x] Entorno virtual (`venv`) e instalación de Django + Pillow
- [x] `django-admin startproject core` + app `menu` creada
- [x] Settings: `INSTALLED_APPS` con `menu`, `STATIC_URL`, `STATICFILES_DIRS`, `MEDIA_URL`/`MEDIA_ROOT`
- [ ] ~~`LANGUAGE_CODE='es'`~~ → **descartado**: la interfaz es en inglés (`en-us`)
- [~] Estructura base: `static/` ✅ creado · `templates/` ⏳ pendiente
- [x] `git init`, `.gitignore`, `requirements.txt`, commit inicial

**Criterio de aceptación:** ✅ cumplido — el servidor levanta y muestra la página de bienvenida de Django.

## Fase 1 — Modelos y Admin ✅
- [x] Modelo `Category`: `name`, `slug`, `description`, `image` (+ `created_at`, `updated_at`)
- [x] Modelo `MenuItem`: `name`, `description`, `price`, `image`, `category` (FK), `is_available`, `is_featured` (+ `created_at`, `updated_at`)
- [x] Modelo `ContactMessage`: `name`, `email`, `phone`, `message`, `date_sent`
- [x] Migraciones aplicadas (`menu/migrations/0001_initial.py`, `db.sqlite3` creado)
- [x] Registro en Admin con `list_display`, `search_fields`, `list_filter`, `list_editable`
- [x] Datos de ejemplo: `initial_data.json` con 4 categorías y 10 platillos (cargado ✅)

**Criterio de aceptación:** ✅ cumplido — desde el Admin se puede crear/editar/eliminar categorías y platillos.

## Fase 2 — Vistas y URLs ✅ (aplicada)
- [x] Vistas: home, lista de menú, detalle de platillo, contacto (`menu/views.py`)
- [x] URL patterns con `name` — `menu/urls.py` con `app_name = 'menu'`
- [x] Conectar `include('menu.urls')` en `core/urls.py`
- [x] Filtrado por categoría vía query param (`?categoria=slug`) — en `menu_list`
- [x] Platillos destacados en home (`is_featured`) — en `home`
- [x] Vista `contact` con POST funcional (guarda `ContactMessage` + `messages` flash)

**Criterio de aceptación:** ⏳ parcial — wiring URLs↔vistas funcionando (verificado con `resolve`/`reverse`); la navegación visual queda pendiente hasta la Fase 3 (templates).

## Fase 3 — Templates (frontend incrustado en Django) ✅ (aplicada)
- [x] Carpeta `templates/` creada con `base.html` (navbar + footer + mensajes flash) y 4 páginas en `templates/menu/`: `home.html`, `menu_list.html`, `menu_detail.html`, `contact.html`
- [x] Assets del frontend copiados a `static/` (`css/styles.css`, `js/main.js`, `js/tailwind-config.js`, `js/menu.js`, `js/contact.js`)
- [x] Home: platillos destacados dinámicos (`featured_items`) con fallback de imagen (placeholder si `item.image` vacío)
- [x] Menú: grid de cards dinámico + filtros por categoría como links `?categoria=slug` (server-side, sin JS)
- [x] Detalle: imagen grande, descripción, precio y categoría desde `item` (`menu/<int:pk>/`)
- [x] Contacto: formulario con POST real (`{% csrf_token %}`) → guarda `ContactMessage` → mensaje flash
- [x] Diseño mobile-first (navbar colapsable, grillas adaptativas, animaciones scroll-reveal)
- [x] Nav activo server-side (`request.resolver_match.url_name`) — fix de `main.js`
- [x] `contact.js` reescrito sin `preventDefault` (no bloquea el POST)
- [x] Superuser creado; fixture de precios alineado al catálogo del frontend y recargado

**Criterio de aceptación:** ✅ cumplido — el sitio se ve y funciona bien en móvil y desktop; el formulario de contacto guarda mensajes (verificado en Admin).

## Fase 4 — Medios y pulido ✅ (aplicada)
- [x] Subida de imágenes desde el Admin: `ImageField` + servido de `MEDIA` en dev (`core/urls.py` con `static()` condicionado a `DEBUG`)
- [x] Preview de imagen (thumbnail) en el listado de Admin (`MenuItemAdmin.thumbnail`)
- [x] Mensajes flash (django.contrib.messages) y validaciones — ya estaban desde Fase 3 (base.html + vista contact)
- [x] Páginas 404/500 custom: `templates/404.html` y `templates/500.html` (branding Coffee Shop + link a Home)
- [x] SEO básico: `<title>` por bloque, `meta description` en base.html, `alt` en imágenes (`{{ item.name }}`)

**Criterio de aceptación:** ✅ cumplido — verificado con test client: subida de imagen → `/media/menu_items/…` responde `200 image/jpeg`; detalle muestra la `<img>`; filtro por categoría OK; 404 custom y 500 custom renderizan.
- [x] **Imágenes subidas (2026-08-28)**: los 10 platillos tienen imagen en `media/menu_items/` (subidas por Admin con las fotos del frontend; ver `imagenes_del_menu.md`). Las categorías no usan imagen en el diseño actual. Detalle menor: `chocolate-frappe..jpg` tiene doble punto en el nombre (cosmético, funciona bien).

## Fase 5 — Tests, README y entrega ⏳ (en progreso)
- [x] Tests: modelos, vistas, filtrado por categoría, formulario de contacto — `menu/tests.py` con **21 tests, todos OK** (`python manage.py test`)
- [ ] README con instrucciones: instalación, migraciones, seed, crear superusuario, correr servidor
- [ ] (Opcional) Despliegue en Render / PythonAnywhere / Railway

**Criterio de aceptación:** ⏳ parcial — `python manage.py test` pasa (21 tests ✅); falta el README.

---

## Comandos útiles (estado actual)
```bash
conda activate DjangoEnvironment    # activar entorno (el venv original ya no existe)
python manage.py runserver          # levantar servidor
python manage.py loaddata initial_data   # recargar datos de ejemplo
python manage.py createsuperuser    # crear admin
python manage.py makemigrations --check --dry-run   # verificar migraciones
```

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
- Django (última versión estable compatible con Python 3.14 — instalar en Fase 0)
- SQLite (por defecto)
- Bootstrap 5 (CDN)

---

## Fase 0 — Setup del proyecto
- [ ] Crear entorno virtual (`venv`) e instalar Django
- [ ] `django-admin startproject` + app `menu`
- [ ] Configurar settings: `LANGUAGE_CODE='es'`, `TIME_ZONE`, `STATIC_URL`, `MEDIA_URL`/`MEDIA_ROOT`
- [ ] Crear estructura base de templates y static
- [ ] `git init`, `.gitignore`, commit inicial

**Criterio de aceptación:** el servidor levanta y muestra la página de bienvenida de Django.

## Fase 1 — Modelos y Admin
- [ ] Modelo `Category`: nombre, slug, descripción (opcional), imagen (opcional)
- [ ] Modelo `MenuItem`: nombre, descripción, precio, imagen, categoría (FK), `is_available`, `is_featured`
- [ ] Modelo `ContactMessage`: nombre, email, teléfono (opcional), mensaje, fecha de envío
- [ ] Migraciones aplicadas
- [ ] Registro en Django Admin con `list_display`, `search_fields`, `list_filter`
- [ ] Datos de ejemplo (seed/fixtures) con algunas categorías y platillos

**Criterio de aceptación:** desde el Admin se puede crear/editar/eliminar categorías y platillos.

## Fase 2 — Vistas y URLs
- [ ] Vistas: home, lista de menú, detalle de platillo, contacto
- [ ] URL patterns con `name` (para `{% url %}` en templates)
- [ ] Filtrado por categoría vía query param (`?categoria=slug`)
- [ ] Platillos destacados en home (`is_featured`)

**Criterio de aceptación:** navegación básica funcionando entre todas las páginas.

## Fase 3 — Templates con Bootstrap (responsivo)
- [ ] `base.html`: navbar (logo + links) y footer, carga de Bootstrap 5
- [ ] Home: logo, info del restaurante, platillos destacados
- [ ] Menú: grid de cards (imagen, nombre, descripción, precio, categoría) + botones de filtro por categoría
- [ ] Detalle de platillo: imagen grande, descripción completa, precio, categoría
- [ ] Contacto: info del restaurante + formulario funcional (POST → guarda `ContactMessage` → mensaje de éxito)
- [ ] Diseño mobile-first (colapsable, grillas adaptativas)

**Criterio de aceptación:** el sitio se ve y funciona bien en móvil y desktop; el formulario de contacto guarda mensajes.

## Fase 4 — Medios y pulido
- [ ] Subida de imágenes desde el Admin (`ImageField` + servido de `MEDIA` en dev)
- [ ] Mensajes flash (django.contrib.messages) y validaciones
- [ ] Páginas 404/500 custom
- [ ] SEO básico: `<title>`, meta description, `alt` en imágenes

**Criterio de aceptación:** se pueden subir imágenes de platillos y todo se muestra correctamente.

## Fase 5 — Tests, README y entrega
- [ ] Tests: modelos, vistas, filtrado por categoría, formulario de contacto
- [ ] README con instrucciones: instalación, migraciones, seed, crear superusuario, correr servidor
- [ ] (Opcional) Despliegue en Render / PythonAnywhere / Railway

**Criterio de aceptación:** `python manage.py test` pasa y el README permite reproducir el proyecto desde cero.

---

## Decisiones abiertas (confirmar antes de Fase 0)
1. Nombre del proyecto/restaurante (afecta títulos, logo, colores).
2. ¿Bootstrap 5 por CDN o archivos locales? (CDN es más simple).
3. ¿Menú de una sola página con filtros o páginas separadas por categoría? (default: una página con filtros).
4. ¿Idioma de la interfaz? (default: español).

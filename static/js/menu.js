/* ============================================================
   Coffee Shop — Menu page
   Category filtering (All / Coffees / Cold Drinks / Desserts / Breakfast)
   Loaded on: menu.html (after main.js)
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  const filterBtns = document.querySelectorAll('.filter-btn');
  const menuItems = document.querySelectorAll('.menu-item');

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      // Remove active state from all buttons
      filterBtns.forEach(b => {
        b.classList.remove('active', 'bg-primary-container', 'text-on-primary', 'border-primary-container');
        b.classList.add('border-outline-variant', 'text-primary');
      });

      // Activate the clicked button
      btn.classList.add('active', 'bg-primary-container', 'text-on-primary', 'border-primary-container');
      btn.classList.remove('border-outline-variant', 'text-primary');

      const filterValue = btn.getAttribute('data-filter');

      menuItems.forEach(item => {
        if (filterValue === 'all' || item.classList.contains(filterValue)) {
          item.style.display = 'flex';
          // Slight delay for smooth visual re-layout
          setTimeout(() => {
            item.style.opacity = '1';
            item.style.transform = 'scale(1)';
          }, 50);
        } else {
          item.style.opacity = '0';
          item.style.transform = 'scale(0.95)';
          setTimeout(() => {
            item.style.display = 'none';
          }, 300); // match transition duration roughly
        }
      });
    });
  });
});

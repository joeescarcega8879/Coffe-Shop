/* ============================================================
   The Hearth Roastery — Contact page
   Form validation + submit feedback
   Loaded on: contact.html (after main.js)
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('contactForm');
  if (!form) return;

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    const messageDiv = document.getElementById('formMessage');

    // Simple validation simulation
    const name = document.getElementById('name').value;
    const email = document.getElementById('email').value;
    const message = document.getElementById('message').value;

    messageDiv.classList.remove('hidden', 'bg-tertiary-container', 'text-on-tertiary', 'bg-error-container', 'text-on-error-container');

    if (name && email && message) {
      // Success state
      messageDiv.classList.add('bg-tertiary-container', 'text-on-tertiary');
      messageDiv.textContent = 'Thank you for reaching out! We will get back to you soon.';
      this.reset();
    } else {
      // Error state (HTML5 required should catch most cases first)
      messageDiv.classList.add('bg-error-container', 'text-on-error-container');
      messageDiv.textContent = 'Please fill in all required fields.';
    }

    // Hide message after 5 seconds
    setTimeout(() => {
      messageDiv.classList.add('hidden');
    }, 5000);
  });
});

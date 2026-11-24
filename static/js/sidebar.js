// sidebar.js – handles mobile sidebar toggle and accessibility
document.addEventListener('DOMContentLoaded', function () {
  const toggleBtn = document.querySelector('.sidebar-toggle');
  const sidebar = document.getElementById('sidebar');
  if (!toggleBtn || !sidebar) {
    // If either element is missing, do nothing but avoid errors
    return;
  }
  // Click toggle
  toggleBtn.addEventListener('click', function () {
    const isCollapsed = sidebar.classList.toggle('collapsed');
    // Update aria-expanded based on visibility (collapsed means hidden)
    toggleBtn.setAttribute('aria-expanded', !isCollapsed);
  });
  // Close sidebar when a navigation link is clicked (mobile)
  sidebar.addEventListener('click', function (e) {
    if (e.target.tagName.toLowerCase() === 'a') {
      // Only collapse on small screens; check computed style or width
      if (window.innerWidth <= 768) {
        sidebar.classList.add('collapsed');
        toggleBtn.setAttribute('aria-expanded', 'false');
      }
    }
  });
  // Escape key closes sidebar on mobile
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && window.innerWidth <= 768) {
      sidebar.classList.add('collapsed');
      toggleBtn.setAttribute('aria-expanded', 'false');
    }
  });
});

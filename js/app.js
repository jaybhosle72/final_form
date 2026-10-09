// NABARD Climate-Aware Credit Risk Assessment — Application Controller
// Handles Hash Routing, Navigation, Active States, and Mobile Menu Toggle

document.addEventListener('DOMContentLoaded', () => {
  initTabNavigation();
  initMobileMenu();
  
  // Listen for browser URL hash changes (Back / Forward navigation)
  window.addEventListener('hashchange', handleRouting);
  
  // Initial route evaluation on page load
  handleRouting();
});

// Route Map
const ROUTES = {
  'dashboard': 'tab-dashboard',
  'loans': 'tab-loans',
  'crops': 'tab-crops',
  'climate': 'tab-climate',
  'risk': 'tab-risk',
  'officer': 'tab-officer',
  'login': 'tab-login',
  'register': 'tab-register'
};

/**
 * Initializes click handlers for navigation tabs
 */
function initTabNavigation() {
  const tabs = document.querySelectorAll('.nav-tab');

  tabs.forEach(tab => {
    tab.addEventListener('click', (e) => {
      const route = tab.getAttribute('data-route') || 'dashboard';
      window.location.hash = `#/${route}`;
      
      // Close mobile drawer on tab click if open
      const navTabsContainer = document.getElementById('mainNav');
      if (navTabsContainer && navTabsContainer.classList.contains('mobile-open')) {
        navTabsContainer.classList.remove('mobile-open');
        const toggleBtn = document.getElementById('mobileNavToggle');
        if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'false');
      }
    });
  });
}

/**
 * Handles client-side hash routing and DOM visibility updates
 */
function handleRouting() {
  const rawHash = window.location.hash || '#/dashboard';
  // Normalize hash (e.g. "#/login" -> "login", "#/register" -> "register")
  let routeName = rawHash.replace(/^#\/?/, '').toLowerCase().trim();
  
  // Default to 'dashboard' if route is unknown or empty
  if (!ROUTES[routeName]) {
    routeName = 'dashboard';
  }

  const targetId = ROUTES[routeName];
  const tabs = document.querySelectorAll('.nav-tab');
  const contents = document.querySelectorAll('.tab-content');
  const mainNav = document.getElementById('mainNav');

  // Hide header navigation tabs on full-screen authentication routes
  const isAuthRoute = (routeName === 'login' || routeName === 'register');
  if (mainNav) {
    mainNav.style.display = isAuthRoute ? 'none' : 'flex';
  }

  // Update active state and ARIA attributes on navigation tabs
  tabs.forEach(tab => {
    const tabRoute = tab.getAttribute('data-route');
    const isTarget = (tabRoute === routeName);
    
    tab.classList.toggle('active', isTarget);
    tab.setAttribute('aria-selected', isTarget ? 'true' : 'false');
  });

  // Toggle visible page section
  contents.forEach(content => {
    const isTarget = (content.id === targetId);
    content.classList.toggle('active', isTarget);
  });

  // Execute route-specific data load & auth route initializers
  if (routeName === 'dashboard' && window.loadFarmerDashboardData) {
    window.loadFarmerDashboardData();
  } else if (routeName === 'loans' && window.prefillLoanApplicationForm) {
    window.prefillLoanApplicationForm();
  } else if (routeName === 'officer' && window.loadOfficerPortalData) {
    window.loadOfficerPortalData();
  } else if (isAuthRoute && window.initAuthPageRoute) {
    window.initAuthPageRoute(routeName);
  }

  // Re-render Lucide icons if loaded
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }

  // Scroll to top of main content on page switch
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/**
 * Initializes mobile responsive hamburger menu toggle
 */
function initMobileMenu() {
  const toggleBtn = document.getElementById('mobileNavToggle');
  const navTabsContainer = document.getElementById('mainNav');

  if (toggleBtn && navTabsContainer) {
    toggleBtn.addEventListener('click', () => {
      const isOpen = navTabsContainer.classList.toggle('mobile-open');
      toggleBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });
  }
}

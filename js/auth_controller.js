// NABARD Climate-Aware Credit Risk Assessment System — Authentication, Dashboard & Application Controller

const AUTH_STORAGE_KEY = 'NABARD_AUTH_SESSION';
const API_BASE_AUTH = (window.location.port === '8000') ? '' : 'http://localhost:8000';
let currentUserSession = null;

document.addEventListener('DOMContentLoaded', () => {
  initAuthSession();
  setupAuthEventListeners();
  checkOAuthCallback();
});

/**
 * Initializes saved session from localStorage/sessionStorage
 */
function initAuthSession() {
  try {
    const saved = localStorage.getItem(AUTH_STORAGE_KEY) || sessionStorage.getItem(AUTH_STORAGE_KEY);
    if (saved) {
      currentUserSession = JSON.parse(saved);
    }
  } catch (e) {
    currentUserSession = null;
  }
  updateNavbarAuthUI();
}

/**
 * Returns authorization header object for API calls
 */
function getAuthHeaders() {
  if (currentUserSession && currentUserSession.access_token) {
    return {
      'Authorization': `Bearer ${currentUserSession.access_token}`,
      'Content-Type': 'application/json'
    };
  }
  return { 'Content-Type': 'application/json' };
}

/**
 * Updates navbar with login trigger or user profile badge
 */
function updateNavbarAuthUI() {
  const container = document.getElementById('navAuthContainer');
  const officerTab = document.getElementById('tab-link-officer');
  if (!container) return;

  if (currentUserSession && currentUserSession.user) {
    const user = currentUserSession.user;
    const isOfficer = user.role === 'bank_officer';
    const roleBadgeClass = isOfficer ? 'badge-teal' : 'badge-cyan';
    const roleLabel = isOfficer ? '🏦 Bank Officer' : `🌾 Farmer (${user.farmer_id || 'ID'})`;

    if (officerTab) officerTab.style.display = isOfficer ? 'inline-flex' : 'none';

    container.innerHTML = `
      <div style="display: flex; align-items: center; gap: 10px;">
        <div style="text-align: right; line-height: 1.2;">
          <div style="font-size: 0.85rem; font-weight: 700; color: var(--text-main);">${escapeHtml(user.full_name || user.sub)}</div>
          <span class="badge ${roleBadgeClass}" style="font-size: 0.7rem; padding: 2px 8px;">${roleLabel}</span>
        </div>
        <button id="btnLogout" class="btn-secondary" style="padding: 5px 10px; font-size: 0.8rem;" title="Sign Out">
          <i data-lucide="log-out"></i> Logout
        </button>
      </div>
    `;

    document.getElementById('btnLogout')?.addEventListener('click', handleLogout);
  } else {
    if (officerTab) officerTab.style.display = 'none';

    container.innerHTML = `
      <a href="#/login" class="btn-primary" style="padding: 6px 14px; font-size: 0.85rem; text-decoration: none; display: inline-flex; align-items: center; gap: 6px;">
        <i data-lucide="user"></i> Login / Register
      </a>
    `;
  }

  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

/**
 * Route initializer for full-screen auth routes (#/login & #/register)
 */
window.initAuthPageRoute = function(routeName) {
  // Clear error banners
  ['loginErrorAlert', 'loginFarmerError', 'loginOfficerError', 'regErrorAlert', 'regFarmerError', 'regOfficerError'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  });
};

/**
 * Handles Auth Event Listeners and Role Selectors
 */
function setupAuthEventListeners() {
  // Role Selection Toggle on Login Page (#/login)
  const btnLoginRoleFarmer = document.getElementById('btnLoginRoleFarmer');
  const btnLoginRoleOfficer = document.getElementById('btnLoginRoleOfficer');
  const formFarmerLogin = document.getElementById('formFarmerLogin');
  const formOfficerLogin = document.getElementById('formOfficerLogin');

  btnLoginRoleFarmer?.addEventListener('click', (e) => {
    e.preventDefault();
    btnLoginRoleFarmer.classList.add('active');
    btnLoginRoleFarmer.style.background = '#ffffff';
    btnLoginRoleFarmer.style.color = '#0d9488';
    btnLoginRoleFarmer.style.boxShadow = '0 1px 3px rgba(0,0,0,0.1)';

    btnLoginRoleOfficer?.classList.remove('active');
    if (btnLoginRoleOfficer) {
      btnLoginRoleOfficer.style.background = 'transparent';
      btnLoginRoleOfficer.style.color = 'var(--text-muted)';
      btnLoginRoleOfficer.style.boxShadow = 'none';
    }

    if (formFarmerLogin) formFarmerLogin.style.display = 'block';
    if (formOfficerLogin) formOfficerLogin.style.display = 'none';
  });

  btnLoginRoleOfficer?.addEventListener('click', (e) => {
    e.preventDefault();
    btnLoginRoleOfficer.classList.add('active');
    btnLoginRoleOfficer.style.background = '#ffffff';
    btnLoginRoleOfficer.style.color = '#0f766e';
    btnLoginRoleOfficer.style.boxShadow = '0 1px 3px rgba(0,0,0,0.1)';

    btnLoginRoleFarmer?.classList.remove('active');
    if (btnLoginRoleFarmer) {
      btnLoginRoleFarmer.style.background = 'transparent';
      btnLoginRoleFarmer.style.color = 'var(--text-muted)';
      btnLoginRoleFarmer.style.boxShadow = 'none';
    }

    if (formOfficerLogin) formOfficerLogin.style.display = 'block';
    if (formFarmerLogin) formFarmerLogin.style.display = 'none';
  });

  // Role Selection Toggle on Registration Page (#/register)
  const btnRegRoleFarmer = document.getElementById('btnRegRoleFarmer');
  const btnRegRoleOfficer = document.getElementById('btnRegRoleOfficer');
  const formFarmerRegister = document.getElementById('formFarmerRegister');
  const formOfficerRegister = document.getElementById('formOfficerRegister');

  btnRegRoleFarmer?.addEventListener('click', (e) => {
    e.preventDefault();
    btnRegRoleFarmer.classList.add('active');
    btnRegRoleFarmer.style.background = '#ffffff';
    btnRegRoleFarmer.style.color = '#0d9488';
    btnRegRoleFarmer.style.boxShadow = '0 1px 3px rgba(0,0,0,0.1)';

    btnRegRoleOfficer?.classList.remove('active');
    if (btnRegRoleOfficer) {
      btnRegRoleOfficer.style.background = 'transparent';
      btnRegRoleOfficer.style.color = 'var(--text-muted)';
      btnRegRoleOfficer.style.boxShadow = 'none';
    }

    if (formFarmerRegister) formFarmerRegister.style.display = 'block';
    if (formOfficerRegister) formOfficerRegister.style.display = 'none';
  });

  btnRegRoleOfficer?.addEventListener('click', (e) => {
    e.preventDefault();
    btnRegRoleOfficer.classList.add('active');
    btnRegRoleOfficer.style.background = '#ffffff';
    btnRegRoleOfficer.style.color = '#0f766e';
    btnRegRoleOfficer.style.boxShadow = '0 1px 3px rgba(0,0,0,0.1)';

    btnRegRoleFarmer?.classList.remove('active');
    if (btnRegRoleFarmer) {
      btnRegRoleFarmer.style.background = 'transparent';
      btnRegRoleFarmer.style.color = 'var(--text-muted)';
      btnRegRoleFarmer.style.boxShadow = 'none';
    }

    if (formOfficerRegister) formOfficerRegister.style.display = 'block';
    if (formFarmerRegister) formFarmerRegister.style.display = 'none';
  });

  // Farmer Login Form
  formFarmerLogin?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btnSubmit = document.getElementById('btnSubmitFarmerLogin');
    if (btnSubmit && btnSubmit.disabled) return;
    if (btnSubmit) btnSubmit.disabled = true;

    const u = document.getElementById('loginFarmerUser').value.trim();
    const p = document.getElementById('loginFarmerPwd').value.trim();
    
    try {
      await executeLogin(u, p, 'farmer', 'loginErrorAlert');
    } finally {
      if (btnSubmit) btnSubmit.disabled = false;
    }
  });

  // Bank Officer Login Form
  formOfficerLogin?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btnSubmit = document.getElementById('btnSubmitOfficerLogin');
    if (btnSubmit && btnSubmit.disabled) return;
    if (btnSubmit) btnSubmit.disabled = true;

    const u = document.getElementById('loginOfficerUser').value.trim();
    const p = document.getElementById('loginOfficerPwd').value.trim();
    
    try {
      await executeLogin(u, p, 'officer', 'loginErrorAlert');
    } finally {
      if (btnSubmit) btnSubmit.disabled = false;
    }
  });

  // Farmer Register Form
  formFarmerRegister?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btnSubmit = document.getElementById('btnSubmitFarmerRegister');
    if (btnSubmit && btnSubmit.disabled) return;
    if (btnSubmit) btnSubmit.disabled = true;

    const u = document.getElementById('regFarmerUser').value.trim();
    const p = document.getElementById('regFarmerPwd').value.trim();
    const name = document.getElementById('regFarmerName').value.trim();
    const dist = document.getElementById('regFarmerDistrict').value.trim();
    const state = document.getElementById('regFarmerState').value.trim();
    const phone = document.getElementById('regFarmerPhone').value.trim();

    try {
      await executeRegister(u, p, name, dist, state, phone, 'regErrorAlert');
    } finally {
      if (btnSubmit) btnSubmit.disabled = false;
    }
  });

  // Bank Officer Register Form (Requires Invite / Authorization Code)
  formOfficerRegister?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btnSubmit = document.getElementById('btnSubmitOfficerRegister');
    if (btnSubmit && btnSubmit.disabled) return;
    if (btnSubmit) btnSubmit.disabled = true;

    const u = document.getElementById('regOfficerUser').value.trim();
    const p = document.getElementById('regOfficerPwd').value.trim();
    const name = document.getElementById('regOfficerName').value.trim();
    const desig = document.getElementById('regOfficerDesignation').value.trim();
    const code = document.getElementById('regOfficerInviteCode')?.value.trim();

    const errorEl = document.getElementById('regErrorAlert') || document.getElementById('regOfficerError');
    if (errorEl) errorEl.style.display = 'none';

    try {
      const res = await fetch(`${API_BASE_AUTH}/api/v2/auth/register-officer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: u, password: p, full_name: name, designation: desig, invite_code: code })
      });
      const data = await res.json();
      if (res.ok && data.access_token) {
        currentUserSession = data;
        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(data));
        updateNavbarAuthUI();
        window.location.hash = '#/officer';
        if (window.loadOfficerPortalData) window.loadOfficerPortalData();
      } else {
        const msg = data.detail?.message || data.detail || 'Officer registration failed.';
        if (errorEl) { errorEl.textContent = msg; errorEl.style.display = 'block'; }
      }
    } catch (err) {
      if (errorEl) { errorEl.textContent = 'Connection error. Make sure backend is running.'; errorEl.style.display = 'block'; }
    } finally {
      if (btnSubmit) btnSubmit.disabled = false;
    }
  });

  // Google Sign-In Button Handler
  document.getElementById('btnGoogleSignIn')?.addEventListener('click', handleGoogleSignInClick);

  // Demo account fast login buttons
  document.querySelectorAll('.btn-demo-login').forEach(btn => {
    btn.addEventListener('click', async () => {
      const u = btn.getAttribute('data-user');
      const p = btn.getAttribute('data-pwd');
      const type = btn.getAttribute('data-type');
      await executeLogin(u, p, type, 'loginErrorAlert');
    });
  });

  // Submit Loan Application Form
  document.getElementById('formSubmitFullLoan')?.addEventListener('submit', handleFullLoanSubmission);

  // Return to Dashboard from Success Screen
  document.getElementById('btnReturnToDashboard')?.addEventListener('click', () => {
    document.getElementById('loanSuccessScreenCard').style.display = 'none';
    document.getElementById('loanFormCard').style.display = 'block';
    window.location.hash = '#/dashboard';
  });

  // Officer Record Lending Decision Form on Risk Page
  document.getElementById('formRecordDecision')?.addEventListener('submit', handleOfficerDecisionRecord);
}

/**
 * Loads Personalized Farmer Dashboard from Backend
 */
async function loadFarmerDashboardData() {
  const dashContainer = document.getElementById('farmerDashboardContainer');
  if (!dashContainer) return;

  if (!currentUserSession || !currentUserSession.access_token) {
    dashContainer.style.display = 'none';
    return;
  }

  try {
    const res = await fetch(`${API_BASE_AUTH}/api/v2/farmers/me/dashboard`, {
      headers: getAuthHeaders()
    });

    if (!res.ok) {
      dashContainer.style.display = 'none';
      return;
    }

    const data = await res.json();
    dashContainer.style.display = 'block';

    // Populate profile fields
    document.getElementById('dashFarmerName').textContent = data.authenticated_user.full_name || 'Farmer';
    document.getElementById('dashFarmerId').textContent = data.profile.farmer_id;
    document.getElementById('dashFarmerLocation').textContent = `${data.profile.district}, ${data.profile.state}`;
    document.getElementById('dashFarmerPhone').textContent = data.profile.phone_number || '+91 98765 XXXXX';
    document.getElementById('dashFarmerVerifiedBadge').textContent = `🟢 ${data.authenticated_user.identity_verification_status}`;

    // Populate KCC Bank details
    const bank = data.bank_summary;
    document.getElementById('dashBankName').textContent = bank.bank_name || 'State Bank of India';
    document.getElementById('dashBankAcctNo').textContent = bank.account_number_masked || 'XXXX-XXXX-1540';
    document.getElementById('dashBankBalance').textContent = typeof bank.account_balance_inr === 'number' ? `₹${bank.account_balance_inr.toLocaleString('en-IN')}` : bank.account_balance_inr;

    // Credit score
    const credit = data.credit_summary;
    document.getElementById('dashCibilScore').textContent = credit.derived_cibil_score || '720';
    document.getElementById('dashRepaymentStatus').textContent = credit.repayment_status || 'Active / Regular';

    // Application status badge
    const status = data.application_status;
    const statusElem = document.getElementById('dashAppStatusBadge');
    if (statusElem) {
      statusElem.textContent = status;
      if (status === 'Approved') statusElem.className = 'badge badge-teal';
      else if (status === 'Rejected') statusElem.className = 'badge badge-rose';
      else if (status.includes('Additional')) statusElem.className = 'badge badge-purple';
      else statusElem.className = 'badge badge-cyan';
    }

    // Render applications list
    const tbody = document.getElementById('dashApplicationsTableBody');
    if (tbody && data.applications) {
      tbody.innerHTML = data.applications.map(app => `
        <tr>
          <td style="padding: 10px 14px; font-weight: 700; color: var(--cyan-hover);">${escapeHtml(app.application_id)}</td>
          <td style="padding: 10px 14px;">₹${Number(app.requested_amount_inr).toLocaleString('en-IN')}</td>
          <td style="padding: 10px 14px;">${escapeHtml(app.loan_purpose)}</td>
          <td style="padding: 10px 14px;">${escapeHtml(app.crop_type)} (${app.farm_area_acres} Acres)</td>
          <td style="padding: 10px 14px;">
            <span class="badge ${app.status === 'Approved' ? 'badge-teal' : (app.status === 'Rejected' ? 'badge-rose' : 'badge-cyan')}">${escapeHtml(app.status)}</span>
          </td>
          <td style="padding: 10px 14px; font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(app.officer_notes || 'In Queue')}</td>
        </tr>
      `).join('');
    }

  } catch (err) {
    console.error('Error loading farmer dashboard:', err);
  }
}

/**
 * Prefills Loan Application Form using Backend Endpoint
 */
async function prefillLoanApplicationForm() {
  if (!currentUserSession || !currentUserSession.access_token) return;

  try {
    const res = await fetch(`${API_BASE_AUTH}/api/v2/farmers/me/application-prefill`, {
      headers: getAuthHeaders()
    });

    if (!res.ok) return;

    const data = await res.json();
    const p = data.prefilled;

    if (!p) return;

    // Prefill fields
    if (document.getElementById('loanApplicantName')) document.getElementById('loanApplicantName').value = p.applicant_name;
    if (document.getElementById('loanPhone')) document.getElementById('loanPhone').value = p.phone_number;
    if (document.getElementById('loanDistrict')) document.getElementById('loanDistrict').value = p.district;
    if (document.getElementById('loanState')) document.getElementById('loanState').value = p.state;
    if (document.getElementById('loanVillage')) document.getElementById('loanVillage').value = p.village_taluka;
    if (document.getElementById('loanCropType')) document.getElementById('loanCropType').value = p.crop_type;
    if (document.getElementById('loanAcres')) document.getElementById('loanAcres').value = p.farm_area_acres;
    if (document.getElementById('loanIrrigation')) document.getElementById('loanIrrigation').value = p.irrigation_type;
    if (document.getElementById('loanWaterSource')) document.getElementById('loanWaterSource').value = p.water_source;
    if (document.getElementById('loanSoilType')) document.getElementById('loanSoilType').value = p.soil_type;
    if (document.getElementById('loanPrevYield')) document.getElementById('loanPrevYield').value = p.previous_crop_yield_tons_ha;
    if (document.getElementById('loanIncome')) document.getElementById('loanIncome').value = p.estimated_annual_income_inr;
    if (document.getElementById('loanAmount')) document.getElementById('loanAmount').value = p.existing_loan_amount_inr || 150000;
    if (document.getElementById('loanPurpose')) document.getElementById('loanPurpose').value = p.existing_loan_purpose || 'Kisan Credit Card (KCC) Crop Input Purchase';
    if (document.getElementById('loanObligations')) document.getElementById('loanObligations').value = p.existing_obligations_inr || 0;
    if (document.getElementById('loanDocStatus')) document.getElementById('loanDocStatus').value = p.land_document_status;

  } catch (err) {
    console.error('Error prefilling loan application:', err);
  }
}

/**
 * Handles Farmer Loan Application Submission with Anti-Duplicate Protection & Success Card
 */
async function handleFullLoanSubmission(e) {
  e.preventDefault();
  const alertBox = document.getElementById('loanSubmitAlert');
  const btnSubmit = document.getElementById('btnSubmitFullLoan');
  
  if (alertBox) alertBox.style.display = 'none';

  if (!currentUserSession || !currentUserSession.access_token) {
    openAuthModal();
    alert('Authentication required. Please log in as a Farmer to submit a loan application.');
    return;
  }

  // Input Validation
  const acres = parseFloat(document.getElementById('loanAcres').value);
  const amount = parseFloat(document.getElementById('loanAmount').value);
  const tenure = parseInt(document.getElementById('loanTenure').value);

  if (isNaN(acres) || acres <= 0) {
    alert('Invalid land area. Please enter a land area greater than 0 acres.');
    return;
  }
  if (isNaN(amount) || amount <= 0) {
    alert('Invalid loan amount. Please enter a loan amount greater than ₹0.');
    return;
  }
  if (isNaN(tenure) || tenure <= 0 || tenure > 120) {
    alert('Invalid tenure. Loan tenure must be between 1 and 120 months.');
    return;
  }

  // Prevent duplicate submissions: Disable button
  if (btnSubmit) {
    btnSubmit.disabled = true;
    btnSubmit.innerHTML = '<i data-lucide="loader-2"></i> Submitting to Bank Officer Review Queue...';
  }

  const payload = {
    applicant_name: document.getElementById('loanApplicantName').value.trim(),
    phone_number: document.getElementById('loanPhone')?.value.trim(),
    village_taluka: document.getElementById('loanVillage')?.value.trim(),
    district: document.getElementById('loanDistrict').value.trim(),
    state: document.getElementById('loanState').value.trim(),
    crop_type: document.getElementById('loanCropType').value.trim(),
    farm_area_acres: acres,
    sowing_date: document.getElementById('loanSowingDate')?.value || '2026-06-15',
    expected_harvest_date: document.getElementById('loanHarvestDate')?.value || '2026-11-20',
    irrigation_type: document.getElementById('loanIrrigation').value,
    water_source: document.getElementById('loanWaterSource')?.value || 'Borewell Grid',
    soil_type: document.getElementById('loanSoilType')?.value || 'Loam Topsoil',
    previous_crop_yield_tons_ha: parseFloat(document.getElementById('loanPrevYield')?.value || 4.5),
    estimated_annual_income: parseFloat(document.getElementById('loanIncome').value),
    loan_amount_inr: amount,
    loan_term_months: tenure,
    loan_purpose: document.getElementById('loanPurpose').value.trim(),
    repayment_source: document.getElementById('loanRepaymentSource')?.value || 'Crop Harvest Sale Proceeds',
    existing_loan_obligations_inr: parseFloat(document.getElementById('loanObligations')?.value || 0),
    land_document_status: document.getElementById('loanDocStatus')?.value || '7/12 Pahani Record Verified'
  };

  try {
    const res = await fetch(`${API_BASE_AUTH}/api/v2/risk/submit-loan`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) {
      if (alertBox) {
        alertBox.className = 'warning-alert';
        alertBox.textContent = data.detail?.message || data.detail || 'Loan submission failed.';
        alertBox.style.display = 'block';
      }
      if (btnSubmit) {
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = '<i data-lucide="send"></i> Submit Loan Application to Officer Review Queue';
      }
      return;
    }

    // Success Screen Toggle
    document.getElementById('loanFormCard').style.display = 'none';
    const successCard = document.getElementById('loanSuccessScreenCard');
    if (successCard) {
      document.getElementById('succAppId').textContent = data.application_id || 'APP-2026-9814';
      document.getElementById('succFarmerId').textContent = data.farmer_id || 'DEMO001';
      document.getElementById('succAmount').textContent = `₹${amount.toLocaleString('en-IN')}`;
      document.getElementById('succTimestamp').textContent = new Date().toLocaleString();
      successCard.style.display = 'block';
    }

    // Refresh Dashboard Data
    loadFarmerDashboardData();

  } catch (err) {
    if (alertBox) {
      alertBox.className = 'warning-alert';
      alertBox.textContent = 'Server communication error while submitting application.';
      alertBox.style.display = 'block';
    }
  } finally {
    if (btnSubmit) {
      btnSubmit.disabled = false;
      btnSubmit.innerHTML = '<i data-lucide="send"></i> Submit Loan Application to Officer Review Queue';
    }
  }
}

/**
 * Executes API Login Call
 */
async function executeLogin(username, password, loginType, errorElemId) {
  const errBox = document.getElementById(errorElemId);
  if (errBox) errBox.style.display = 'none';

  try {
    const res = await fetch(`${API_BASE_AUTH}/api/v2/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, login_type: loginType })
    });

    const data = await res.json();
    if (!res.ok) {
      const msg = data.detail?.message || data.detail || 'Login failed. Please check credentials.';
      if (errBox) {
        errBox.textContent = msg;
        errBox.style.display = 'block';
      }
      return;
    }

    currentUserSession = data;
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(data));
    updateNavbarAuthUI();
    closeAuthModal();

    alert(`Welcome back, ${data.user.full_name || data.user.sub}! Successfully logged in as ${data.user.role === 'bank_officer' ? 'Bank Officer' : 'Farmer'}.`);

    if (data.user.role === 'bank_officer') {
      window.location.hash = '#/risk';
    } else {
      window.location.hash = '#/dashboard';
      loadFarmerDashboardData();
    }
    
    if (window.handleRouting) window.handleRouting();

  } catch (err) {
    if (errBox) {
      errBox.textContent = 'Server connection error. Please ensure backend server is running.';
      errBox.style.display = 'block';
    }
  }
}

/**
 * Executes Farmer Registration API Call
 */
async function executeRegister(username, password, fullName, district, state, phone, errorElemId) {
  const errBox = document.getElementById(errorElemId);
  if (errBox) errBox.style.display = 'none';

  try {
    const res = await fetch(`${API_BASE_AUTH}/api/v2/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username, password, full_name: fullName, district, state, phone
      })
    });

    const data = await res.json();
    if (!res.ok) {
      const msg = data.detail?.message || data.detail || 'Registration failed.';
      if (errBox) {
        errBox.textContent = msg;
        errBox.style.display = 'block';
      }
      return;
    }

    currentUserSession = data;
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(data));
    updateNavbarAuthUI();
    closeAuthModal();

    alert(`Registration successful! Welcome, ${data.user.full_name} (${data.user.farmer_id}).`);
    window.location.hash = '#/dashboard';
    loadFarmerDashboardData();
    if (window.handleRouting) window.handleRouting();

  } catch (err) {
    if (errBox) {
      errBox.textContent = 'Server connection error. Please try again.';
      errBox.style.display = 'block';
    }
  }
}

/**
 * Handles Bank Officer Recording Lending Decision
 */
async function handleOfficerDecisionRecord(e) {
  e.preventDefault();
  const alertBox = document.getElementById('officerDecisionAlert');
  if (alertBox) alertBox.style.display = 'none';

  if (!currentUserSession || !currentUserSession.user || currentUserSession.user.role !== 'bank_officer') {
    alert('Forbidden. Only authenticated Bank Officers can record lending decisions.');
    openAuthModal();
    return;
  }

  const fid = document.getElementById('officerFarmerId').value.trim();
  const dec = document.getElementById('officerDecisionSelect').value;
  const notes = document.getElementById('officerNotes').value.trim();
  const amt = parseFloat(document.getElementById('officerApprovedAmount').value) || null;

  try {
    const res = await fetch(`${API_BASE_AUTH}/api/v2/risk/decision`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        farmer_id: fid,
        decision: dec,
        officer_notes: notes,
        approved_amount_inr: amt
      })
    });

    const data = await res.json();
    if (!res.ok) {
      if (alertBox) {
        alertBox.className = 'warning-alert';
        alertBox.textContent = data.detail?.message || 'Failed to record decision.';
        alertBox.style.display = 'block';
      }
      return;
    }

    if (alertBox) {
      alertBox.className = 'info-alert';
      alertBox.style.background = '#f0fdf4';
      alertBox.style.border = '1px solid #86efac';
      alertBox.style.color = '#166534';
      alertBox.innerHTML = `<strong>✅ Decision Recorded!</strong><br>Decision '${dec}' recorded for Farmer <code>${fid}</code>.`;
      alertBox.style.display = 'block';
    }

  } catch (err) {
    if (alertBox) {
      alertBox.className = 'warning-alert';
      alertBox.textContent = 'Server communication error.';
      alertBox.style.display = 'block';
    }
  }
}

/**
 * Logs out user
 */
function handleLogout() {
  currentUserSession = null;
  localStorage.removeItem(AUTH_STORAGE_KEY);
  sessionStorage.removeItem(AUTH_STORAGE_KEY);
  updateNavbarAuthUI();
  const dashContainer = document.getElementById('farmerDashboardContainer');
  if (dashContainer) dashContainer.style.display = 'none';
  alert('You have logged out.');
  window.location.hash = '#/dashboard';
  if (window.handleRouting) window.handleRouting();
}

function openAuthModal() {
  window.location.hash = '#/login';
}

function closeAuthModal() {
  window.location.hash = '#/dashboard';
}

function escapeHtml(str) {
  return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/**
 * Handles Google OAuth Sign-In button click with environment status checking
 */
async function handleGoogleSignInClick() {
  try {
    const res = await fetch(`${API_BASE_AUTH}/api/v2/auth/google/config`);
    const data = await res.json();

    if (data.is_configured) {
      // Credentials present in environment: redirect to Google Authorization URL
      const urlRes = await fetch(`${API_BASE_AUTH}/api/v2/auth/google/url`);
      const urlData = await urlRes.json();
      if (urlData.authorization_url) {
        window.location.href = urlData.authorization_url;
      } else {
        alert('Failed to obtain Google authorization URL.');
      }
    } else {
      // Credentials not configured in .env: display clean setup notification modal
      const modal = document.getElementById('googleOauthModal');
      if (modal) {
        modal.style.display = 'flex';
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
          window.lucide.createIcons();
        }
      } else {
        alert('Google OAuth Configuration Required:\nPlease copy .env.example to .env and set GOOGLE_CLIENT_ID & GOOGLE_CLIENT_SECRET.\nIn the meantime, use the quick demo login buttons below.');
      }
    }
  } catch (err) {
    console.error('Error checking Google Auth config:', err);
    alert('Could not verify Google OAuth configuration status. Please ensure backend server is running.');
  }
}

/**
 * Checks for Google OAuth authorization code in query string on page load
 */
async function checkOAuthCallback() {
  const urlParams = new URLSearchParams(window.location.search);
  const code = urlParams.get('code');
  if (code) {
    try {
      window.history.replaceState({}, document.title, window.location.pathname + window.location.hash);
      const res = await fetch(`${API_BASE_AUTH}/api/v2/auth/google/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code })
      });
      const data = await res.json();
      if (res.ok && data.access_token) {
        currentUserSession = data;
        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(data));
        updateNavbarAuthUI();
        alert(`Google Sign-In successful! Welcome, ${data.user.full_name} (${data.user.role.toUpperCase()}).`);
        if (data.user.role === 'bank_officer') {
          window.location.hash = '#/officer';
        } else {
          window.location.hash = '#/dashboard';
          loadFarmerDashboardData();
        }
      } else {
        alert(`Google Sign-In failed: ${data.detail?.message || data.detail || 'Authentication error.'}`);
      }
    } catch (err) {
      console.error('Error in Google OAuth callback:', err);
    }
  }
}

window.loadFarmerDashboardData = loadFarmerDashboardData;
window.prefillLoanApplicationForm = prefillLoanApplicationForm;
window.handleGoogleSignInClick = handleGoogleSignInClick;

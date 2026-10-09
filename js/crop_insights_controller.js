// NABARD Agricultural Datasets & Insights Controller
// Controls Dataset Explorer, Table Viewer, Pagination, Filters, and Chart.js Agronomic Visualizations

document.addEventListener('DOMContentLoaded', () => {
  initCropInsights();
});

const API_BASE = (window.location.port === '8000') ? '' : 'http://localhost:8000';

let currentCropDataset = 'crop_recommendation_water';
let currentCropPage = 1;
let cropPageLimit = 10;
let cropSearchQuery = '';
let catalogCache = null;

let chartCropNPKInstance = null;
let chartSoilDistInstance = null;

function initCropInsights() {
  const datasetSelect = document.getElementById('cropDatasetSelect');
  const searchInput = document.getElementById('cropSearchInput');
  const prevBtn = document.getElementById('btnCropPrevPage');
  const nextBtn = document.getElementById('btnCropNextPage');

  if (datasetSelect) {
    datasetSelect.addEventListener('change', (e) => {
      currentCropDataset = e.target.value;
      currentCropPage = 1;
      loadDatasetRecords();
    });
  }

  if (searchInput) {
    let debounceTimer = null;
    searchInput.addEventListener('input', (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        cropSearchQuery = e.target.value.trim();
        currentCropPage = 1;
        loadDatasetRecords();
      }, 300);
    });
  }

  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      if (currentCropPage > 1) {
        currentCropPage--;
        loadDatasetRecords();
      }
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      currentCropPage++;
      loadDatasetRecords();
    });
  }

  // Load datasets list, summary metrics, and insights
  fetchDatasetsList();
  fetchSummaryMetrics();
  loadAgronomicInsights();
}

async function getLocalCatalog() {
  if (catalogCache) return catalogCache;
  try {
    const res = await fetch('data/catalog.json');
    if (res.ok) {
      catalogCache = await res.json();
      return catalogCache;
    }
  } catch (e) {
    console.warn('[CropService] Local catalog.json fetch failed:', e);
  }
  return null;
}

async function fetchDatasetsList() {
  const datasetSelect = document.getElementById('cropDatasetSelect');
  if (!datasetSelect) return;

  try {
    const res = await fetch(`${API_BASE}/api/v2/crops/datasets`);
    if (res.ok) {
      const data = await res.json();
      if (data.datasets && data.datasets.length > 0) {
        populateDatasetDropdown(data.datasets);
        loadDatasetRecords();
        return;
      }
    }
  } catch (err) {
    console.warn('[CropService] Backend datasets API call failed, falling back to data/catalog.json:', err);
  }

  // Fallback to local catalog.json
  const cat = await getLocalCatalog();
  if (cat && cat.datasets) {
    populateDatasetDropdown(cat.datasets);
  }
  loadDatasetRecords();
}

function populateDatasetDropdown(datasets) {
  const datasetSelect = document.getElementById('cropDatasetSelect');
  if (!datasetSelect) return;

  datasetSelect.innerHTML = '';
  datasets.forEach(ds => {
    const opt = document.createElement('option');
    opt.value = ds.dataset_id;
    opt.textContent = `${ds.dataset_id} — ${ds.domain} (${(ds.total_rows || 0).toLocaleString()} rows)`;
    datasetSelect.appendChild(opt);
  });
  datasetSelect.value = currentCropDataset;
}

async function fetchSummaryMetrics() {
  try {
    const res = await fetch(`${API_BASE}/api/v2/crops/summary`);
    if (res.ok) {
      const data = await res.json();
      updateSummaryDOM(
        data.total_datasets,
        data.total_records,
        data.total_crop_categories,
        data.soil_types_available
      );
      return;
    }
  } catch (err) {
    console.warn('[CropService] Backend summary API failed, using fallback:', err);
  }

  // Fallback
  const cat = await getLocalCatalog();
  if (cat && cat.summary) {
    updateSummaryDOM(
      cat.summary.total_datasets || 12,
      cat.summary.total_ingested_rows || 186676,
      45,
      17
    );
  } else {
    updateSummaryDOM(12, 186676, 45, 17);
  }
}

function updateSummaryDOM(totalDs, totalRec, cropCats, soilTypes) {
  const elTotalDs = document.getElementById('dashTotalDatasets');
  const elTotalRec = document.getElementById('dashTotalRecords');
  const elCropCats = document.getElementById('dashCropCategories');
  const elSoilTypes = document.getElementById('dashSoilTypes');

  if (elTotalDs) elTotalDs.textContent = `${totalDs} Datasets`;
  if (elTotalRec) elTotalRec.textContent = `${totalRec.toLocaleString()} Rows`;
  if (elCropCats) elCropCats.textContent = `${cropCats} Crops`;
  if (elSoilTypes) elSoilTypes.textContent = `${soilTypes} Soil Types`;

  const elCropsStatTotalRec = document.getElementById('cropsStatTotalRecords');
  const elCropsStatDatasets = document.getElementById('cropsStatTotalDatasets');
  if (elCropsStatTotalRec) elCropsStatTotalRec.textContent = `${totalRec.toLocaleString()}`;
  if (elCropsStatDatasets) elCropsStatDatasets.textContent = `${totalDs}`;
}

async function loadDatasetRecords() {
  const tableHead = document.getElementById('cropTableHead');
  const tableBody = document.getElementById('cropTableBody');
  const pageIndicator = document.getElementById('cropPageIndicator');
  const datasetMetaBadge = document.getElementById('cropDatasetMetaBadge');
  const prevBtn = document.getElementById('btnCropPrevPage');
  const nextBtn = document.getElementById('btnCropNextPage');

  if (!tableBody) return;

  tableBody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 2rem; color: var(--text-muted);"><i data-lucide="loader-2" class="spin"></i> Loading records...</td></tr>`;

  // 1. Try Backend API first
  try {
    let url = `${API_BASE}/api/v2/crops/data/${currentCropDataset}?page=${currentCropPage}&limit=${cropPageLimit}`;
    if (cropSearchQuery) {
      url += `&search=${encodeURIComponent(cropSearchQuery)}`;
    }

    const res = await fetch(url);
    if (res.ok) {
      const result = await res.json();
      renderRecordsTable(result);
      return;
    }
  } catch (err) {
    console.warn('[CropService] Backend records API call failed, attempting local catalog fallback:', err);
  }

  // 2. Fallback to local catalog.json
  const cat = await getLocalCatalog();
  if (cat && cat.datasets) {
    const ds = cat.datasets.find(d => d.dataset_id === currentCropDataset);
    if (ds) {
      let sampleRows = [];
      (ds.files || []).forEach(f => {
        if (f.sample_rows) sampleRows = sampleRows.concat(f.sample_rows);
      });

      if (cropSearchQuery) {
        const sq = cropSearchQuery.toLowerCase();
        sampleRows = sampleRows.filter(r => 
          Object.values(r).some(v => String(v).toLowerCase().includes(sq))
        );
      }

      const totalCount = sampleRows.length;
      const totalPages = Math.max(1, Math.ceil(totalCount / cropPageLimit));
      const startIdx = (currentCropPage - 1) * cropPageLimit;
      const paginated = sampleRows.slice(startIdx, startIdx + cropPageLimit);

      renderRecordsTable({
        domain: ds.domain,
        total_records: ds.total_rows || totalCount,
        page: currentCropPage,
        total_pages: totalPages,
        sample_preview_total: totalCount,
        data: paginated
      });
      return;
    }
  }

  tableBody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 2rem; color: var(--rose);">Error loading dataset records. Please check backend connection.</td></tr>`;
}

function renderRecordsTable(result) {
  const tableHead = document.getElementById('cropTableHead');
  const tableBody = document.getElementById('cropTableBody');
  const pageIndicator = document.getElementById('cropPageIndicator');
  const datasetMetaBadge = document.getElementById('cropDatasetMetaBadge');
  const prevBtn = document.getElementById('btnCropPrevPage');
  const nextBtn = document.getElementById('btnCropNextPage');

  if (datasetMetaBadge) {
    datasetMetaBadge.textContent = `${result.domain} | ${(result.total_records || 0).toLocaleString()} Total Records`;
  }

  if (pageIndicator) {
    pageIndicator.textContent = `Page ${result.page} of ${result.total_pages} (${result.sample_preview_total || 0} preview records)`;
  }

  if (prevBtn) prevBtn.disabled = (result.page <= 1);
  if (nextBtn) nextBtn.disabled = (result.page >= result.total_pages);

  const rows = result.data || [];
  if (rows.length === 0) {
    tableBody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 2rem; color: var(--text-muted);">No matching records found.</td></tr>`;
    return;
  }

  // Dynamic headers based on first record keys
  const headers = Object.keys(rows[0]);
  if (tableHead) {
    let trHead = '<tr>';
    headers.forEach(h => {
      trHead += `<th style="text-transform: capitalize; padding: 10px 14px; background: #f8fafc; border-bottom: 2px solid var(--border-subtle);">${h.replace(/_/g, ' ')}</th>`;
    });
    trHead += '</tr>';
    tableHead.innerHTML = trHead;
  }

  // Render body rows
  let trBody = '';
  rows.forEach(r => {
    trBody += '<tr>';
    headers.forEach(h => {
      const val = (r[h] !== null && r[h] !== undefined) ? r[h] : '-';
      trBody += `<td style="padding: 10px 14px; border-bottom: 1px solid var(--border-subtle); font-size: 0.88rem;">${val}</td>`;
    });
    trBody += '</tr>';
  });
  tableBody.innerHTML = trBody;

  if (window.lucide) lucide.createIcons();
}

async function loadAgronomicInsights() {
  const fallbackInsights = {
    crop_recommendations: [
      {"crop": "Rice", "samples": 100, "avg_N": 79.9, "avg_P": 47.6, "avg_K": 39.9, "avg_rainfall_mm": 236.2},
      {"crop": "Maize", "samples": 100, "avg_N": 77.8, "avg_P": 48.4, "avg_K": 19.8, "avg_rainfall_mm": 84.8},
      {"crop": "Jute", "samples": 100, "avg_N": 78.4, "avg_P": 46.8, "avg_K": 39.9, "avg_rainfall_mm": 174.3},
      {"crop": "Cotton", "samples": 100, "avg_N": 117.8, "avg_P": 46.2, "avg_K": 19.6, "avg_rainfall_mm": 80.4},
      {"crop": "Coconut", "samples": 100, "avg_N": 21.9, "avg_P": 16.9, "avg_K": 30.6, "avg_rainfall_mm": 175.7},
      {"crop": "Coffee", "samples": 100, "avg_N": 101.2, "avg_P": 28.7, "avg_K": 29.9, "avg_rainfall_mm": 158.1},
      {"crop": "Chickpea", "samples": 100, "avg_N": 40.1, "avg_P": 67.8, "avg_K": 79.9, "avg_rainfall_mm": 80.1},
      {"crop": "Kidneybeans", "samples": 100, "avg_N": 20.8, "avg_P": 67.5, "avg_K": 20.1, "avg_rainfall_mm": 105.9}
    ],
    soil_type_distribution: [
      {"type": "Clayey", "share_percent": 28.4},
      {"type": "Loamy", "share_percent": 34.2},
      {"type": "Sandy", "share_percent": 14.1},
      {"type": "Black Soil", "share_percent": 16.5},
      {"type": "Red Soil", "share_percent": 6.8}
    ]
  };

  try {
    const res = await fetch(`${API_BASE}/api/v2/crops/insights`);
    if (res.ok) {
      const data = await res.json();
      renderCropNPKChart(data.crop_recommendations || fallbackInsights.crop_recommendations);
      renderSoilDistributionChart(data.soil_type_distribution || fallbackInsights.soil_type_distribution);
      return;
    }
  } catch (err) {
    console.warn('[CropService] Could not load insights live, using fallback:', err);
  }

  renderCropNPKChart(fallbackInsights.crop_recommendations);
  renderSoilDistributionChart(fallbackInsights.soil_type_distribution);
}

function renderCropNPKChart(cropData) {
  const canvas = document.getElementById('chartCropNPK');
  if (!canvas || !window.Chart) return;

  if (chartCropNPKInstance) {
    chartCropNPKInstance.destroy();
  }

  const labels = cropData.map(d => d.crop);
  const dataN = cropData.map(d => d.avg_N);
  const dataP = cropData.map(d => d.avg_P);
  const dataK = cropData.map(d => d.avg_K);

  chartCropNPKInstance = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        { label: 'Nitrogen (N)', data: dataN, backgroundColor: '#0d9488' },
        { label: 'Phosphorus (P)', data: dataP, backgroundColor: '#06b6d4' },
        { label: 'Potassium (K)', data: dataK, backgroundColor: '#6366f1' }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top' },
        tooltip: { mode: 'index', intersect: false }
      },
      scales: {
        x: { grid: { display: false } },
        y: { beginAtZero: true, title: { display: true, text: 'Nutrient Content (kg/ha)' } }
      }
    }
  });
}

function renderSoilDistributionChart(soilData) {
  const canvas = document.getElementById('chartSoilDistribution');
  if (!canvas || !window.Chart) return;

  if (chartSoilDistInstance) {
    chartSoilDistInstance.destroy();
  }

  const labels = soilData.map(s => s.type);
  const shares = soilData.map(s => s.share_percent);

  chartSoilDistInstance = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: shares,
        backgroundColor: ['#0d9488', '#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899']
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'right' }
      }
    }
  });
}

/**
 * NABARD FIN-03 Interactive Leaflet Field Selector & Polygon Capture Tool
 * 
 * Features:
 * - Uses OpenStreetMap tiles with standard required attribution.
 * - Guarantees full map container rendering (prevents grey tile boxes).
 * - Interactive click-to-draw polygon mode with live vertex counters and status overlay banner.
 * - Calculates geodesic area in Acres & Hectares.
 * - Exports GeoJSON polygon coordinates & auto-populates land area into application form.
 * - Decoupled from satellite data fetching.
 */

class MapFieldSelector {
  constructor(containerId = 'fieldSelectorMap') {
    this.containerId = containerId;
    this.map = null;
    this.drawnPolygon = null;
    this.polyline = null;
    this.vertexMarkers = [];
    this.polygonCoords = []; // Array of [lat, lng]
    this.isDrawing = true;   // Active by default for immediate click-to-draw
    this.statusControl = null;

    this.initMap();
  }

  initMap() {
    const container = document.getElementById(this.containerId);
    if (!container) return;

    // Center default on India (Vidarbha agricultural region)
    this.map = L.map(this.containerId, {
      zoomControl: true,
      scrollWheelZoom: true
    }).setView([21.1458, 79.0882], 13);

    // Standard OpenStreetMap Tile Layer with Required Attribution
    const osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors'
    });
    osmLayer.addTo(this.map);

    // Ensure map resizes properly across all viewport sizes
    [100, 300, 600, 1000].forEach(delay => {
      setTimeout(() => {
        if (this.map) this.map.invalidateSize();
      }, delay);
    });

    // Create Map Status Overlay Banner
    this.createStatusBanner();

    // Map Click Listener to add Polygon Vertices
    this.map.on('click', (e) => this.handleMapClick(e));

    // Cursor indicator
    this.map.getContainer().style.cursor = 'crosshair';
  }

  createStatusBanner() {
    const StatusControl = L.Control.extend({
      options: { position: 'topright' },
      onAdd: function () {
        const div = L.DomUtil.create('div', 'map-status-banner');
        div.style.background = '#0f172a';
        div.style.color = '#f8fafc';
        div.style.padding = '6px 12px';
        div.style.borderRadius = '6px';
        div.style.border = '1px solid #334155';
        div.style.fontSize = '12px';
        div.style.fontWeight = '600';
        div.style.boxShadow = '0 2px 6px rgba(0,0,0,0.3)';
        div.id = 'mapStatusBanner';
        div.innerHTML = '✏️ <strong>Click map</strong> to add field corners';
        return div;
      }
    });

    this.statusControl = new StatusControl();
    this.map.addControl(this.statusControl);
  }

  handleMapClick(e) {
    if (!this.isDrawing) return;

    const lat = parseFloat(e.latlng.lat.toFixed(6));
    const lng = parseFloat(e.latlng.lng.toFixed(6));

    this.polygonCoords.push([lat, lng]);
    const pointIndex = this.polygonCoords.length;

    // Create vertex marker with point number tooltip
    const marker = L.circleMarker([lat, lng], {
      radius: 7,
      fillColor: '#0ea5e9',
      color: '#ffffff',
      weight: 2,
      opacity: 1,
      fillOpacity: 1
    }).addTo(this.map);

    marker.bindTooltip(`Point ${pointIndex}`, { permanent: false, direction: 'top' });
    this.vertexMarkers.push(marker);

    // If clicking first marker again when points >= 3, close polygon
    if (pointIndex > 1) {
      marker.on('click', (evt) => {
        L.DomEvent.stopPropagation(evt);
        if (this.polygonCoords.length >= 3) {
          this.stopDrawing();
        }
      });
    }

    this.updatePolygon();
  }

  startDrawing() {
    this.clearDrawing();
    this.isDrawing = true;
    this.map.getContainer().style.cursor = 'crosshair';
    this.updateBannerText('✏️ <strong>Click map</strong> to add field corners');
  }

  stopDrawing() {
    this.isDrawing = false;
    this.map.getContainer().style.cursor = '';
    if (this.polygonCoords.length >= 3) {
      const areaM2 = this.calculateGeodesicArea(this.polygonCoords);
      const acres = (areaM2 / 4046.86).toFixed(2);
      this.updateBannerText(`✅ <strong>Field Closed</strong> (${acres} Acres)`);
      if (this.drawnPolygon) {
        this.map.fitBounds(this.drawnPolygon.getBounds(), { padding: [25, 25] });
      }
    }
  }

  clearDrawing() {
    this.isDrawing = true;
    this.polygonCoords = [];
    this.map.getContainer().style.cursor = 'crosshair';

    if (this.drawnPolygon) {
      this.map.removeLayer(this.drawnPolygon);
      this.drawnPolygon = null;
    }
    if (this.polyline) {
      this.map.removeLayer(this.polyline);
      this.polyline = null;
    }

    this.vertexMarkers.forEach(m => this.map.removeLayer(m));
    this.vertexMarkers = [];

    this.updateBannerText('✏️ <strong>Click map</strong> to add field corners');
    this.updateUI(0, []);
  }

  updatePolygon() {
    if (this.polygonCoords.length < 1) return;

    // Remove old layers
    if (this.drawnPolygon) {
      this.map.removeLayer(this.drawnPolygon);
      this.drawnPolygon = null;
    }
    if (this.polyline) {
      this.map.removeLayer(this.polyline);
      this.polyline = null;
    }

    if (this.polygonCoords.length === 2) {
      // Draw connecting line for 2 points
      this.polyline = L.polyline(this.polygonCoords, {
        color: '#0ea5e9',
        weight: 3,
        dashArray: '5, 5'
      }).addTo(this.map);
      this.updateBannerText(`📍 <strong>2 points placed</strong> (click 3rd point to create polygon)`);
    } else if (this.polygonCoords.length >= 3) {
      // Draw closed polygon for 3+ points
      this.drawnPolygon = L.polygon(this.polygonCoords, {
        color: '#10b981',
        fillColor: '#10b981',
        fillOpacity: 0.35,
        weight: 3
      }).addTo(this.map);

      const areaM2 = this.calculateGeodesicArea(this.polygonCoords);
      const areaAcres = parseFloat((areaM2 / 4046.86).toFixed(2));
      const areaHectares = parseFloat((areaM2 / 10000).toFixed(2));

      this.updateBannerText(`🌾 <strong>Field Polygon (${this.polygonCoords.length} points)</strong>: ${areaAcres} Acres`);

      // GeoJSON coordinates [longitude, latitude]
      const geoJsonCoords = this.polygonCoords.map(([lat, lng]) => [lng, lat]);
      geoJsonCoords.push([this.polygonCoords[0][1], this.polygonCoords[0][0]]); // Close loop

      this.updateUI(areaAcres, geoJsonCoords, areaHectares);
    }
  }

  updateBannerText(htmlContent) {
    const banner = document.getElementById('mapStatusBanner');
    if (banner) {
      banner.innerHTML = htmlContent;
    }
  }

  // Geodesic Area Calculation (Shoelace formula on WGS84 ellipsoid)
  calculateGeodesicArea(coords) {
    if (coords.length < 3) return 0;
    const RAD = Math.PI / 180;
    const R = 6378137; // Earth radius in meters
    let total = 0;

    for (let i = 0; i < coords.length; i++) {
      const p1 = coords[i];
      const p2 = coords[(i + 1) % coords.length];
      total += (p2[1] * RAD - p1[1] * RAD) * (2 + Math.sin(p1[0] * RAD) + Math.sin(p2[0] * RAD));
    }
    return Math.abs(total * R * R / 2.0);
  }

  updateUI(acres, geoJsonCoords, hectares = 0) {
    const areaEl = document.getElementById('selectedFieldArea');
    const inputLand = document.getElementById('landAcres');
    const geoJsonEl = document.getElementById('fieldGeoJSONDisplay');

    if (areaEl) {
      areaEl.textContent = acres > 0 ? `${acres} Acres (${hectares} Ha)` : 'No field selected';
    }
    if (inputLand && acres > 0) {
      inputLand.value = acres;
    }
    if (geoJsonEl) {
      const geoJson = {
        type: "Feature",
        geometry: {
          type: "Polygon",
          coordinates: [geoJsonCoords]
        },
        properties: {
          areaAcres: acres,
          areaHectares: hectares
        }
      };
      geoJsonEl.textContent = geoJsonCoords.length > 0 ? JSON.stringify(geoJson, null, 2) : '// Click on map to add field corners';
    }
  }
}

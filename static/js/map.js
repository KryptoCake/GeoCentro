document.addEventListener('DOMContentLoaded', function() {
    // 1. Initialize Map centered on Central America to capture Guatemala, Nicaragua and Costa Rica
    const map = L.map('main-map').setView([12.5, -87.5], 6);
    
    // Sleek CartoDB Dark Matter tiles
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);

    // Initialize LayerGroups and add them to the map
    const localSismosLayer = L.layerGroup().addTo(map);
    const usgsSismosLayer = L.layerGroup().addTo(map);
    const volcanoesLayer = L.layerGroup().addTo(map);
    
    // Add Layer Control to the map
    const overlayMaps = {
        "Sismos Locales (INETER/OVSICORI)": localSismosLayer,
        "Sismos Globales (USGS)": usgsSismosLayer,
        "Volcanes Activos": volcanoesLayer
    };
    L.control.layers(null, overlayMaps, { position: 'topright' }).addTo(map);
    
    // Volcano Icons (Pulsing Div Icon)
    const volcanoIcon = L.divIcon({
        className: 'volcano-marker-wrapper',
        html: '<div class="volcano-marker-dot"></div><div class="volcano-marker-pulse"></div>',
        iconSize: [20, 20],
        iconAnchor: [10, 10]
    });
    
    // Volcanoes Data
    const volcanoes = [
        { name: "Volcán San Cristóbal", lat: 12.7019, lon: -87.0039, height: "1,745 m", status: "Activo", webcams: [{ code: "v_sancris2", label: "Cámara Principal" }] },
        { name: "Volcán Telica", lat: 12.6061, lon: -86.8400, height: "1,061 m", status: "Activo", webcams: [{ code: "v_telica", label: "Cámara Principal" }] },
        { name: "Volcán Cerro Negro", lat: 12.5061, lon: -86.7019, height: "728 m", status: "Activo", webcams: [] },
        { name: "Volcán Momotombo", lat: 12.4231, lon: -86.5392, height: "1,297 m", status: "Activo", webcams: [{ code: "v_momotombo", label: "Cámara Principal" }] },
        { name: "Volcán Masaya", lat: 11.9844, lon: -86.1689, height: "635 m", status: "Activo", webcams: [{ code: "v_masaya", label: "Cráter Principal" }, { code: "v_masaya4", label: "Sector Nindirí" }] },
        { name: "Volcán Concepción", lat: 11.5378, lon: -85.6222, height: "1,610 m", status: "Activo", webcams: [{ code: "v_concepcion2", label: "Sector Concepción 2" }, { code: "v_concepcion3", label: "Sector Concepción 3" }] },
        // Costa Rica Volcanoes
        { name: "Volcán Poás", lat: 10.1983, lon: -84.2306, height: "2,708 m", status: "Activo", webcams: [{ code: "v_craterpoas", label: "Cráter Principal" }, { code: "v_chahuites", label: "Sector Chahuites" }] },
        { name: "Volcán Rincón de la Vieja", lat: 10.8306, lon: -85.3242, height: "1,916 m", status: "Activo", webcams: [{ code: "v_curubande", label: "Sector Curubandé" }, { code: "v_rincon2", label: "Mirador Rincón" }] },
        { name: "Volcán Irazú", lat: 9.9792, lon: -83.8525, height: "3,432 m", status: "Activo", webcams: [{ code: "v_irazu", label: "Cráter Principal" }] },
        { name: "Volcán Turrialba", lat: 10.0250, lon: -83.7667, height: "3,340 m", status: "Activo", webcams: [{ code: "v_turrialba", label: "Cráter Principal" }] },
        // Guatemala Volcanoes
        { name: "Volcán de Fuego", lat: 14.4747, lon: -90.8808, height: "3,763 m", status: "Activo", webcams: [{ code: "v_fuego_so", label: "Flanco Suroeste" }, { code: "v_fuego_se", label: "Flanco Sureste" }, { code: "v_fuego_ceniza", label: "Barranca Ceniza" }] },
        { name: "Volcán Santiaguito", lat: 14.7561, lon: -91.5519, height: "2,500 m", status: "Activo", webcams: [{ code: "v_santiaguito", label: "San Marcos Palajunoj" }] }
    ];
    
    // Add Volcano Markers
    volcanoes.forEach(v => {
        let popupContent = `
            <div class="map-popup volcano-popup" style="color: #111827; font-family: 'Outfit', sans-serif;">
                <h4 style="color: #111827; font-size: 0.95rem; font-weight: 700; margin-bottom: 6px;"><i class="fa-solid fa-mountain" style="color: #ff5722; margin-right: 5px;"></i> ${v.name}</h4>
                <p style="font-size: 0.8rem; margin: 2px 0; color: #374151;"><strong>Altura:</strong> ${v.height}</p>
                <p style="font-size: 0.8rem; margin: 2px 0; color: #374151;"><strong>Estado:</strong> <span class="status-badge active" style="background: rgba(76, 175, 80, 0.15); color: #4caf50; padding: 2px 8px; border-radius: 10px; font-weight: 600; font-size: 0.75rem;">${v.status}</span></p>
        `;
        if (v.webcams && v.webcams.length > 0) {
            v.webcams.forEach(cam => {
                popupContent += `<button class="btn btn-primary btn-sm btn-view-cam" data-cam="${cam.code}" data-name="${v.name} (${cam.label})" style="margin-top: 8px; width: 100%; border-radius: 6px; padding: 6px; cursor: pointer; font-size: 0.8rem; display: flex; align-items: center; justify-content: center; gap: 6px;"><i class="fa-solid fa-camera"></i> Ver ${cam.label}</button>`;
            });
        }
        popupContent += `</div>`;
        
        L.marker([v.lat, v.lon], { icon: volcanoIcon })
            .bindPopup(popupContent)
            .addTo(volcanoesLayer);
    });
    
    // Webcam Modal DOM Elements
    const modal = document.getElementById('webcam-modal');
    const modalTitle = document.getElementById('modal-webcam-title');
    const modalImg = document.getElementById('modal-webcam-img');
    const modalTime = document.getElementById('modal-webcam-time');
    const closeModal = document.getElementById('close-webcam-modal');
    const refreshBtn = document.getElementById('btn-refresh-modal-webcam');
    
    let activeCamCode = '';
    
    // Handle opening webcam modal
    document.addEventListener('click', function(e) {
        const btn = e.target.closest('.btn-view-cam');
        if (btn) {
            const camCode = btn.getAttribute('data-cam');
            const name = btn.getAttribute('data-name');
            openWebcam(camCode, name);
        }
    });
    
    function openWebcam(camCode, name) {
        activeCamCode = camCode;
        modalTitle.textContent = `Cámara en Vivo - ${name}`;
        modalImg.src = `/api/webcam/proxy?volcan=${camCode}&t=${new Date().getTime()}`;
        modalTime.textContent = `Actualizado: ${new Date().toLocaleTimeString()}`;
        modal.style.display = 'flex';
    }
    
    if (closeModal) {
        closeModal.onclick = function() {
            modal.style.display = 'none';
            modalImg.src = ''; // Stop loading image in background
        };
    }
    
    if (refreshBtn) {
        refreshBtn.onclick = function() {
            if (activeCamCode) {
                modalImg.src = `/api/webcam/proxy?volcan=${activeCamCode}&t=${new Date().getTime()}`;
                modalTime.textContent = `Actualizado: ${new Date().toLocaleTimeString()}`;
            }
        };
    }
    
    // Close modal when clicking outside
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = 'none';
            modalImg.src = '';
        }
    };
    
    // Sismos marker layers references
    let localMarkers = [];
    let usgsMarkers = [];
    
    // In-memory data store
    let localSismos = [];
    let usgsSismos = [];
    let activeTab = 'locales'; // 'locales' or 'usgs'
    
    // Fetch and draw recent sismos
    function loadSismosData() {
        const listContainer = document.getElementById('recent-sismos-list');
        if (listContainer) {
            listContainer.innerHTML = `
                <div class="loading-placeholder">
                    <i class="fa-solid fa-spinner fa-spin"></i> Cargando eventos...
                </div>
            `;
        }

        const fetchLocal = fetch('/api/sismos?limit=100').then(res => res.json());
        const fetchUsgs = fetch('/api/sismos/usgs?limit=100').then(res => res.json());
        
        Promise.all([fetchLocal, fetchUsgs])
            .then(([localData, usgsData]) => {
                localSismos = localData;
                usgsSismos = usgsData;
                
                // Clear and render local markers
                localMarkers.forEach(m => localSismosLayer.removeLayer(m));
                localMarkers = [];
                renderLocalMarkers(localSismos);
                
                // Clear and render USGS markers
                usgsMarkers.forEach(m => usgsSismosLayer.removeLayer(m));
                usgsMarkers = [];
                renderUsgsMarkers(usgsSismos);
                
                // Update stats (using local sismos as primary regional reference)
                updateStats(localSismos);
                
                // Refresh list based on the active tab
                refreshSidebarList();
            })
            .catch(err => {
                console.error("Error loading sismos data:", err);
                if (listContainer) {
                    listContainer.innerHTML = `<div class="error-text" style="color: #f44336; padding: 20px; text-align: center;"><i class="fa-solid fa-circle-exclamation"></i> Error al cargar datos de sismos.</div>`;
                }
            });
    }

    function renderLocalMarkers(data) {
        data.forEach((s) => {
            const lat = s.latitud;
            const lon = s.longitud;
            const mag = s.magnitud;
            const depth = s.profundidad;
            
            let markerColor = '#4caf50'; // Low
            let markerClass = 'mag-low';
            if (mag >= 3.0 && mag < 5.0) {
                markerColor = '#ffb300'; // Med
                markerClass = 'mag-med';
            } else if (mag >= 5.0) {
                markerColor = '#f44336'; // High
                markerClass = 'mag-high';
            }
            
            const radiusSize = Math.max(mag * 3.5, 6);
            
            const popupHTML = `
                <div class="map-popup sismo-popup" style="color: #f1f5f9; font-family: 'Outfit', sans-serif;">
                    <div class="popup-mag-badge ${markerClass}" style="font-size: 1.1rem; font-weight: 800; margin-bottom: 6px; display: inline-block;">Mw ${mag.toFixed(1)}</div>
                    <h4 style="font-size: 0.95rem; font-weight: 700; margin-bottom: 6px; line-height: 1.3; color: #f1f5f9;">${s.descripcion}</h4>
                    <p style="font-size: 0.8rem; margin: 2px 0; color: #d1d5db;"><strong>Fecha (UTC):</strong> ${s.fecha_utc}</p>
                    <p style="font-size: 0.8rem; margin: 2px 0; color: #d1d5db;"><strong>Hora (UTC):</strong> ${s.hora_utc}</p>
                    <p style="font-size: 0.8rem; margin: 2px 0; color: #d1d5db;"><strong>Profundidad:</strong> ${depth} km</p>
                    <p style="font-size: 0.8rem; margin: 2px 0; color: #d1d5db;"><strong>Coordenadas:</strong> ${lat.toFixed(3)}, ${lon.toFixed(3)}</p>
                    <p style="font-size: 0.8rem; margin: 4px 0 0 0; color: var(--text-muted); font-style: italic;">Sismo Regional (Locales)</p>
                </div>
            `;
            
            const marker = L.circleMarker([lat, lon], {
                radius: radiusSize,
                fillColor: markerColor,
                color: markerColor,
                weight: 1.5,
                opacity: 0.9,
                fillOpacity: 0.6
            })
            .bindPopup(popupHTML);
            
            marker.sismoId = s.id;
            localSismosLayer.addLayer(marker);
            localMarkers.push(marker);
        });
    }

    function renderUsgsMarkers(data) {
        data.forEach((s) => {
            const lat = s.latitud;
            const lon = s.longitud;
            const mag = s.magnitud;
            const depth = s.profundidad;
            
            let markerColor = '#4caf50'; // Low
            let markerClass = 'mag-low';
            if (mag >= 3.0 && mag < 5.0) {
                markerColor = '#ffb300'; // Med
                markerClass = 'mag-med';
            } else if (mag >= 5.0) {
                markerColor = '#f44336'; // High
                markerClass = 'mag-high';
            }
            
            const radiusSize = Math.max(mag * 3.5, 6);
            
            const popupHTML = `
                <div class="map-popup sismo-popup" style="color: #f1f5f9; font-family: 'Outfit', sans-serif;">
                    <div class="popup-mag-badge ${markerClass}" style="font-size: 1.1rem; font-weight: 800; margin-bottom: 6px; display: inline-block;">Mw ${mag.toFixed(1)}</div>
                    <h4 style="font-size: 0.95rem; font-weight: 700; margin-bottom: 6px; line-height: 1.3; color: #f1f5f9;">${s.descripcion}</h4>
                    <p style="font-size: 0.8rem; margin: 2px 0; color: #d1d5db;"><strong>Fecha (UTC):</strong> ${s.fecha_utc}</p>
                    <p style="font-size: 0.8rem; margin: 2px 0; color: #d1d5db;"><strong>Hora (UTC):</strong> ${s.hora_utc}</p>
                    <p style="font-size: 0.8rem; margin: 2px 0; color: #d1d5db;"><strong>Profundidad:</strong> ${depth} km</p>
                    <p style="font-size: 0.8rem; margin: 2px 0; color: #d1d5db;"><strong>Coordenadas:</strong> ${lat.toFixed(3)}, ${lon.toFixed(3)}</p>
                    <p style="font-size: 0.8rem; margin: 2px 0; color: #d1d5db;"><strong>País:</strong> ${s.pais}</p>
                    ${s.url ? `<a href="${s.url}" target="_blank" style="display: inline-flex; align-items: center; gap: 5px; font-size: 0.8rem; margin-top: 8px; font-weight: 600; color: var(--accent);"><i class="fa-solid fa-arrow-up-right-from-square"></i> Ver en USGS</a>` : ''}
                </div>
            `;
            
            const marker = L.circleMarker([lat, lon], {
                radius: radiusSize,
                fillColor: markerColor,
                color: markerColor,
                weight: 1.5,
                opacity: 0.9,
                fillOpacity: 0.5,
                dashArray: '3, 3' // Dashed outline for USGS sismos
            })
            .bindPopup(popupHTML);
            
            marker.sismoId = s.id;
            usgsSismosLayer.addLayer(marker);
            usgsMarkers.push(marker);
        });
    }
    
    function refreshSidebarList() {
        const sismos = (activeTab === 'locales') ? localSismos : usgsSismos;
        const listContainer = document.getElementById('recent-sismos-list');
        const badge = document.getElementById('sismos-badge');
        
        if (!listContainer) return;
        
        if (badge) badge.textContent = sismos.length;
        
        if (sismos.length === 0) {
            listContainer.innerHTML = `<div class="seismo-placeholder-text" style="color: #6b7280; padding: 20px; text-align: center;">No se registraron sismos recientes.</div>`;
            return;
        }
        
        listContainer.innerHTML = '';
        
        // Render top 25 recent events in list for performance
        sismos.slice(0, 25).forEach(s => {
            let magClass = 'mag-low';
            if (s.magnitud >= 3.0 && s.magnitud < 5.0) magClass = 'mag-med';
            else if (s.magnitud >= 5.0) magClass = 'mag-high';
            
            const item = document.createElement('div');
            item.className = 'sismo-item';
            item.dataset.id = s.id;
            item.dataset.lat = s.latitud;
            item.dataset.lon = s.longitud;
            
            item.innerHTML = `
                <div class="sismo-item-top">
                    <span class="sismo-item-mag ${magClass}">Mw ${s.magnitud.toFixed(1)}</span>
                    <span class="sismo-item-depth">${s.profundidad} km</span>
                </div>
                <div class="sismo-item-loc">${s.descripcion}</div>
                <div class="sismo-item-time">
                    <span>${s.fecha_utc}</span>
                    <span>${s.hora_utc} UTC</span>
                </div>
            `;
            
            // List item click pans and opens popup
            item.addEventListener('click', function() {
                const lat = parseFloat(this.dataset.lat);
                const lon = parseFloat(this.dataset.lon);
                const id = parseInt(this.dataset.id);
                
                // Pan map
                map.setView([lat, lon], activeTab === 'locales' ? 9 : 7);
                
                // Active layer if disabled
                const currentLayer = (activeTab === 'locales') ? localSismosLayer : usgsSismosLayer;
                if (!map.hasLayer(currentLayer)) {
                    map.addLayer(currentLayer);
                }
                
                // Find matching marker and open popup
                const markers = (activeTab === 'locales') ? localMarkers : usgsMarkers;
                const marker = markers.find(m => m.sismoId === id);
                if (marker) {
                    setTimeout(() => {
                        marker.openPopup();
                    }, 200);
                }
            });
            
            listContainer.appendChild(item);
        });
    }
    
    // Sidebar Tabs Logic
    const tabLocales = document.getElementById('tab-locales');
    const tabUsgs = document.getElementById('tab-usgs');
    
    if (tabLocales && tabUsgs) {
        tabLocales.addEventListener('click', function() {
            activeTab = 'locales';
            tabLocales.classList.add('active');
            tabUsgs.classList.remove('active');
            refreshSidebarList();
        });
        
        tabUsgs.addEventListener('click', function() {
            activeTab = 'usgs';
            tabUsgs.classList.add('active');
            tabLocales.classList.remove('active');
            refreshSidebarList();
        });
    }
    
    function updateStats(sismos) {
        const totalEl = document.getElementById('stat-total-sismos');
        const maxEl = document.getElementById('stat-max-mag');
        const updateEl = document.getElementById('stat-last-update');
        
        if (totalEl) totalEl.textContent = sismos.length;
        
        if (sismos.length > 0) {
            const maxMag = Math.max(...sismos.map(s => s.magnitud));
            if (maxEl) maxEl.textContent = maxMag.toFixed(1);
        } else {
            if (maxEl) maxEl.textContent = "0.0";
        }
        
        if (updateEl) {
            updateEl.textContent = new Date().toLocaleTimeString();
        }
    }
    
    // Load data initially
    loadSismosData();
    
    // Make loadSismosData globally accessible to allow trigger from sync button
    window.refreshMapData = loadSismosData;
});

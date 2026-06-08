document.addEventListener('DOMContentLoaded', function() {
    let allSismos = [];
    let filteredSismos = [];
    let currentPage = 1;
    const pageSize = 15;
    let currentSource = 'locales'; // 'locales' or 'usgs'
    
    let timelineChart = null;
    let magnitudeChart = null;
    
    // DOM Elements
    const filterForm = document.getElementById('filter-form');
    const minMagSlider = document.getElementById('filter-min-mag');
    const minMagVal = document.getElementById('mag-val');
    const countrySelect = document.getElementById('filter-pais');
    const minDepthInput = document.getElementById('filter-min-depth');
    const maxDepthInput = document.getElementById('filter-max-depth');
    const startDateInput = document.getElementById('filter-start-date');
    const endDateInput = document.getElementById('filter-end-date');
    const searchInput = document.getElementById('filter-search');
    const btnReset = document.getElementById('btn-reset-filters');
    const btnExport = document.getElementById('btn-export-csv');
    
    const tableBody = document.getElementById('historical-table-body');
    const paginationInfo = document.getElementById('pagination-info');
    const btnPrev = document.getElementById('btn-prev');
    const btnNext = document.getElementById('btn-next');
    
    // Helper to format date as YYYY-MM-DD in local time
    function formatDateLocal(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    // Set default date range: today and 10 days ago
    const today = new Date();
    const tenDaysAgo = new Date();
    tenDaysAgo.setDate(today.getDate() - 10);
    
    const defaultEndDate = formatDateLocal(today);
    const defaultStartDate = formatDateLocal(tenDaysAgo);
    
    if (startDateInput) startDateInput.value = defaultStartDate;
    if (endDateInput) endDateInput.value = defaultEndDate;

    // Helper to update slider label
    function updateMagLabel(val) {
        if (minMagVal) {
            const num = parseFloat(val);
            if (num <= 1.0) {
                minMagVal.textContent = "Cualquiera";
            } else {
                minMagVal.textContent = num.toFixed(1);
            }
        }
    }

    // Initialize magnitude slider label
    if (minMagSlider) {
        updateMagLabel(minMagSlider.value);
        minMagSlider.addEventListener('input', function() {
            updateMagLabel(this.value);
        });
    }
    
    // Fetch all data initially
    function fetchData() {
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="loading-placeholder" style="text-align: center; height: 120px; color: var(--text-secondary); line-height: 120px;">
                        <i class="fa-solid fa-spinner fa-spin" style="margin-right: 8px;"></i> Cargando eventos sísmicos...
                    </td>
                </tr>
            `;
        }
        
        const endpoint = (currentSource === 'locales') ? '/api/sismos?limit=1000' : '/api/sismos/usgs?limit=1000';
        
        fetch(endpoint)
            .then(res => res.json())
            .then(data => {
                allSismos = data;
                applyFilters();
            })
            .catch(err => {
                console.error("Error fetching historical data:", err);
                if (tableBody) {
                    tableBody.innerHTML = `
                        <tr>
                            <td colspan="7" style="text-align: center; color: var(--danger); padding: 30px;">
                                <i class="fa-solid fa-triangle-exclamation"></i> Error al cargar datos del servidor.
                            </td>
                        </tr>
                    `;
                }
            });
    }
    
    // Apply filters client-side for instantaneous feedback without page reload
    function applyFilters() {
        const minMag = minMagSlider ? parseFloat(minMagSlider.value) : 1.0;
        const country = countrySelect ? countrySelect.value : '';
        const minDepth = minDepthInput && minDepthInput.value ? parseInt(minDepthInput.value) : null;
        const maxDepth = maxDepthInput && maxDepthInput.value ? parseInt(maxDepthInput.value) : null;
        const startDate = startDateInput ? startDateInput.value : '';
        const endDate = endDateInput ? endDateInput.value : '';
        const searchQuery = searchInput ? searchInput.value.toLowerCase().trim() : '';
        
        filteredSismos = allSismos.filter(s => {
            // Country Filter
            if (country) {
                if (country === 'Otros') {
                    const centralAmericanCountries = ['Nicaragua', 'El Salvador', 'Guatemala', 'Honduras', 'Costa Rica', 'Panamá', 'Panama'];
                    if (centralAmericanCountries.includes(s.pais)) return false;
                } else if (s.pais !== country) {
                    return false;
                }
            }

            // Magnitude Filter (if slider is at 1.0, ignore magnitude filter to allow all sismos)
            if (minMag > 1.0 && s.magnitud < minMag) return false;
            
            // Depth Filters
            if (minDepth !== null && s.profundidad < minDepth) return false;
            if (maxDepth !== null && s.profundidad > maxDepth) return false;
            
            // Start Date Filter
            if (startDate && s.fecha_utc < startDate) return false;
            
            // End Date Filter
            if (endDate && s.fecha_utc > endDate) return false;
            
            // Text Search Filter (Location)
            if (searchQuery && !s.descripcion.toLowerCase().includes(searchQuery)) return false;
            
            return true;
        });
        
        // Sort by Date & Time descending (newest first)
        filteredSismos.sort((a, b) => {
            const dtA = new Date(`${a.fecha_utc}T${a.hora_utc}Z`);
            const dtB = new Date(`${b.fecha_utc}T${b.hora_utc}Z`);
            return dtB - dtA;
        });
        
        currentPage = 1;
        renderTable();
        updateCharts();
    }
    
    // Render the paginated table rows
    function renderTable() {
        if (!tableBody) return;
        
        if (filteredSismos.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 30px;">
                        No se encontraron sismos con los filtros aplicados.
                    </td>
                </tr>
            `;
            if (paginationInfo) paginationInfo.textContent = "Mostrando 0-0 de 0 eventos";
            if (btnPrev) btnPrev.disabled = true;
            if (btnNext) btnNext.disabled = true;
            return;
        }
        
        const totalItems = filteredSismos.length;
        const totalPages = Math.ceil(totalItems / pageSize);
        
        // Page boundary check
        if (currentPage < 1) currentPage = 1;
        if (currentPage > totalPages) currentPage = totalPages;
        
        const startIndex = (currentPage - 1) * pageSize;
        const endIndex = Math.min(startIndex + pageSize, totalItems);
        const paginatedData = filteredSismos.slice(startIndex, endIndex);
        
        tableBody.innerHTML = '';
        paginatedData.forEach(s => {
            let magClass = 'mag-low';
            if (s.magnitud >= 3.0 && s.magnitud < 5.0) magClass = 'mag-med';
            else if (s.magnitud >= 5.0) magClass = 'mag-high';
            
            const latVal = s.latitud ? s.latitud.toFixed(3) : '0.000';
            const lonVal = s.longitud ? s.longitud.toFixed(3) : '0.000';
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${s.fecha_utc}</strong></td>
                <td>${s.hora_utc}</td>
                <td><span class="mag-cell ${magClass}">${s.magnitud.toFixed(1)}</span></td>
                <td class="depth-cell">${s.profundidad} km</td>
                <td>${s.descripcion}</td>
                <td><span class="country-cell">${s.pais}</span></td>
                <td style="font-family: monospace; font-size: 0.9em; color: var(--text-secondary);">${latVal}, ${lonVal}</td>
            `;
            tableBody.appendChild(tr);
        });
        
        // Update pagination details
        if (paginationInfo) {
            paginationInfo.textContent = `Mostrando ${startIndex + 1}-${endIndex} de ${totalItems} eventos`;
        }
        
        if (btnPrev) btnPrev.disabled = currentPage === 1;
        if (btnNext) btnNext.disabled = currentPage === totalPages;
    }
    
    // Pagination event listeners
    if (btnPrev) {
        btnPrev.addEventListener('click', function() {
            if (currentPage > 1) {
                currentPage--;
                renderTable();
            }
        });
    }
    
    if (btnNext) {
        btnNext.addEventListener('click', function() {
            const totalPages = Math.ceil(filteredSismos.length / pageSize);
            if (currentPage < totalPages) {
                currentPage++;
                renderTable();
            }
        });
    }
    
    // Chart Generation with Chart.js
    function updateCharts() {
        renderTimelineChart();
        renderCountryChart();
    }
    
    function renderTimelineChart() {
        const ctx = document.getElementById('chart-timeline');
        if (!ctx) return;
        
        // Aggregate daily counts from filtered data
        const dailyCounts = {};
        filteredSismos.forEach(s => {
            const d = s.fecha_utc;
            dailyCounts[d] = (dailyCounts[d] || 0) + 1;
        });
        
        // Sort and select last 20 active days of data for visibility
        const sortedDates = Object.keys(dailyCounts).sort();
        const displayDates = sortedDates.slice(-20);
        const counts = displayDates.map(d => dailyCounts[d]);
        
        if (timelineChart) {
            timelineChart.destroy();
        }
        
        timelineChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: displayDates,
                datasets: [{
                    label: 'Sismos por Día',
                    data: counts,
                    borderColor: '#ff5722',
                    backgroundColor: 'rgba(255, 87, 34, 0.08)',
                    fill: true,
                    tension: 0.35,
                    borderWidth: 2,
                    pointBackgroundColor: '#ff5722',
                    pointRadius: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#111218',
                        titleColor: '#fff',
                        bodyColor: '#ccc',
                        borderColor: 'rgba(255,255,255,0.08)',
                        borderWidth: 1
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.03)' },
                        ticks: { color: '#9ca3af', font: { family: 'Outfit', size: 10 } }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.03)' },
                        ticks: { 
                            color: '#9ca3af', 
                            font: { family: 'Outfit', size: 10 },
                            stepSize: 1
                        },
                        beginAtZero: true
                    }
                }
            }
        });
    }
    
    function renderCountryChart() {
        const ctx = document.getElementById('chart-countries');
        if (!ctx) return;
        
        // Aggregate country counts from filtered data
        const countryCounts = {};
        filteredSismos.forEach(s => {
            const country = s.pais || 'Otros';
            countryCounts[country] = (countryCounts[country] || 0) + 1;
        });
        
        const labels = Object.keys(countryCounts);
        const data = Object.values(countryCounts);
        
        // Dynamic color palette matching the maps/design system
        const colors = {
            'Nicaragua': '#2196f3',
            'El Salvador': '#3f51b5',
            'Costa Rica': '#f44336',
            'Guatemala': '#009688',
            'Honduras': '#03a9f4',
            'Panamá': '#9c27b0',
            'Otros': '#9e9e9e'
        };
        
        const backgroundColors = labels.map(c => colors[c] || '#607d8b');
        
        if (magnitudeChart) {
            magnitudeChart.destroy();
        }
        
        magnitudeChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: backgroundColors.map(color => color + 'b3'), // 70% opacity
                    borderColor: backgroundColors,
                    borderWidth: 1.5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: '#9ca3af',
                            font: { family: 'Outfit', size: 10 },
                            padding: 10,
                            boxWidth: 10
                        }
                    },
                    tooltip: {
                        backgroundColor: '#111218',
                        titleColor: '#fff',
                        bodyColor: '#ccc',
                        borderColor: 'rgba(255,255,255,0.08)',
                        borderWidth: 1
                    }
                },
                cutout: '65%'
            }
        });
    }
    
    // CSV Exporter
    if (btnExport) {
        btnExport.addEventListener('click', function() {
            if (filteredSismos.length === 0) {
                if (window.showToast) window.showToast('No hay datos para exportar.', 'error');
                return;
            }
            
            let csvContent = "\uFEFF"; // UTF-8 BOM
            csvContent += "Fecha (UTC),Hora (UTC),Magnitud,Profundidad (km),Localizacion,Pais,Latitud,Longitud\r\n";
            
            filteredSismos.forEach(s => {
                const cleanLoc = `"${s.descripcion.replace(/"/g, '""')}"`;
                const row = `${s.fecha_utc},${s.hora_utc},${s.magnitud.toFixed(1)},${s.profundidad},${cleanLoc},${s.pais},${s.latitud},${s.longitud}`;
                csvContent += row + "\r\n";
            });
            
            const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.setAttribute("href", url);
            link.setAttribute("download", `sismos_geocentro_${new Date().toISOString().split('T')[0]}.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            if (window.showToast) window.showToast('Datos exportados exitosamente en CSV.', 'success');
        });
    }
    
    // Form Submission (Apply Filters)
    if (filterForm) {
        filterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            applyFilters();
        });
    }
    
    // Reset Filters Button
    if (btnReset) {
        btnReset.addEventListener('click', function(e) {
            e.preventDefault();
            if (countrySelect) countrySelect.value = '';
            if (minMagSlider) {
                minMagSlider.value = 1.0;
                updateMagLabel(1.0);
            }
            if (minDepthInput) minDepthInput.value = '';
            if (maxDepthInput) maxDepthInput.value = '';
            if (startDateInput) startDateInput.value = defaultStartDate;
            if (endDateInput) endDateInput.value = defaultEndDate;
            if (searchInput) searchInput.value = '';
            applyFilters();
        });
    }
    
    // Historical Table Tabs Logic
    const tabTableLocales = document.getElementById('table-tab-locales');
    const tabTableUsgs = document.getElementById('table-tab-usgs');
    
    if (tabTableLocales && tabTableUsgs) {
        tabTableLocales.addEventListener('click', function() {
            if (currentSource !== 'locales') {
                currentSource = 'locales';
                tabTableLocales.classList.add('active');
                tabTableUsgs.classList.remove('active');
                fetchData();
            }
        });
        
        tabTableUsgs.addEventListener('click', function() {
            if (currentSource !== 'usgs') {
                currentSource = 'usgs';
                tabTableUsgs.classList.add('active');
                tabTableLocales.classList.remove('active');
                fetchData();
            }
        });
    }
    
    // Setup sync reload callback
    window.refreshHistoricalData = function() {
        fetchData();
    };
    
    // Parse URL query parameters to filter country on load
    const urlParams = new URLSearchParams(window.location.search);
    const urlPais = urlParams.get('pais');
    if (urlPais && countrySelect) {
        // If the country is "Otros", we also switch tab to USGS (Global)
        if (urlPais === 'Otros') {
            currentSource = 'usgs';
            const tabTableLocales = document.getElementById('table-tab-locales');
            const tabTableUsgs = document.getElementById('table-tab-usgs');
            if (tabTableLocales && tabTableUsgs) {
                tabTableUsgs.classList.add('active');
                tabTableLocales.classList.remove('active');
            }
        }
        countrySelect.value = urlPais;
    }
    
    // Trigger initial load
    fetchData();
});

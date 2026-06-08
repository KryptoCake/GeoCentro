document.addEventListener('DOMContentLoaded', function() {
    // 1. Windy Layer Selector Logic
    const windyTabs = document.querySelectorAll('.windy-tab-btn');
    const windyIframe = document.getElementById('windy-iframe');
    const baseIframeUrl = "https://embed.windy.com/embed2.html?lat=12.5&lon=-86.0&zoom=6&level=surface&menu=&message=true&marker=&calendar=&pressure=&type=map&location=coordinates&metricWind=default&metricTemp=default&radarRange=-1";
    
    if (windyTabs && windyIframe) {
        windyTabs.forEach(btn => {
            btn.addEventListener('click', function() {
                // Remove active class from all tabs
                windyTabs.forEach(t => t.classList.remove('active'));
                
                // Add active class to clicked tab
                this.classList.add('active');
                
                // Update iframe src with overlay
                const overlay = this.getAttribute('data-overlay');
                windyIframe.src = `${baseIframeUrl}&overlay=${overlay}`;
            });
        });
    }

    // 2. Open-Meteo Capital Cities weather API
    const capitals = [
        { name: "Managua", country: "Nicaragua", lat: 12.1328, lon: -86.2504 },
        { name: "San José", country: "Costa Rica", lat: 9.9281, lon: -84.0907 },
        { name: "San Salvador", country: "El Salvador", lat: 13.6929, lon: -89.2182 },
        { name: "Tegucigalpa", country: "Honduras", lat: 14.0818, lon: -87.2068 },
        { name: "Ciudad de Guatemala", country: "Guatemala", lat: 14.6349, lon: -90.5069 },
        { name: "Ciudad de Panamá", country: "Panamá", lat: 8.9824, lon: -79.5199 }
    ];

    const weatherListContainer = document.getElementById('capitals-weather-list');
    
    // Mapping weathercode to icon and human-readable description
    function getWeatherDescription(code) {
        const codes = {
            0: { desc: "Despejado", icon: "fa-sun", color: "#ffb300" },
            1: { desc: "Mayormente despejado", icon: "fa-cloud-sun", color: "#ffb300" },
            2: { desc: "Parcialmente nublado", icon: "fa-cloud-sun", color: "#9ca3af" },
            3: { desc: "Nublado", icon: "fa-cloud", color: "#9ca3af" },
            45: { desc: "Neblina", icon: "fa-smog", color: "#6b7280" },
            48: { desc: "Neblina deposición", icon: "fa-smog", color: "#6b7280" },
            51: { desc: "Llovizna ligera", icon: "fa-cloud-rain", color: "#2196f3" },
            53: { desc: "Llovizna moderada", icon: "fa-cloud-rain", color: "#2196f3" },
            55: { desc: "Llovizna densa", icon: "fa-cloud-rain", color: "#2196f3" },
            61: { desc: "Lluvia ligera", icon: "fa-cloud-showers-heavy", color: "#2196f3" },
            63: { desc: "Lluvia moderada", icon: "fa-cloud-showers-heavy", color: "#1976d2" },
            65: { desc: "Lluvia fuerte", icon: "fa-cloud-showers-water", color: "#0d47a1" },
            80: { desc: "Lloviznas dispersas", icon: "fa-cloud-sun-rain", color: "#2196f3" },
            81: { desc: "Lluvias dispersas", icon: "fa-cloud-showers-heavy", color: "#2196f3" },
            82: { desc: "Chubascos fuertes", icon: "fa-cloud-showers-water", color: "#0d47a1" },
            95: { desc: "Tormenta eléctrica", icon: "fa-cloud-bolt", color: "#f44336" },
            96: { desc: "Tormenta con granizo ligero", icon: "fa-cloud-bolt", color: "#f44336" },
            99: { desc: "Tormenta con granizo fuerte", icon: "fa-cloud-bolt", color: "#f44336" }
        };
        return codes[code] || { desc: "Desconocido", icon: "fa-cloud-sun", color: "#9ca3af" };
    }

    function fetchCapitalsWeather() {
        if (!weatherListContainer) return;
        
        const promises = capitals.map(city => {
            const url = `https://api.open-meteo.com/v1/forecast?latitude=${city.lat}&longitude=${city.lon}&current_weather=true`;
            return fetch(url)
                .then(res => res.json())
                .then(data => {
                    const current = data.current_weather;
                    return {
                        ...city,
                        temp: current.temperature,
                        windspeed: current.windspeed,
                        weathercode: current.weathercode
                    };
                })
                .catch(err => {
                    console.error(`Error loading weather for ${city.name}:`, err);
                    return {
                        ...city,
                        temp: null,
                        windspeed: null,
                        weathercode: 3,
                        error: true
                    };
                });
        });

        Promise.all(promises)
            .then(results => {
                // Clear loading
                weatherListContainer.innerHTML = '';
                
                // Calculate Extremes
                calculateAndRenderExtremes(results);

                // Render Cities
                results.forEach(city => {
                    if (city.error) {
                        const errItem = document.createElement('div');
                        errItem.className = 'sismo-item';
                        errItem.style.cursor = 'default';
                        errItem.innerHTML = `
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-weight:700;">${city.name}</span>
                                <span style="color:var(--danger); font-size:0.8rem;"><i class="fa-solid fa-triangle-exclamation"></i> Error</span>
                            </div>
                        `;
                        weatherListContainer.appendChild(errItem);
                        return;
                    }

                    const weatherInfo = getWeatherDescription(city.weathercode);
                    const item = document.createElement('div');
                    item.className = 'sismo-item';
                    item.style.cursor = 'default';
                    item.style.background = 'rgba(255, 255, 255, 0.02)';
                    item.style.border = '1px solid var(--border-color)';
                    
                    item.innerHTML = `
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 6px;">
                            <span style="font-weight:700; font-size: 0.95rem;">${city.name}</span>
                            <span style="font-weight:800; font-size: 1.1rem; color: var(--text-primary);">${city.temp.toFixed(1)}°C</span>
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:center; font-size: 0.8rem; color: var(--text-secondary);">
                            <span style="display:flex; align-items:center; gap:6px;">
                                <i class="fa-solid ${weatherInfo.icon}" style="color:${weatherInfo.color};"></i> ${weatherInfo.desc}
                            </span>
                            <span style="display:flex; align-items:center; gap:8px;">
                                <span><i class="fa-solid fa-wind" style="color: var(--text-muted);"></i> ${city.windspeed.toFixed(0)} km/h</span>
                            </span>
                        </div>
                    `;
                    weatherListContainer.appendChild(item);
                });
            });
    }

    // Calculate Weather Extremes dynamically
    function calculateAndRenderExtremes(cities) {
        const validCities = cities.filter(c => !c.error && c.temp !== null);
        if (validCities.length === 0) return;

        // Find Hottest
        let hottest = validCities[0];
        // Find Coldest
        let coldest = validCities[0];
        // Find Windiest
        let windiest = validCities[0];

        validCities.forEach(city => {
            if (city.temp > hottest.temp) hottest = city;
            if (city.temp < coldest.temp) coldest = city;
            if (city.windspeed > windiest.windspeed) windiest = city;
        });

        // Set DOM text
        const hEl = document.getElementById('extreme-hottest');
        const cEl = document.getElementById('extreme-coldest');
        const wEl = document.getElementById('extreme-windiest');

        if (hEl) hEl.innerHTML = `${hottest.name} <span style="color: var(--danger); font-weight:800;">${hottest.temp.toFixed(1)}°C</span>`;
        if (cEl) cEl.innerHTML = `${coldest.name} <span style="color: var(--info); font-weight:800;">${coldest.temp.toFixed(1)}°C</span>`;
        if (wEl) wEl.innerHTML = `${windiest.name} <span style="color: var(--warning); font-weight:800;">${windiest.windspeed.toFixed(0)} km/h</span>`;
    }

    // 3. Load Weather Alerts Feed (NHC NOAA)
    const alertsContainer = document.getElementById('weather-alerts-feed');
    
    function loadWeatherAlerts() {
        if (!alertsContainer) return;
        
        fetch('/api/news?categoria=clima&limit=6')
            .then(res => res.json())
            .then(data => {
                if (data.length === 0) {
                    alertsContainer.innerHTML = `
                        <div class="seismo-placeholder-text" style="color: var(--text-secondary); text-align: center; padding: 24px; font-weight: 500;">
                            <i class="fa-solid fa-cloud-sun" style="color: var(--success); font-size: 1.5rem; display: block; margin-bottom: 8px;"></i>
                            No hay alertas tropicales activas en este momento.
                        </div>
                    `;
                    return;
                }
                
                alertsContainer.innerHTML = '';
                data.forEach(item => {
                    const card = document.createElement('div');
                    card.className = 'news-card-item';
                    
                    // Style alert depending on severity
                    let borderStyle = '';
                    let iconStyle = '';
                    if (item.titulo.toLowerCase().includes('warning') || item.titulo.toLowerCase().includes('alerta') || item.titulo.toLowerCase().includes('huracán') || item.titulo.toLowerCase().includes('hurricane')) {
                        borderStyle = 'border-left: 4px solid var(--danger);';
                        iconStyle = '<i class="fa-solid fa-triangle-exclamation" style="color: var(--danger); margin-right: 6px;"></i>';
                    } else if (item.titulo.toLowerCase().includes('watch') || item.titulo.toLowerCase().includes('vigilancia') || item.titulo.toLowerCase().includes('storm') || item.titulo.toLowerCase().includes('tormenta')) {
                        borderStyle = 'border-left: 4px solid var(--warning);';
                        iconStyle = '<i class="fa-solid fa-circle-exclamation" style="color: var(--warning); margin-right: 6px;"></i>';
                    } else {
                        borderStyle = 'border-left: 4px solid var(--info);';
                        iconStyle = '<i class="fa-solid fa-circle-info" style="color: var(--info); margin-right: 6px;"></i>';
                    }

                    card.setAttribute('style', borderStyle);
                    
                    let alertUrl = item.url ? item.url.trim() : 'https://www.nhc.noaa.gov/';
                    if (alertUrl === '#' || alertUrl.startsWith('#')) {
                        alertUrl = 'https://www.nhc.noaa.gov/';
                    } else if (!alertUrl.startsWith('http')) {
                        if (alertUrl.startsWith('/')) {
                            alertUrl = 'https://www.nhc.noaa.gov' + alertUrl;
                        } else {
                            alertUrl = 'https://www.nhc.noaa.gov/' + alertUrl;
                        }
                    }

                    const countryUrl = `/historical?pais=${encodeURIComponent(item.pais)}`;
                    
                    card.innerHTML = `
                        <div class="news-item-header">
                            <h4 class="news-item-title">${iconStyle}${item.titulo}</h4>
                            <span class="news-item-date">${item.fecha}</span>
                        </div>
                        <p class="news-item-desc" style="font-family: monospace; font-size: 0.8rem; background: rgba(0,0,0,0.15); padding: 8px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.02); margin-top: 6px; white-space: pre-line; line-height: 1.4;">${item.resumen}</p>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
                            <a href="${countryUrl}" class="news-item-country-badge" style="text-decoration: none; cursor: pointer;">${item.pais}</a>
                            <a href="${alertUrl}" target="_blank" style="font-size: 0.75rem; font-weight: 700; color: var(--accent); display: inline-flex; align-items: center; gap: 4px;"><i class="fa-solid fa-arrow-up-right-from-square"></i> Ver Fuente</a>
                        </div>
                    `;
                    alertsContainer.appendChild(card);
                });
            })
            .catch(err => {
                console.error("Error loading weather alerts:", err);
                alertsContainer.innerHTML = '<div class="error-text" style="color: #f44336; padding: 20px; text-align: center;"><i class="fa-solid fa-circle-exclamation"></i> Error al cargar boletines.</div>';
            });
    }

    // Initial load calls
    fetchCapitalsWeather();
    loadWeatherAlerts();
    
    // Refresh weather alerts if global sync trigger runs
    const origRefreshHistoricalData = window.refreshHistoricalData;
    window.refreshHistoricalData = function() {
        if (typeof origRefreshHistoricalData === 'function') origRefreshHistoricalData();
        fetchCapitalsWeather();
        loadWeatherAlerts();
    };
    
    const origRefreshMapData = window.refreshMapData;
    window.refreshMapData = function() {
        if (typeof origRefreshMapData === 'function') origRefreshMapData();
        fetchCapitalsWeather();
        loadWeatherAlerts();
    };
});

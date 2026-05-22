document.addEventListener('DOMContentLoaded', function() {
    
    // ==========================================
    // 1. SEISMOGRAM GENERATOR
    // ==========================================
    const seismoForm = document.getElementById('seismogram-form');
    const seismoDate = document.getElementById('seismo-date');
    const seismoPeriod = document.getElementById('seismo-period');
    const seismoStation = document.getElementById('seismo-station');
    
    const seismoImg = document.getElementById('seismogram-img');
    const seismoPlaceholder = document.getElementById('seismo-placeholder');
    const seismoInfoBox = document.getElementById('seismo-info');
    const seismoStationName = document.getElementById('seismo-station-name');
    const seismoTimeInfo = document.getElementById('seismo-time-info');
    
    // Set default date to today local (YYYY-MM-DD format)
    if (seismoDate) {
        const today = new Date();
        const yyyy = today.getFullYear();
        const mm = String(today.getMonth() + 1).padStart(2, '0');
        const dd = String(today.getDate()).padStart(2, '0');
        seismoDate.value = `${yyyy}-${mm}-${dd}`;
    }
    
    // Set default period based on current local hour (hours >= 12 -> 12, else 00)
    if (seismoPeriod) {
        const today = new Date();
        const hours = today.getHours();
        if (hours >= 12) {
            seismoPeriod.value = "12";
        } else {
            seismoPeriod.value = "00";
        }
    }
    
    if (seismoForm) {
        seismoForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const rawDate = seismoDate.value; // YYYY-MM-DD
            if (!rawDate) {
                if (window.showToast) window.showToast('Por favor, selecciona una fecha.', 'error');
                return;
            }
            
            // Format to YYYYMMDD
            const cleanDate = rawDate.replace(/-/g, '');
            const period = seismoPeriod.value;
            const station = seismoStation.value;
            const stationText = seismoStation.options[seismoStation.selectedIndex].text;
            
            // Show loading state
            if (seismoPlaceholder) {
                seismoPlaceholder.style.display = 'flex';
                seismoPlaceholder.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin fa-2x" style="color: var(--accent);"></i><p style="margin-top: 10px;">Obteniendo sismograma de INETER...</p>';
            }
            if (seismoImg) seismoImg.style.display = 'none';
            if (seismoInfoBox) seismoInfoBox.style.display = 'none';
            
            // Build api endpoint
            const imgSrc = `/api/seismogram?date=${cleanDate}&hour=${period}&station=${station}`;
            
            const testImg = new Image();
            testImg.onload = function() {
                if (seismoPlaceholder) seismoPlaceholder.style.display = 'none';
                if (seismoImg) {
                    seismoImg.src = imgSrc;
                    seismoImg.style.display = 'block';
                }
                if (seismoStationName) seismoStationName.textContent = stationText;
                
                const periodLabel = period === "12" ? "12:00 PM - 11:59 PM (12)" : "12:00 AM - 11:59 AM (00)";
                if (seismoTimeInfo) seismoTimeInfo.textContent = `Fecha: ${rawDate} | Período de corte: ${periodLabel}`;
                if (seismoInfoBox) seismoInfoBox.style.display = 'block';
            };
            
            testImg.onerror = function() {
                if (seismoPlaceholder) {
                    seismoPlaceholder.style.display = 'flex';
                    seismoPlaceholder.innerHTML = `
                        <div style="text-align: center; color: var(--text-secondary); padding: 20px;">
                            <i class="fa-solid fa-image-broken fa-3x" style="color: var(--danger); margin-bottom: 12px;"></i>
                            <h4 style="margin-bottom: 6px; color: var(--text-primary);">Sismograma no disponible</h4>
                            <p style="font-size: 0.8rem; line-height: 1.4; max-width: 340px; margin: 0 auto; color: var(--text-secondary);">
                                La estación seleccionada no registra datos para esa hora, o el archivo ha sido depurado del servidor de INETER (archivos de más de 48 horas).
                            </p>
                        </div>
                    `;
                }
            };
            
            testImg.src = imgSrc;
        });
    }
    
    // ==========================================
    // 2. WEBCAMS AUTO-REFRESH & MANUAL REFRESH
    // ==========================================
    const autoRefreshToggle = document.getElementById('auto-refresh-webcams');
    let refreshIntervalId = null;
    
    // Function to refresh a specific webcam
    function refreshWebcam(card) {
        const refreshBtn = card.querySelector('.btn-refresh-cam');
        if (!refreshBtn) return;
        
        const camCode = refreshBtn.getAttribute('data-cam');
        const img = card.querySelector('.webcam-feed');
        const stamp = card.querySelector('.webcam-timestamp');
        const icon = refreshBtn.querySelector('i');
        
        if (icon) icon.classList.add('fa-spin');
        
        if (img) {
            const tempImg = new Image();
            const newSrc = `/api/webcam/proxy?volcan=${camCode}&t=${new Date().getTime()}`;
            
            tempImg.onload = function() {
                img.src = newSrc;
                if (stamp) {
                    stamp.textContent = `Actualizado: ${new Date().toLocaleTimeString()}`;
                }
                if (icon) icon.classList.remove('fa-spin');
            };
            
            tempImg.onerror = function() {
                if (icon) icon.classList.remove('fa-spin');
            };
            
            tempImg.src = newSrc;
        }
    }
    
    // Function to refresh all webcams
    function refreshAllWebcams() {
        const cards = document.querySelectorAll('.webcam-card-item');
        cards.forEach(card => {
            refreshWebcam(card);
        });
    }
    
    // Event listener for individual refreshes
    document.addEventListener('click', function(e) {
        const refreshBtn = e.target.closest('.btn-refresh-cam');
        if (refreshBtn) {
            e.preventDefault();
            const card = refreshBtn.closest('.webcam-card-item');
            if (card) {
                const camCode = refreshBtn.getAttribute('data-cam');
                refreshWebcam(card);
                if (window.showToast) {
                    const camName = card.querySelector('.webcam-title')?.textContent || camCode;
                    window.showToast(`Cámara de ${camName} actualizada.`, 'info');
                }
            }
        }
    });
    
    // Auto refresh trigger (30 seconds interval as per HTML label)
    if (autoRefreshToggle) {
        // Set initial interval if checked by default
        if (autoRefreshToggle.checked) {
            refreshIntervalId = setInterval(refreshAllWebcams, 30000);
        }
        
        autoRefreshToggle.addEventListener('change', function() {
            if (this.checked) {
                if (window.showToast) window.showToast('Auto-recarga activada (cada 30s).', 'success');
                refreshAllWebcams();
                refreshIntervalId = setInterval(refreshAllWebcams, 30000);
            } else {
                if (window.showToast) window.showToast('Auto-recarga desactivada.', 'info');
                if (refreshIntervalId) {
                    clearInterval(refreshIntervalId);
                    refreshIntervalId = null;
                }
            }
        });
    }
    
    // Cleanup interval on page navigate
    window.addEventListener('beforeunload', function() {
        if (refreshIntervalId) {
            clearInterval(refreshIntervalId);
        }
    });
    
    // ==========================================
    // 3. SEISMIC RISK CALCULATOR
    // ==========================================
    const riskForm = document.getElementById('risk-calc-form');
    const btnGetLocation = document.getElementById('btn-get-location');
    
    // Geolocation Support
    if (btnGetLocation) {
        btnGetLocation.addEventListener('click', function() {
            if (navigator.geolocation) {
                btnGetLocation.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Obteniendo...';
                btnGetLocation.disabled = true;
                
                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        const latInput = document.getElementById('calc-lat');
                        const lonInput = document.getElementById('calc-lon');
                        if (latInput) latInput.value = position.coords.latitude.toFixed(4);
                        if (lonInput) lonInput.value = position.coords.longitude.toFixed(4);
                        
                        btnGetLocation.innerHTML = '<i class="fa-solid fa-location-crosshairs"></i> Obtener Ubicación';
                        btnGetLocation.disabled = false;
                        if (window.showToast) window.showToast('Coordenadas obtenidas con éxito.', 'success');
                    },
                    function(error) {
                        btnGetLocation.innerHTML = '<i class="fa-solid fa-location-crosshairs"></i> Obtener Ubicación';
                        btnGetLocation.disabled = false;
                        let msg = 'No se pudo obtener la ubicación.';
                        if (error.code === error.PERMISSION_DENIED) {
                            msg = 'Permiso denegado para acceder a la ubicación.';
                        }
                        if (window.showToast) window.showToast(msg, 'error');
                    },
                    { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }
                );
            } else {
                if (window.showToast) window.showToast('Geolocalización no soportada por el navegador.', 'error');
            }
        });
    }
    
    // Calculation Logic on Form Submit
    if (riskForm) {
        riskForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const latVal = document.getElementById('calc-lat')?.value;
            const lonVal = document.getElementById('calc-lon')?.value;
            
            if (!latVal || !lonVal) {
                if (window.showToast) window.showToast('Por favor ingresa latitud y longitud válidas.', 'error');
                return;
            }
            
            const lat = parseFloat(latVal);
            const lon = parseFloat(lonVal);
            const struct_val = parseFloat(document.getElementById('calc-structure').value);
            const soil_val = parseFloat(document.getElementById('calc-soil').value);
            
            // Calculate hazard based on location proximity to active tectonic zones in Central America
            let hazard = 40; // Default baseline
            let locationDesc = "";
            
            // Nicaragua/Central America box: Lat [10.5, 15.0], Lon [-88.0, -82.5]
            if (lat >= 10.5 && lat <= 15.0 && lon >= -88.0 && lon <= -82.5) {
                locationDesc = "Ubicación detectada en la zona de Centroamérica (Nicaragua y vecindades), caracterizada por alta actividad tectónica.";
                if (lon < -85.5) {
                    // Pacific / Volcanic region
                    // Distance to Volcanic Belt (estimated line: y = -0.73 * x - 51.1)
                    const distToVolcanoLine = Math.abs(lat - (-0.73 * lon - 51.1)) / Math.sqrt(1 + 0.73 * 0.73);
                    hazard = 85 - (distToVolcanoLine * 15);
                    if (hazard < 55) hazard = 55;
                    
                    // Boost near Managua fault system (12.13, -86.25)
                    const distToManagua = Math.sqrt(Math.pow(lat - 12.13, 2) + Math.pow(lon - -86.25, 2));
                    if (distToManagua < 0.4) {
                        hazard += (0.4 - distToManagua) * 35;
                        locationDesc += " Cercanía crítica al sistema de fallas sísmicas locales de Managua.";
                    } else {
                        locationDesc += " Ubicado en la franja sísmica del Pacífico y arco volcánico de alta sismicidad por subducción de la placa de Cocos.";
                    }
                } else {
                    // Central / Caribbean region
                    hazard = 55;
                    locationDesc += " Ubicado en la región central/atlántica, con menor densidad de fallas activas y sismicidad histórica moderada.";
                }
            } else {
                hazard = 35; // Default low risk outside the region
                locationDesc = "Ubicación fuera del área de calibración principal de Centroamérica. Se asume sismicidad de base estándar.";
            }
            
            hazard = Math.min(95, Math.max(20, hazard));
            
            // Vulnerability factor from structural selections
            // Structure: Adobe (0.9), Mampostería (0.7), Concreto (0.4), Madera (0.3), Acero (0.2)
            // Soil: Blando (0.8), Firme (0.5), Roca (0.2)
            const vuln = (struct_val + soil_val) / 1.7; // Normalized 0 to 1
            let score = Math.round(hazard * (0.3 + 0.7 * vuln));
            score = Math.min(100, Math.max(1, score));
            
            // Show result area
            const riskResult = document.getElementById('risk-result');
            if (riskResult) {
                riskResult.style.display = 'block';
            }
            
            // Update gauge values
            const riskVal = document.getElementById('risk-val');
            const riskLabel = document.getElementById('risk-label');
            const riskGaugeBar = document.getElementById('risk-gauge-bar');
            
            if (riskVal) riskVal.textContent = `${score}%`;
            
            let level = "";
            let color = "";
            let report = "";
            
            if (score < 25) {
                level = "Bajo";
                color = "#4caf50"; // Green
                report = `<strong>Riesgo Sísmico Estimado: BAJO (${score}%)</strong><br><br>${locationDesc}<br><br>Su estructura posee alta resistencia (o ductilidad) y está desplantada sobre suelo firme/roca. Ante un sismo de magnitud importante, la sacudida percibida será leve y la probabilidad de daño estructural es mínima.`;
            } else if (score < 50) {
                level = "Moderado";
                color = "#ffb300"; // Yellow
                report = `<strong>Riesgo Sísmico Estimado: MODERADO (${score}%)</strong><br><br>${locationDesc}<br><br>Riesgo de sacudida intermedia. La estructura posee un nivel de resistencia estándar pero el tipo de suelo o la cercanía a zonas activas pueden amplificar las vibraciones. Se aconseja realizar inspecciones periódicas de fisuras y asegurar elementos no estructurales suspendidos.`;
            } else if (score < 75) {
                level = "Alto";
                color = "#ff5722"; // Orange
                report = `<strong>Riesgo Sísmico Estimado: ALTO (${score}%)</strong><br><br>${locationDesc}<br><br>¡PELIGRO! La estructura o el suelo presentan vulnerabilidades importantes en una zona de sismicidad activa. Es probable que un evento sísmico moderado o fuerte provoque daños considerables en paredes, mampostería o cimientos. Se recomienda encarecidamente asesoría de ingeniería estructural para reforzamiento.`;
            } else {
                level = "Muy Alto";
                color = "#f44336"; // Red
                report = `<strong>Riesgo Sísmico Estimado: CRÍTICO / MUY ALTO (${score}%)</strong><br><br>${locationDesc}<br><br>¡ZONA DE DESASTRE POTENCIAL! La combinación de una estructura altamente vulnerable (como adobe o mampostería sin refuerzo) y suelo blando en una zona sísmica de alto peligro (falla local o subducción) genera una amenaza crítica. Existe un alto riesgo de colapso parcial o total ante sismos mayores. Se aconseja la reubicación o sustitución inmediata de sistemas estructurales vulnerables.`;
            }
            
            if (riskLabel) {
                riskLabel.textContent = level;
                riskLabel.style.color = color;
            }
            
            if (riskGaugeBar) {
                riskGaugeBar.style.height = `${score}%`;
                riskGaugeBar.style.backgroundColor = color;
            }
            
            const riskReport = document.getElementById('risk-report');
            if (riskReport) {
                riskReport.innerHTML = report;
            }
            
            // Scroll results into view smoothly
            if (riskResult) {
                riskResult.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        });
    }
});

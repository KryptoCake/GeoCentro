/**
 * risk_map.js — Controlador JavaScript para el Mapa de Riesgo Sísmico Interactivo
 * Desarrollado para GeoCentro
 */

document.addEventListener('DOMContentLoaded', function() {
    let map;
    let evalMarker = null;
    let poligonosLayers = [];
    let sismosLayerGroup;
    let poligonosLayerGroup;
    
    // Elementos del DOM
    const manualLatInput = document.getElementById('manual-lat');
    const manualLonInput = document.getElementById('manual-lon');
    const btnEvalManual = document.getElementById('btn-eval-manual');
    const riskInfoDefault = document.getElementById('risk-info-default');
    const riskInfoResults = document.getElementById('risk-info-results');
    const riskValBadge = document.getElementById('risk-val-badge');
    const riskLabelBadge = document.getElementById('risk-label-badge');
    const gaugeBarRisk = document.getElementById('gauge-bar-risk');
    const coordsText = document.getElementById('coords-text');
    const riskAttributesList = document.getElementById('risk-attributes-list');
    const riskTechnicalDesc = document.getElementById('risk-technical-desc');
    
    // Importador KML
    const kmlFileInput = document.getElementById('kml-file-input');
    const kmlUploadStatus = document.getElementById('kml-upload-status');
    const btnFileDummy = document.getElementById('btn-file-dummy');

    // 1. INICIALIZAR MAPA
    // ==========================================
    function initMap() {
        // Centro geográfico de Centroamérica (Nicaragua)
        const center = [12.6, -86.2];
        const defaultZoom = 7.5;
        
        map = L.map('map-risk', {
            center: center,
            zoom: defaultZoom,
            zoomControl: false // Lo agregaremos abajo en una posición más cómoda
        });
        
        // Agregar control de zoom
        L.control.zoom({ position: 'topleft' }).addTo(map);
        
        // Capa base: CartoDB Dark Matter (diseño estético oscuro)
        const baseLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }).addTo(map);
        
        // Inicializar grupos de capas
        poligonosLayerGroup = L.layerGroup().addTo(map);
        sismosLayerGroup = L.layerGroup().addTo(map);
        
        // Control de capas
        const overlayMaps = {
            '<span style="color: #64b5f6;"><i class="fa-solid fa-draw-polygon"></i> Polígonos de Riesgo</span>': poligonosLayerGroup,
            '<span style="color: #e57373;"><i class="fa-solid fa-circle"></i> Sismicidad Reciente</span>': sismosLayerGroup
        };
        L.control.layers(null, overlayMaps, { collapsed: false, position: 'bottomleft' }).addTo(map);
        
        // Evento de clic en el mapa para evaluar coordenadas
        map.on('click', function(e) {
            evaluarCoordenada(e.latlng.lat, e.latlng.lng);
        });
    }

    // 2. CARGAR POLÍGONOS DESDE LA API
    // ==========================================
    function cargarPoligonos() {
        // Limpiar capa actual
        poligonosLayerGroup.clearLayers();
        poligonosLayers = [];
        
        fetch('/api/poligonos')
            .then(response => response.json())
            .then(polys => {
                polys.forEach(p => {
                    if (p.puntos && p.puntos.length >= 3) {
                        // Leaflet requiere [[lat1, lon1], [lat2, lon2], ...]
                        const latLngs = p.puntos.map(pt => [pt.lat, pt.lon]);
                        
                        // Diseñar estilo según su color e importancia
                        const polyLayer = L.polygon(latLngs, {
                            color: p.color || '#ff5722',
                            fillColor: p.color || '#ff5722',
                            weight: 2,
                            fillOpacity: 0.15,
                            lineJoin: 'round'
                        });
                        
                        // Formatear popup estético
                        const pesoVal = (p.peso !== null && p.peso !== undefined) ? p.peso.toLocaleString() : '0';
                        const unidadVal = p.unidad || 'Exposición';
                        const popupContent = `
                            <div style="font-family: inherit; color: #fff; min-width: 180px; padding: 5px;">
                                <h4 style="margin: 0 0 8px 0; color: ${p.color || '#ff5722'}; font-size: 0.95rem; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px;">
                                    <i class="fa-solid fa-draw-polygon"></i> ${p.nombre}
                                </h4>
                                <p style="margin: 0 0 8px 0; font-size: 0.8rem; line-height: 1.4; color: #ccc;">
                                    ${p.descripcion || 'Sin descripción'}
                                </p>
                                <div style="font-size: 0.8rem; background: rgba(0,0,0,0.2); padding: 6px; border-radius: 4px;">
                                    <strong>Carga/Exposición:</strong> ${pesoVal} ${unidadVal}
                                </div>
                            </div>
                        `;
                        
                        polyLayer.bindPopup(popupContent);
                        poligonosLayerGroup.addLayer(polyLayer);
                        poligonosLayers.push({ data: p, layer: polyLayer });
                    }
                });
            })
            .catch(error => {
                console.error("Error al cargar polígonos:", error);
                if (window.showToast) window.showToast('Error al cargar polígonos de riesgo.', 'error');
            });
    }

    // 3. CARGAR SISMICIDAD RECIENTE PARA COMPARACIÓN VISUAL
    // ==========================================
    function cargarSismosRecientes() {
        sismosLayerGroup.clearLayers();
        
        // Obtener sismos locales recientes (últimos 150)
        fetch('/api/sismos?limit=150')
            .then(response => response.json())
            .then(sismos => {
                sismos.forEach(s => {
                    const lat = parseFloat(s.latitud);
                    const lon = parseFloat(s.longitud);
                    const mag = parseFloat(s.magnitud);
                    
                    if (!isNaN(lat) && !isNaN(lon)) {
                        // Determinar color de magnitud
                        let color = '#4caf50'; // Verde (<4.0)
                        if (mag >= 6.0) color = '#f44336'; // Rojo (Fuerte)
                        else if (mag >= 5.0) color = '#ff5722'; // Naranja (Moderado)
                        else if (mag >= 4.0) color = '#ffb300'; // Amarillo (Ligero)
                        
                        // El radio depende de la magnitud de forma exponencial
                        const radius = Math.pow(mag, 1.8) * 1.5;
                        
                        const circleMarker = L.circleMarker([lat, lon], {
                            radius: radius,
                            color: color,
                            fillColor: color,
                            weight: 1.5,
                            fillOpacity: 0.45
                        });
                        
                        const popupText = `
                            <div style="font-family: inherit; color: #fff; min-width: 150px;">
                                <h4 style="margin: 0 0 5px 0; color: ${color};">M ${mag.toFixed(1)} — ${s.pais}</h4>
                                <p style="margin: 0; font-size: 0.8rem;">
                                    <strong>Ubicación:</strong> ${s.descripcion}<br>
                                    <strong>Profundidad:</strong> ${s.profundidad} km<br>
                                    <strong>Fecha UTC:</strong> ${s.fecha_utc} ${s.hora_utc}
                                </p>
                            </div>
                        `;
                        
                        circleMarker.bindPopup(popupText);
                        
                        // Evento hover para dar feedback
                        circleMarker.on('mouseover', function(e) {
                            this.openPopup();
                            this.setStyle({ fillOpacity: 0.8 });
                        });
                        circleMarker.on('mouseout', function(e) {
                            this.setStyle({ fillOpacity: 0.45 });
                        });
                        
                        sismosLayerGroup.addLayer(circleMarker);
                    }
                });
            })
            .catch(error => console.error("Error al cargar sismicidad reciente:", error));
    }

    // 4. ALGORITMO EVALUAR RIESGO DE COORDENADA (API CALL)
    // ==========================================
    function evaluarCoordenada(lat, lon) {
        lat = parseFloat(lat);
        lon = parseFloat(lon);
        
        if (isNaN(lat) || isNaN(lon)) return;
        
        // Mover inputs manuales a este valor para sincronización
        manualLatInput.value = lat.toFixed(4);
        manualLonInput.value = lon.toFixed(4);
        
        // Mostrar u ocultar marcador de evaluación en el mapa
        if (evalMarker === null) {
            evalMarker = L.marker([lat, lon], {
                draggable: true,
                icon: L.icon({
                    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
                    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [1, -34],
                    shadowSize: [41, 41]
                })
            }).addTo(map);
            
            // Si el usuario arrastra el marcador, evaluar de nuevo al soltarlo
            evalMarker.on('dragend', function(e) {
                const position = evalMarker.getLatLng();
                evaluarCoordenada(position.lat, position.lng);
            });
        } else {
            evalMarker.setLatLng([lat, lon]);
        }
        
        // Panear suavemente al punto
        map.panTo([lat, lon]);
        
        // Llamar API
        fetch(`/api/riesgo/evaluar?lat=${lat}&lon=${lon}`)
            .then(response => response.json())
            .then(res => {
                if (res.error) {
                    if (window.showToast) window.showToast(res.error, 'error');
                    return;
                }
                
                // Mostrar sidebar de resultados y ocultar default
                riskInfoDefault.style.display = 'none';
                riskInfoResults.style.display = 'block';
                
                // Actualizar coordenadas
                coordsText.textContent = `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
                
                // Determinar nivel
                const score = res.score;
                riskValBadge.textContent = `${score}%`;
                
                let level = "Bajo";
                let color = "#4caf50";
                if (score >= 75) {
                    level = "Muy Alto";
                    color = "#f44336";
                } else if (score >= 50) {
                    level = "Alto";
                    color = "#ff5722";
                } else if (score >= 25) {
                    level = "Moderado";
                    color = "#ffb300";
                }
                
                riskLabelBadge.textContent = level;
                riskLabelBadge.style.color = color;
                
                // Actualizar gauge bar de fondo
                gaugeBarRisk.style.height = `${score}%`;
                gaugeBarRisk.style.backgroundColor = color;
                
                // Llenar lista de atributos
                let attrHTML = '';
                
                // Atributo Vs30
                if (res.en_grilla && res.vs30) {
                    attrHTML += `<li>
                        <i class="fa-solid fa-wave-square" style="color: #4fc3f7; margin-right: 6px;"></i> 
                        Vs30: <strong>${res.vs30.toFixed(0)} m/s</strong> (Clase ${res.clase_sitio})
                    </li>`;
                    attrHTML += `<li>
                        <i class="fa-solid fa-circle-chevron-up" style="color: #81c784; margin-right: 6px;"></i> 
                        Amplificación local: <strong>${res.amp_factor >= 0 ? '+' : ''}${res.amp_factor.toFixed(2)} MMI</strong>
                    </li>`;
                } else {
                    attrHTML += `<li>
                        <i class="fa-solid fa-wave-square" style="color: #e0e0e0; margin-right: 6px;"></i> 
                        Vs30: <strong>Estimado (760 m/s)</strong> (Fuera de grilla)
                    </li>`;
                }
                
                // Atributo Slab2
                if (res.en_grilla && res.slab_prof_km) {
                    attrHTML += `<li>
                        <i class="fa-solid fa-layer-group" style="color: #ba68c8; margin-right: 6px;"></i> 
                        Placa Cocos (Slab2): <strong>${Math.abs(res.slab_prof_km).toFixed(1)} km</strong> prof.
                    </li>`;
                } else {
                    attrHTML += `<li>
                        <i class="fa-solid fa-layer-group" style="color: #e0e0e0; margin-right: 6px;"></i> 
                        Placa Cocos: <strong>Sin cobertura</strong>
                    </li>`;
                }
                
                // Polígonos intersectados
                if (res.poligonos && res.poligonos.length > 0) {
                    res.poligonos.forEach(p => {
                        const pesoVal = (p.peso !== null && p.peso !== undefined) ? p.peso.toLocaleString() : '0';
                        const unidadVal = p.unidad || 'Exposición';
                        attrHTML += `<li style="border-left: 3px solid ${p.color}; padding-left: 8px; margin-top: 5px; background: rgba(255,255,255,0.02); border-radius: 0 4px 4px 0; padding: 4px 8px;">
                            <i class="fa-solid fa-draw-polygon" style="color: ${p.color};"></i> 
                            <strong>${p.nombre}</strong><br>
                            <span style="font-size: 0.75rem; color: var(--text-secondary);">${pesoVal} ${unidadVal}</span>
                        </li>`;
                    });
                } else {
                    attrHTML += `<li style="color: var(--text-secondary);">
                        <i class="fa-solid fa-square-minus" style="margin-right: 6px;"></i> Ningún polígono intersectado
                    </li>`;
                }
                
                riskAttributesList.innerHTML = attrHTML;
                
                // Redactar diagnóstico técnico
                let desc = '';
                if (res.poligonos && res.poligonos.length > 0) {
                    const polysNames = res.poligonos.map(p => p.nombre).join(', ');
                    desc += `El punto de interés se encuentra localizado en el interior de: <strong>${polysNames}</strong>. `;
                }
                
                if (res.en_grilla && res.vs30) {
                    if (res.vs30 <= 180) {
                        desc += `El suelo predominante en la zona es de tipo <strong>E (Blando/Sedimentario)</strong>. Esto genera una amplificación sísmica muy elevada de hasta ${res.amp_factor.toFixed(2)} grados en escala macrosísmica de Mercalli (MMI). Ante un sismo de magnitud moderada, las vibraciones se magnificarán sustancialmente. `;
                    } else if (res.vs30 <= 360) {
                        desc += `El suelo local es de clase <strong>D (Suelo rígido/compacto)</strong>. Tiene potencial moderado de amplificación de ondas sísmicas (+${res.amp_factor.toFixed(2)} MMI). `;
                    } else {
                        desc += `El terreno está asentado sobre <strong>Roca madre o suelo duro</strong> (Clase ${res.clase_sitio}). La atenuación natural de la roca minimiza la amplificación estructural, reduciendo la sacudida y previniendo efectos secundarios de sitio. `;
                    }
                } else {
                    desc += `El punto se encuentra fuera de la cobertura costera de microzonificación. Se asume un suelo firme neutro. `;
                }
                
                if (res.en_grilla && res.slab_prof_km) {
                    desc += `Existe un peligro sísmico de fondo dominante por la placa de subducción de Cocos, localizada a unos <strong>${Math.abs(res.slab_prof_km).toFixed(1)} km</strong> de profundidad bajo la corteza. `;
                }
                
                // Conclusión por nivel
                if (score >= 75) {
                    desc += `<br><br><span style="color: #f44336; font-weight: 600;"><i class="fa-solid fa-triangle-exclamation"></i> Zona crítica de alta vulnerabilidad. Se recomienda evitar construcciones de mampostería no reforzada o adobe en esta región.</span>`;
                } else if (score >= 50) {
                    desc += `<br><br><span style="color: #ff5722; font-weight: 600;"><i class="fa-solid fa-triangle-exclamation"></i> Peligro moderado-alto. Se recomiendan inspecciones estructurales preventivas periódicas.</span>`;
                } else {
                    desc += `<br><br><span style="color: #4caf50; font-weight: 600;"><i class="fa-solid fa-circle-check"></i> El riesgo estimado en el punto es bajo. Las vibraciones esperadas no deberían generar daños estructurales mayores.</span>`;
                }
                
                riskTechnicalDesc.innerHTML = desc;
            })
            .catch(error => {
                console.error("Error al evaluar coordenadas:", error);
                if (window.showToast) window.showToast('Error de conexión con el backend de evaluación.', 'error');
            });
    }

    // 5. EVENTOS E INTERACCIONES DE INTERFAZ
    // ==========================================
    if (btnEvalManual) {
        btnEvalManual.addEventListener('click', function() {
            const lat = parseFloat(manualLatInput.value);
            const lon = parseFloat(manualLonInput.value);
            
            if (isNaN(lat) || isNaN(lon)) {
                if (window.showToast) window.showToast('Ingresa coordenadas numéricas válidas.', 'error');
                return;
            }
            evaluarCoordenada(lat, lon);
        });
    }
    
    // Sincronizar inputs al presionar Enter
    [manualLatInput, manualLonInput].forEach(inp => {
        if (inp) {
            inp.addEventListener('keyup', function(e) {
                if (e.key === 'Enter') {
                    btnEvalManual.click();
                }
            });
        }
    });

    // 6. ENVIAR FORMULARIO DE IMPORTACIÓN KML (POST)
    // ==========================================
    if (kmlFileInput) {
        kmlFileInput.addEventListener('change', function() {
            const file = kmlFileInput.files[0];
            if (!file) return;
            
            // Validar extensión
            if (!file.name.toLowerCase().endsWith('.kml')) {
                if (window.showToast) window.showToast('El archivo seleccionado debe ser un .kml válido.', 'error');
                kmlFileInput.value = '';
                return;
            }
            
            kmlUploadStatus.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Subiendo y procesando...';
            btnFileDummy.disabled = true;
            
            const formData = new FormData();
            formData.append('file', file);
            
            fetch('/api/poligonos/importar-kml', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(res => {
                kmlFileInput.value = ''; // Limpiar file
                btnFileDummy.disabled = false;
                
                if (res.success) {
                    kmlUploadStatus.innerHTML = `<span style="color: #4caf50;"><i class="fa-solid fa-check"></i> ${res.message}</span>`;
                    if (window.showToast) window.showToast(res.message, 'success');
                    // Recargar polígonos en el mapa para ver los nuevos
                    cargarPoligonos();
                } else {
                    kmlUploadStatus.innerHTML = `<span style="color: #f44336;"><i class="fa-solid fa-xmark"></i> ${res.error}</span>`;
                    if (window.showToast) window.showToast(res.error, 'error');
                }
            })
            .catch(error => {
                btnFileDummy.disabled = false;
                kmlFileInput.value = '';
                kmlUploadStatus.innerHTML = '<span style="color: #f44336;">Error de red.</span>';
                console.error("Error al importar KML:", error);
                if (window.showToast) window.showToast('Error de red al intentar importar KML.', 'error');
            });
        });
    }

    // Inicializar todo
    initMap();
    cargarPoligonos();
    cargarSismosRecientes();
});

document.addEventListener('DOMContentLoaded', function() {
    // 1. Mobile Menu Toggle
    const mobileToggle = document.getElementById('mobile-toggle');
    const navbar = document.querySelector('.navbar');
    
    if (mobileToggle && navbar) {
        mobileToggle.addEventListener('click', function() {
            navbar.classList.toggle('show');
            const icon = mobileToggle.querySelector('i');
            if (navbar.classList.contains('show')) {
                icon.className = 'fa-solid fa-xmark';
            } else {
                icon.className = 'fa-solid fa-bars';
            }
        });
    }
    
    // 2. Sync button handling
    const btnSync = document.getElementById('btn-sync');
    if (btnSync) {
        btnSync.addEventListener('click', function() {
            const icon = btnSync.querySelector('i');
            const label = btnSync.querySelector('span');
            
            // Start spinning icon
            icon.classList.add('fa-spin');
            btnSync.disabled = true;
            if (label) label.textContent = 'Actualizando...';
            
            fetch('/api/scrape/trigger', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(res => res.json())
            .then(data => {
                icon.classList.remove('fa-spin');
                btnSync.disabled = false;
                if (label) label.textContent = 'Actualizar';
                
                if (data.success) {
                    showToast(`Éxito: Se encontraron ${data.new_sismos} nuevos eventos sísmicos.`, 'success');
                    // If on homepage, refresh map data
                    if (typeof window.refreshMapData === 'function') {
                        window.refreshMapData();
                    }
                    // If on historical page, refresh table data
                    if (typeof window.refreshHistoricalData === 'function') {
                        window.refreshHistoricalData();
                    }
                    // Reload news if present
                    if (document.getElementById('news-feed-container')) {
                        loadNewsFeed();
                    }
                } else {
                    showToast(`Error al actualizar: ${data.error}`, 'error');
                }
            })
            .catch(err => {
                icon.classList.remove('fa-spin');
                btnSync.disabled = false;
                if (label) label.textContent = 'Actualizar';
                showToast('Error de red al conectar con el servidor.', 'error');
                console.error(err);
            });
        });
    }
    
    // 3. Load news feed if container is present
    const newsContainer = document.getElementById('news-feed-container');
    if (newsContainer) {
        loadNewsFeed();
    }
    
    function loadNewsFeed() {
        fetch('/api/news?limit=6')
            .then(res => res.json())
            .then(data => {
                if (data.length === 0) {
                    newsContainer.innerHTML = '<div class="seismo-placeholder-text">No hay noticias o alertas publicadas.</div>';
                    return;
                }
                
                newsContainer.innerHTML = '';
                data.forEach(item => {
                    const card = document.createElement('div');
                    card.className = 'news-card-item';
                    card.innerHTML = `
                        <div class="news-item-header">
                            <h4 class="news-item-title">${item.titulo}</h4>
                            <span class="news-item-date">${item.fecha}</span>
                        </div>
                        <p class="news-item-desc">${item.resumen}</p>
                        <span class="news-item-country-badge">${item.pais}</span>
                    `;
                    newsContainer.appendChild(card);
                });
            })
            .catch(err => {
                console.error("Error loading news feed:", err);
                newsContainer.innerHTML = '<div class="error-text" style="color: #f44336; padding: 20px; text-align: center;"><i class="fa-solid fa-circle-exclamation"></i> Error al cargar las noticias.</div>';
            });
    }
    
    // Toast notifications utility
    function showToast(message, type = 'info') {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.style.position = 'fixed';
            container.style.bottom = '24px';
            container.style.right = '24px';
            container.style.zIndex = '9999';
            container.style.display = 'flex';
            container.style.flexDirection = 'column';
            container.style.gap = '10px';
            document.body.appendChild(container);
        }
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.style.background = 'rgba(20, 21, 28, 0.9)';
        toast.style.backdropFilter = 'blur(10px)';
        toast.style.border = '1px solid rgba(255,255,255,0.08)';
        toast.style.borderRadius = '8px';
        toast.style.padding = '12px 20px';
        toast.style.color = '#fff';
        toast.style.fontSize = '0.9rem';
        toast.style.fontWeight = '500';
        toast.style.boxShadow = '0 10px 30px rgba(0,0,0,0.5)';
        toast.style.display = 'flex';
        toast.style.alignItems = 'center';
        toast.style.gap = '10px';
        toast.style.transform = 'translateY(100px)';
        toast.style.opacity = '0';
        toast.style.transition = 'all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
        
        let icon = '<i class="fa-solid fa-circle-info" style="color: #00bcd4;"></i>';
        if (type === 'success') {
            icon = '<i class="fa-solid fa-circle-check" style="color: #4caf50;"></i>';
            toast.style.borderLeft = '4px solid #4caf50';
        } else if (type === 'error') {
            icon = '<i class="fa-solid fa-circle-exclamation" style="color: #f44336;"></i>';
            toast.style.borderLeft = '4px solid #f44336';
        }
        
        toast.innerHTML = `${icon} <span>${message}</span>`;
        container.appendChild(toast);
        
        // Animate in
        setTimeout(() => {
            toast.style.transform = 'translateY(0)';
            toast.style.opacity = '1';
        }, 10);
        
        // Remove toast after 4 seconds
        setTimeout(() => {
            toast.style.transform = 'translateY(-20px)';
            toast.style.opacity = '0';
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 4000);
    }
    
    // Share showToast globally
    window.showToast = showToast;
});

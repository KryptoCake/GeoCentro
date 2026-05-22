# Guías de Diseño y UX - GeoCentro

## Estética y Estilo Visual
1. **Diseño Moderno y Premium:**
   - La interfaz debe transmitir profesionalismo y ser visualmente impactante ("Wow factor").
   - Uso de un tema oscuro refinado (Dark Mode) con contrastes elegantes, evitando el negro puro en favor de tonos gris azulados profundos.
   - Tipografía moderna e interactiva (ej. Inter u Outfit de Google Fonts) en lugar de fuentes por defecto del navegador.
   - Bordes redondeados sutiles, efectos de cristal (glassmorphism/backdrop-filter) en paneles flotantes sobre el mapa.
   
2. **Esquema de Colores (Gama de Alerta):**
   - **Fondo principal:** Tonos oscuros (#121824, #1a2333).
   - **Sismos leves (magnitud < 4):** Amarillo suave / naranja translúcido.
   - **Sismos moderados (magnitud 4 - 5.5):** Naranja brillante.
   - **Sismos fuertes (magnitud > 5.5):** Rojo / carmesí vibrante.
   - **Acentos y enlaces:** Azul eléctrico o cian (#00d2ff, #3b82f6).

3. **Interactividad:**
   - Animaciones y transiciones suaves en botones y modales (hover effects).
   - Micro-interacciones al hacer clic en marcadores del mapa (animación de rebote o pulsación concéntrica).

## Principios de UX (Experiencia de Usuario)
1. **Prioridad del Mapa:**
   - El mapa debe ser el elemento central de la portada y ocupar la mayor parte de la pantalla (idealmente pantalla completa o layout de panel lateral colapsable).
   - Controles del mapa simplificados e intuitivos.
   
2. **Filtros Flexibles:**
   - La sección de historial debe permitir filtrar de manera rápida y reactiva sin necesidad de recargar la página completa.
   - Inputs de fechas y magnitudes fáciles de manipular en pantallas táctiles (móvil) y de escritorio.

3. **Rendimiento y Carga Rápida:**
   - Minimizar el peso de los scripts.
   - El proxy de webcams y sismogramas debe responder eficientemente y manejar errores de origen de manera amigable (mostrando placeholders o mensajes claros si la cámara está fuera de línea).

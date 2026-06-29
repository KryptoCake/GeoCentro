#!/usr/bin/env python3
"""
GeoCentro - Virtual Webmaster Alert Management CLI
Allows the virtual agent (Hermes) or human operators to add, list, update, and delete alerts/news.
"""
import sys
import os
import argparse
from datetime import datetime

# Add root directory to python path to ensure we can import database
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import database

def format_date(date_str):
    if not date_str:
        return datetime.now().strftime('%Y-%m-%d')
    try:
        # Check if already YYYY-MM-DD
        datetime.strptime(date_str, '%Y-%m-%d')
        return date_str
    except ValueError:
        # Fallback/Parse other common formats if needed
        return datetime.now().strftime('%Y-%m-%d')

def cmd_list(args):
    """List recent alerts in the system."""
    limit = args.limit or 20
    category = args.category
    
    print(f"\n--- LISTANDO ALERTAS (Categoria: {category or 'Todas'}, Límite: {limit}) ---")
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT id, titulo, fecha, pais, categoria, url, imagen_url FROM news"
    params = []
    
    if category:
        query += " WHERE categoria = ?"
        params.append(category)
        
    query += " ORDER BY fecha DESC, created_at DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("No se encontraron alertas en el sistema.")
        return
        
    print(f"{'ID':<5} | {'CATEGORIA':<9} | {'PAIS':<12} | {'FECHA':<10} | {'TITULO'}")
    print("-" * 80)
    for row in rows:
        title = row['titulo']
        if len(title) > 40:
            title = title[:37] + "..."
        print(f"{row['id']:<5} | {row['categoria']:<9} | {row['pais']:<12} | {row['fecha']:<10} | {title}")
        if args.verbose:
            print(f"      Enlace: {row['url']}")
            if row['imagen_url']:
                print(f"      Imagen: {row['imagen_url']}")
            print("-" * 80)
    print("")

def cmd_add(args):
    """Add a new alert/news item."""
    if not args.title or not args.summary or not args.country:
        print("Error: Los parámetros --title, --summary y --country son obligatorios.")
        sys.exit(1)
        
    fecha = format_date(args.date)
    category = args.category or 'general'
    
    # Generate unique URL anchor if not provided to avoid hash_id collisions
    url = args.url
    if not url:
        timestamp = int(datetime.now().timestamp())
        url = f"#alert_{timestamp}"
        
    # Standardize image url
    image_url = args.image_url
    if image_url == '':
        image_url = None
        
    print(f"Agregando alerta: '{args.title}' para {args.country}...")
    
    success = database.save_news(
        titulo=args.title.strip(),
        url=url.strip(),
        fecha=fecha,
        resumen=args.summary.strip(),
        pais=args.country.strip(),
        categoria=category,
        imagen_url=image_url
    )
    
    if success:
        print("¡Alerta agregada exitosamente!")
    else:
        print("Error: No se pudo agregar la alerta. Probablemente ya existe una alerta con ese título y enlace (conflicto de hash_id).")
        sys.exit(1)

def cmd_update(args):
    """Update fields of an existing alert."""
    alert_id = args.id
    
    # Check if exists
    existing = database.get_news_by_id(alert_id)
    if not existing:
        print(f"Error: No se encontró ninguna alerta con el ID {alert_id}")
        sys.exit(1)
        
    print(f"Actualizando alerta ID {alert_id}...")
    
    # Build dictionary of fields to update
    updates = {}
    if args.title is not None:
        updates['titulo'] = args.title.strip()
    if args.url is not None:
        updates['url'] = args.url.strip()
    if args.date is not None:
        updates['fecha'] = format_date(args.date)
    if args.summary is not None:
        updates['resumen'] = args.summary.strip()
    if args.country is not None:
        updates['pais'] = args.country.strip()
    if args.category is not None:
        updates['categoria'] = args.category
    if args.image_url is not None:
        updates['imagen_url'] = args.image_url.strip() if args.image_url.strip() else None
        
    if not updates:
        print("No se especificaron campos para actualizar. Use --title, --summary, etc.")
        return
        
    success = database.update_news(alert_id, **updates)
    if success:
        print(f"¡Alerta ID {alert_id} actualizada correctamente!")
    else:
        print(f"Error al actualizar la alerta ID {alert_id}. Verifique restricciones de unicidad.")
        sys.exit(1)

def cmd_delete(args):
    """Delete an alert from the system."""
    alert_id = args.id
    
    existing = database.get_news_by_id(alert_id)
    if not existing:
        print(f"Error: No se encontró la alerta con el ID {alert_id}")
        sys.exit(1)
        
    confirm = args.force
    if not confirm:
        res = input(f"¿Está seguro de que desea eliminar la alerta ID {alert_id} ('{existing['titulo']}')? [s/N]: ")
        confirm = res.lower().strip() in ['s', 'si', 'y', 'yes']
        
    if confirm:
        success = database.delete_news(alert_id)
        if success:
            print(f"Alerta ID {alert_id} eliminada correctamente.")
        else:
            print(f"Error al intentar eliminar la alerta ID {alert_id}.")
            sys.exit(1)
    else:
        print("Operación cancelada.")

def main():
    parser = argparse.ArgumentParser(
        description="GeoCentro Virtual Webmaster CLI - Administrador de Alertas y Noticias"
    )
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")
    
    # list command
    p_list = subparsers.add_parser("list", help="Listar alertas recientes")
    p_list.add_argument("--limit", type=int, default=20, help="Límite de registros a mostrar (defecto: 20)")
    p_list.add_argument("--category", choices=['general', 'clima'], help="Filtrar por categoría")
    p_list.add_argument("--verbose", "-v", action="store_true", help="Mostrar enlaces e imagen")
    p_list.set_defaults(func=cmd_list)
    
    # add command
    p_add = subparsers.add_parser("add", help="Agregar una nueva alerta")
    p_add.add_argument("--title", required=True, help="Título de la alerta")
    p_add.add_argument("--summary", required=True, help="Contenido o resumen detallado de la alerta")
    p_add.add_argument("--country", required=True, help="País afectado (ej: Nicaragua, Costa Rica, Honduras, Guatemala, El Salvador, Panamá, Otros)")
    p_add.add_argument("--category", choices=['general', 'clima'], default='general', help="Categoría de la alerta (defecto: general)")
    p_add.add_argument("--url", help="Enlace web opcional (fuente de información)")
    p_add.add_argument("--image-url", help="URL opcional de una imagen ilustrativa")
    p_add.add_argument("--date", help="Fecha en formato YYYY-MM-DD (por defecto hoy)")
    p_add.set_defaults(func=cmd_add)
    
    # update command
    p_update = subparsers.add_parser("update", help="Actualizar una alerta existente")
    p_update.add_argument("id", type=int, help="ID de la alerta a modificar")
    p_update.add_argument("--title", help="Nuevo título")
    p_update.add_argument("--summary", help="Nuevo resumen o descripción")
    p_update.add_argument("--country", help="Nuevo país")
    p_update.add_argument("--category", choices=['general', 'clima'], help="Nueva categoría")
    p_update.add_argument("--url", help="Nuevo enlace web")
    p_update.add_argument("--image-url", help="Nueva URL de imagen (deje vacío para remover)")
    p_update.add_argument("--date", help="Nueva fecha (YYYY-MM-DD)")
    p_update.set_defaults(func=cmd_update)
    
    # delete command
    p_delete = subparsers.add_parser("delete", help="Eliminar una alerta")
    p_delete.add_argument("id", type=int, help="ID de la alerta a eliminar")
    p_delete.add_argument("--force", "-f", action="store_true", help="Forzar eliminación sin confirmación interactiva")
    p_delete.set_defaults(func=cmd_delete)
    
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)
        
    args.func(args)

if __name__ == "__main__":
    main()

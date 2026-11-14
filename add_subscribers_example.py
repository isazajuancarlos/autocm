"""
Script de ejemplo para añadir suscriptores a tu base de datos de email marketing.

USO:
python add_subscribers_example.py
"""

from email_marketing import EmailMarketingAgent
import logging

logging.basicConfig(level=logging.INFO)

def main():
    print("=" * 60)
    print("📧 SCRIPT DE EJEMPLO - AÑADIR SUSCRIPTORES")
    print("=" * 60)
    print()

    # Inicializar agente
    agent = EmailMarketingAgent()

    # OPCIÓN 1: Añadir suscriptor individual
    print("1️⃣ Añadiendo suscriptor individual...")
    success, msg = agent.add_subscriber(
        email="ejemplo@email.com",
        nombre="Usuario Ejemplo",
        fuente="script_inicial"
    )
    print(f"   Resultado: {msg}")
    print()

    # OPCIÓN 2: Añadir múltiples suscriptores
    print("2️⃣ Añadiendo múltiples suscriptores...")
    emails_lista = [
        ("contacto1@empresa.com", "Contacto Uno"),
        ("contacto2@empresa.com", "Contacto Dos"),
        ("abogado@bufete.com", "Abogado Principal"),
        ("dev@startup.com", "Developer"),
    ]

    stats = agent.bulk_add_subscribers(emails_lista, fuente="importacion_inicial")
    print(f"   Añadidos: {stats['added']}")
    print(f"   Duplicados: {stats['duplicates']}")
    print(f"   Errores: {stats['errors']}")
    print()

    # OPCIÓN 3: Importar desde archivo CSV
    print("3️⃣ Para importar desde CSV, crea un archivo 'contactos.csv':")
    print("""
   email,nombre
   user1@example.com,Usuario 1
   user2@example.com,Usuario 2
    """)
    print("   Luego descomenta el código abajo en este script.")
    print()

    # Descomentar para usar:
    """
    import csv
    with open('contactos.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Saltar header
        emails_csv = [(row[0], row[1]) for row in reader]
    agent.bulk_add_subscribers(emails_csv, fuente="csv_import")
    """

    # Mostrar estadísticas finales
    print("=" * 60)
    print("📊 ESTADÍSTICAS ACTUALES")
    print("=" * 60)
    stats = agent.get_stats()
    print(f"Total contactos: {stats['total_contactos']}")
    print(f"Activos: {stats['activos']}")
    print(f"Confirmados: {stats['confirmados']}")
    print(f"Campañas enviadas: {stats['total_campañas']}")
    print(f"\nFuentes de suscriptores:")
    for fuente, count in stats['fuentes'].items():
        print(f"  - {fuente}: {count}")
    print()

    # Exportar contactos
    print("4️⃣ Exportando contactos a CSV...")
    filename = agent.export_contacts('contactos_export.csv')
    print(f"   ✅ Exportado a: {filename}")
    print()

    agent.close()

    print("=" * 60)
    print("✅ SCRIPT COMPLETADO")
    print("=" * 60)
    print()
    print("Próximos pasos:")
    print("1. Edita este script con tus emails reales")
    print("2. Ejecuta: python add_subscribers_example.py")
    print("3. Inicia la API: python lead_capture_api.py")
    print("4. Configura formulario en xiliux.com")
    print("5. ¡Empieza a crecer tu lista!")


if __name__ == "__main__":
    main()
